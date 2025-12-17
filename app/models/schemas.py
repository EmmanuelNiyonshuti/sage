from datetime import date, datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.utils import geojson_to_shapely, shapely_to_wkbelement, wkb_to_geojson


class GeometrySchema(BaseModel):
    """GeoJSON Polygon geometry."""

    model_config = ConfigDict(populate_by_name=True)
    geometry_type: Annotated[
        str, Field(pattern="^Polygon$", alias="type", serialization_alias="type")
    ]
    coordinates: list[list[list[float]]]

    @field_validator("coordinates")
    @classmethod
    def validate_polygon(cls, v):
        """Validate polygon structure."""
        if not v or not v[0]:
            raise ValueError("Polygon must have at least one ring")

        exterior_ring = v[0]
        if len(exterior_ring) < 4:
            raise ValueError("Polygon must have at least 4 points")
        if exterior_ring[0] != exterior_ring[-1]:
            raise ValueError("Polygon must be closed (first == last point)")
        for point in exterior_ring:
            if len(point) != 2:
                raise ValueError("Each coordinate must be [longitude, latitude]")
            lng, lat = point
            if not (-180 <= lng <= 180):
                raise ValueError(
                    f"Longitude {lng} out of range [-180, 180]"
                )  # 180 degrees E  and -180 degrees W
            if not (-90 <= lat <= 90):
                raise ValueError(
                    f"Latitude {lat} out of range [-90, 90]"
                )  # 90 degrees north and -90 degrees south

        return v


class ParcelCreate(BaseModel):
    """Schema for creating a new field."""

    name: Annotated[str, Field(min_length=5, max_length=255)]
    geometry: Any

    crop_type: Annotated[str | None, Field(min_length=3, max_length=100)]
    soil_type: Annotated[str | None, Field(min_length=3, max_length=100)]
    irrigation_type: Literal["rainfed", "irrigated", "mixed"] | None = None

    @field_validator("geometry", mode="before")
    @classmethod
    def convert_geojson_to_wkb(cls, v):
        validated_geojson = GeometrySchema.model_validate(v)
        shapely_obj = geojson_to_shapely(validated_geojson.model_dump(by_alias=True))
        return shapely_to_wkbelement(shapely_obj)


class ParcelUpdate(BaseModel):
    name: Annotated[str, Field(min_length=5, max_length=255)]
    crop_type: Annotated[str | None, Field(min_length=3, max_length=100)]
    soil_type: Annotated[str | None, Field(min_length=3, max_length=100)]
    irrigation_type: Literal["rainfed", "irrigated", "mixed"] | None = None
    is_active: bool | None = None


class ParcelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    uid: str
    name: str
    geometry: dict[str, Any]  # GeoJSON
    area_hectares: float | None
    crop_type: str | None
    soil_type: str | None
    irrigation_type: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @field_validator("geometry", mode="before")
    @classmethod
    def convert_geometry_to_geojson(cls, v) -> dict[str, Any] | None:
        """Convert WKB geometry to geojson"""
        if v is None:
            return None
        if isinstance(v, dict):
            return v
        return wkb_to_geojson(v)


class ParcelListResponse(BaseModel):
    """Schema for list of fields."""

    parcels: list[ParcelResponse]
    total: int
    limit: int
    offset: int


class ParcelStatsRequest(BaseModel):
    parcel_id: str


class RawRasterStatsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    metric_type: str
    mean_value: float
    max_value: float
    min_value: float
    std_dev: float
    processed_at: datetime
    acquisition_date: datetime


class ParcelStatsListResponse(ParcelStatsRequest):
    parcel_id: str
    stats: list[RawRasterStatsOut]
    total: int | None = None
    limit: int
    offset: int


class TimeSeriesStats(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    metric_type: str
    time_period: str
    start_date: date
    end_date: date
    value: float | int
    change_from_previous: float | None
    is_anomaly: bool | None


class TimeSeriesResponse(BaseModel):
    parcel_id: str
    stats: list[TimeSeriesStats]
    total: int | None = None
    limit: int
    offset: int


class ParcelListParams(BaseModel):
    """Query parameters for listing parcels."""

    limit: Annotated[int, Field(ge=1, le=100)] = 50
    offset: Annotated[int, Field(ge=0)] = 0
    is_active: bool | None = None
    crop_type: str | None = None
    search: str | None = Field(None, description="Search by parcel name")
