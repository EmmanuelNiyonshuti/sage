"""
Service for ingesting satellite data into the database.

This is the business logic layer that:
1. Fetches parcel data from database
2. Calls Sentinel Hub API via client
3. Parses responses
4. Stores results in database
5. Handles errors and edge cases
"""

from datetime import date, datetime
from typing import Any

from geoalchemy2.shape import to_shape
from sqlalchemy.orm import Session

from app.clients.sentinel_hub import sentinel_client
from app.constants.evalscripts import NDVI_EVALSCRIPT
from app.models import Parcel, RasterStats


class IngestionService:
    """Service for ingesting satellite imagery statistics."""

    def __init__(self, db_s: Session):
        """
        Initialize ingestion service.

        Args:
            db_s: SQLAlchemy database session
        """
        self.db_s = db_s

    def ingest_parcel_ndvi(
        self,
        parcel_id: str,
        start_date: date,
        end_date: date,
    ) -> dict[str, Any]:
        """
        Ingest NDVI data for a specific parcel.

        This is the main entry point for satellite data ingestion.

        Process:
        1. Fetch parcel from database
        2. Convert geometry to GeoJSON
        3. Call Sentinel Hub API
        4. Parse response
        5. Store statistics in raster_stats table
        6. Return summary

        Args:
            parcel_id: UUID of the parcel to process
            start_date: Start of date range
            end_date: End of date range

        Returns:
            Summary of ingestion results

        Raises:
            ValueError: If parcel not found
            httpx.HTTPStatusError: If API call fails
        """
        parcel = self._get_parcel(parcel_id)

        # 2. Convert PostGIS geometry to GeoJSON
        geometry_geojson = self._convert_geometry_to_geojson(parcel.geometry)

        # 3. Call Sentinel Hub API
        response = sentinel_client.get_statistics(
            geometry=geometry_geojson,
            start_date=start_date,
            end_date=end_date,
            evalscript=NDVI_EVALSCRIPT,
            max_cloud_coverage=30,
        )

        # 4. Parse response and store
        stored_count = self._parse_and_store_response(
            parcel_id=parcel_id,
            response=response,
            metric_type="NDVI",
        )
        self.db_s.commit()

        return {
            "parcel_id": parcel_id,
            "parcel_name": parcel.name,
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
            "records_created": stored_count,
            "status": "success",
        }

    def _get_parcel(self, parcel_id: str) -> Parcel:
        """
        Fetch parcel from database.

        Args:
            parcel_id: parcel UUID

        Returns:
            parcel model instance

        Raises:
            ValueError: If parcel not found
        """
        parcel = self.db_s.get(Parcel, parcel_id)

        if not parcel:
            raise ValueError(f"parcel with uid '{parcel_id}' not found")

        if not parcel.is_active:
            raise ValueError(f"parcel '{parcel_id}' is not active")

        return parcel

    def _convert_geometry_to_geojson(self, geometry) -> dict[str, Any]:
        """
        Convert PostGIS geometry to GeoJSON format.

        Args:
            geometry: SQLAlchemy geometry object (from geoalchemy2)

        Returns:
            GeoJSON dictionary
        """
        # Convert WKB (Well-Known Binary) to Shapely shape
        shape = to_shape(geometry)

        # Convert to GeoJSON
        return {
            "type": "Polygon",
            "coordinates": [list(shape.exterior.coords)],
        }

    def _parse_and_store_response(
        self,
        parcel_id: str,
        response: dict[str, Any],
        metric_type: str,
    ) -> int:
        """
        Parse Sentinel Hub response and store in database.

        The response contains multiple time intervals (one per satellite pass).
        For each interval, we extract statistics and create a raster_stats record.

        Args:
            parcel_id: parcel UUID
            response: Raw API response
            metric_type: Type of index (NDVI, NDMI, etc.)

        Returns:
            Number of records created
        """
        data_intervals = response.get("data", [])
        stored_count = 0

        for interval_data in data_intervals:
            # Extract acquisition date from interval
            interval_from = interval_data["interval"]["from"]
            acquisition_date = self._parse_acquisition_date(interval_from)

            # Extract statistics from response
            # Path: outputs -> default -> bands -> B0 -> stats
            stats = (
                interval_data.get("outputs", {})
                .get("default", {})
                .get("bands", {})
                .get("B0", {})
                .get("stats", {})
            )

            if not stats:
                # No data for this interval (too cloudy, no satellite pass, etc.)
                continue

            # Check if this record already exists (idempotent operation)
            exists = self._check_record_exists(
                parcel_id=parcel_id,
                acquisition_date=acquisition_date,
                metric_type=metric_type,
            )

            if exists:
                # Skip if already processed
                continue

            # Create new raster_stats record
            self._create_raster_stat(
                parcel_id=parcel_id,
                acquisition_date=acquisition_date,
                netric_type=metric_type,
                stats=stats,
                raw_metadata=interval_data,
            )

            stored_count += 1

        return stored_count

    def _parse_acquisition_date(self, datetime_str: str) -> date:
        """
        Parse ISO 8601 datetime string to date.

        Args:
            datetime_str: ISO 8601 datetime string (e.g., "2024-11-15T08:15:59Z")

        Returns:
            Date object
        """
        dt = datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))
        return dt.date()

    def _check_record_exists(
        self,
        parcel_id: str,
        acquisition_date: date,
        metric_type: str,
    ) -> bool:
        """
        Check if raster_stats record already exists.

        This makes the ingestion idempotent - running it multiple times
        won't create duplicate records.

        Args:
            parcel_id: parcel UUID
            acquisition_date: Date of acquisition
            netric_type: Index type

        Returns:
            True if record exists, False otherwise
        """
        exists = (
            self.db_s.query(RasterStats)
            .filter(
                RasterStats.parcel_id == parcel_id,
                RasterStats.acquisition_date == acquisition_date,
                RasterStats.metric_type == metric_type,
            )
            .first()
        )

        return exists is not None

    def _create_raster_stat(
        self,
        parcel_id: str,
        acquisition_date: date,
        netric_type: str,
        stats: dict[str, Any],
        raw_metadata: dict[str, Any],
    ) -> RasterStats:
        """
        Create a new raster_stats database record.

        Args:
            parcel_id: parcel UUID
            acquisition_date: Date of satellite acquisition
            netric_type: Type of vegetation index
            stats: Statistics dictionary from API response
            raw_metadata: Full interval data for debugging

        Returns:
            Created RasterStats instance
        """
        raster_stat = RasterStats(
            parcel_id=parcel_id,
            acquisition_date=acquisition_date,
            satellite_source="sentinel-2-l2a",
            metric_type=netric_type,
            mean_value=stats["mean"],
            min_value=stats["min"],
            max_value=stats["max"],
            std_dev=stats.get("stDev"),
            pixel_count=stats.get("sampleCount"),
            cloud_cover_percent=None,  # Not directly available in stats
            raw_metadata=raw_metadata,
        )

        self.db_s.add(raster_stat)
        self.db_s.flush()
        return raster_stat
