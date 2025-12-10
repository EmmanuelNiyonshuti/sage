"""
Service for ingesting satellite data into the database.

This is the business logic layer that:
1. Fetches parcel data from database
2. Calls Sentinel Hub API via client
3. Parses responses
4. Stores results in database
5. Handles errors and edge cases
"""

import logging
from datetime import UTC, date, datetime
from typing import Any

from geoalchemy2.shape import to_shape
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clients.sentinel_hub import sentinel_client
from app.constants.evalscripts import NDVI_EVALSCRIPT
from app.models import IngestionJob, Parcel, RasterStats

logger = logging.getLogger(__name__)


class IngestionService:
    """
    Service for ingesting satellite data into the database.
    """

    def __init__(self, session_factory):
        self.session_factory = session_factory

    def ingest_with_job_tracking(self, db_s: Session, job: IngestionJob):
        logger.info(f"starting ingestion for parcel with id {job.parcel_id}")
        job.status = "running"
        job.started_at = datetime.now(UTC)
        db_s.commit()
        try:
            parcel_boundary_geojson_obj = self.get_parcel_geometry(job.parcel_id)
            response = sentinel_client.get_statistics(
                parcel_boundary_geojson_obj,
                job.requested_start_date,
                job.requested_end_date,
                NDVI_EVALSCRIPT,
            )
            created, skipped, acquisition_dates = 0, 0, []
            for interval_data in response.get("data", []):
                try:
                    acq_date = self.parse_acquisition_date(
                        interval_data["interval"]["from"]
                    )
                    stats = self.extract_stats(interval_data)
                    already_exists = self.record_exists(
                        db_s, job.parcel_id, acq_date, job.metric_type
                    )
                    if already_exists:
                        logger.debug(
                            f"Record already exists for {job.parcel_id}"
                            f"on {acq_date} skiping"
                        )
                        skipped += 1
                        continue
                    self._create_raster_stat(
                        db_s,
                        job.parcel_id,
                        acq_date,
                        job.metric_type,
                        job.data_source_id,
                        stats,
                        interval_data,
                    )
                    created += 1
                    acquisition_dates.append(acq_date)
                except Exception as e:
                    # Logs but continue with other intervals
                    logger.error(
                        f"Failed to process interval for date "
                        f"{interval_data.get('interval', {}).get('from')}: {e}"
                    )
            if created > 0:
                job.status = "completed"
                job.actual_start_date = min(acquisition_dates)
                job.actual_end_date = max(acquisition_dates)
                db_s.commit()
            elif skipped > 0:
                job.status = "completed"  # All already existed
                db_s.commit()
            else:
                job.status = "partial"  # Requested data not available
                db_s.commit()
            job.records_created = created
            job.records_skipped = skipped
            job.completed_at = datetime.now(UTC)
            db_s.commit()

            if created > 0:
                self._update_parcel_metadata(
                    db_s, job.parcel_id, max(acquisition_dates)
                )

            logger.info(
                f"Job {job.uid} completed: {created} created, {skipped} skipped"
            )

            return job

        except Exception as e:
            job.status = "failed"
            job.error_message = str(e)
            job.completed_at = datetime.now(UTC)
            job.retry_count += 1
            db_s.commit()

            logger.exception(f"Job {job.uid} failed: {e}")
            raise

    def get_parcel_geometry(self, parcel_id: str) -> dict[str, Any]:
        with self.session_factory() as db_s:
            parcel = db_s.get(Parcel, parcel_id)
        if parcel is None:
            raise ValueError(f"parcel with id {parcel_id} is not found")
        if not parcel.is_active:
            raise ValueError(f"parcel with id {parcel_id} is not active")
        # convert PostGis to shapely
        polygon_shape = to_shape(parcel.geometry)
        # convert to geojson
        return {"type": "Polygon", "coordinates": [list(polygon_shape.exterior.coords)]}

    def parse_acquisition_date(self, acq_date: str) -> date:
        return datetime.fromisoformat(acq_date).date()

    def extract_stats(self, interval_data: dict[str, Any]) -> dict[str, Any]:
        stats = (
            interval_data.get("outputs", {})
            .get("default", {})
            .get("bands", {})
            .get("B0", {})
            .get("stats", {})
        )
        if not stats:
            raise ValueError("No statistics found in interval data")

        return stats

    def record_exists(
        self, db_s: Session, parcel_id: str, acquisition_date: date, metric_type: str
    ) -> bool:
        exist_stmt = select(RasterStats).where(
            RasterStats.acquisition_date == acquisition_date,
            RasterStats.parcel_id == parcel_id,
            RasterStats.metric_type == metric_type,
        )
        return db_s.scalar(exist_stmt) is not None

    def _create_raster_stat(
        self,
        db_s: Session,
        parcel_id: str,
        acquisition_date: date,
        metric_type: str,
        satellite_source_id: str,
        stats: dict[str, Any],
        raw_metadata: dict[str, Any],
    ) -> RasterStats:
        """
        Create a new raster_stats database record.

        Args:
            parcel_id: Parcel UUID
            acquisition_date: Date of satellite acquisition
            metric_type: Type of vegetation index (NDVI, NDMI, etc.)
            satellite_source: Data source name (sentinel-2-l2a, etc.)
            stats: Statistics dictionary from API response
            raw_metadata: Full interval data for debugging

        Returns:
            Created RasterStats instance (not yet committed)
        """
        raster_stat = RasterStats(
            parcel_id=parcel_id,
            acquisition_date=acquisition_date,
            data_source_id=satellite_source_id,
            metric_type=metric_type,
            mean_value=stats["mean"],
            min_value=stats["min"],
            max_value=stats["max"],
            std_dev=stats.get("stDev"),
            pixel_count=stats.get("sampleCount"),
            cloud_cover_percent=None,  # Not directly available in stats response
            raw_metadata=raw_metadata,
        )

        db_s.add(raster_stat)
        db_s.commit()
        return raster_stat

    def _update_parcel_metadata(self, db_s: Session, parcel_id: str, latest_date: date):
        """
        Update parcel's ingestion metadata after successful ingestion.

        Updates:
        - last_data_synced_at: Current timestamp
        - latest_acquisition_date: Most recent satellite date

        Args:
            parcel_id: Parcel UUID
            latest_date: Most recent acquisition date from this job
        """
        parcel = db_s.get(Parcel, parcel_id)

        if not parcel:
            logger.warning(f"Parcel {parcel_id} not found during metadata update")
            return
        parcel.last_data_synced_at = datetime.now(UTC)
        # Update latest acquisition date if newer
        if (
            parcel.latest_acquisition_date is None
            or latest_date > parcel.latest_acquisition_date
        ):
            parcel.latest_acquisition_date = latest_date
        logger.debug(
            f"Updated parcel {parcel_id} metadata: "
            f"latest_acquisition_date={latest_date}"
        )
