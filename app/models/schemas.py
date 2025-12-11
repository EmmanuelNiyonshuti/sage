from datetime import datetime
from typing import Any

from geoalchemy2.shape import to_shape
from pydantic import BaseModel, ConfigDict, Field, field_validator


class GeometrySchema(BaseModel):
    """GeoJSON Polygon geometry."""

    type: str = Field(..., pattern="^Polygon$")  # geometry type, polygon
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

        # Check closed
        if exterior_ring[0] != exterior_ring[-1]:
            raise ValueError("Polygon must be closed (first == last point)")

        # Check coordinate format [lng, lat]
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

    name: str = Field(min_length=1, max_length=255)
    geometry: GeometrySchema

    crop_type: str | None = Field(None, max_length=100)
    soil_type: str | None = Field(None, max_length=100)
    irrigation_type: str | None = Field(None, pattern="^(rainfed|irrigated|mixed)$")


class ParcelUpdate(BaseModel):
    """Schema for updating a field."""

    name: str | None = Field(None, min_length=1, max_length=255)
    crop_type: str | None = None
    soil_type: str | None = None
    irrigation_type: str | None = None
    is_active: bool | None = None


class ParcelResponse(BaseModel):
    """Schema for field responses."""

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
    def convert_geometry_to_geojson(cls, v):
        """Convert WKB geometry to geojson"""
        if v is None:
            return None
        if isinstance(v, dict):
            return v

        shape_obj = to_shape(v)
        return {"type": "Polygon", "coordinates": [list(shape_obj.exterior.coords)]}


class ParcelListResponse(BaseModel):
    """Schema for list of fields."""

    fields: list[ParcelResponse]
    total: int


class ParcelStatsRequest(BaseModel):
    parcel_id: str


class RasterStatsOut(BaseModel):
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
    stats: list[RasterStatsOut]
    total: int
    limit: int
    offset: int
