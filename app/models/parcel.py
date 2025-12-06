import uuid
from datetime import UTC, datetime

import sqlalchemy as sa
import sqlalchemy.orm as so
from geoalchemy2 import Geometry

from app.core.database import Base


class Parcel(Base):
    """Represents a land parcel entity"""

    __tablename__ = "parcels"

    uid: so.Mapped[str] = so.mapped_column(
        sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    name: so.Mapped[str] = so.mapped_column(sa.String(255), nullable=False)

    # Stores the(shape) polygon boundary using PostGIS
    geometry: so.Mapped[str] = so.mapped_column(
        Geometry(
            "POLYGON", srid=4326
        ),  # SRID(Spatial Reference System Identifier) 4326 = WGS84 (standard lat/long), defines how to convert coordinates into real-world locations
        nullable=False,
    )

    # Computed from geometry
    area_hectares: so.Mapped[float | None] = so.mapped_column(
        sa.Numeric(
            10, 4
        ),  # will store numbers with up to 10 total digits(precision), with 4 of them being after the decimal point(scale) e.g 999999.9999 hectares
        nullable=True,
    )

    # Farm characteristics
    soil_type: so.Mapped[str | None] = so.mapped_column(sa.String(100))
    crop_type: so.Mapped[str | None] = so.mapped_column(sa.String(100))
    irrigation_type: so.Mapped[str | None] = so.mapped_column(
        sa.String(50), comment="rainfed, irrigated, mixed"
    )

    # Metadata
    created_at: so.Mapped[datetime] = so.mapped_column(
        sa.DateTime, default=datetime.now(UTC), nullable=False
    )
    updated_at: so.Mapped[datetime] = so.mapped_column(
        sa.DateTime,
        default=datetime.now(UTC),
        onupdate=datetime.now(UTC),
        nullable=False,
    )

    # Status
    is_active: so.Mapped[bool] = so.mapped_column(
        sa.Boolean, default=True, comment="Whether to actively monitor this parcel"
    )

    # Relationships
    raster_stats: so.Mapped[list["RasterStats"]] = so.relationship(  # noqa: F821
        back_populates="parcel", cascade="all, delete-orphan"
    )
    time_series: so.Mapped[list["TimeSeries"]] = so.relationship(  # noqa: F821
        back_populates="parcel", cascade="all, delete-orphan"
    )
    alerts: so.Mapped[list["Alerts"]] = so.relationship(  # noqa: F821
        back_populates="parcel", cascade="all, delete-orphan"
    )
