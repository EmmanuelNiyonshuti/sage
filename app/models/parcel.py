import uuid
from datetime import UTC, date, datetime

import sqlalchemy as sa
import sqlalchemy.orm as so
from geoalchemy2 import Geography, Geometry

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
    area_hectares: so.Mapped[float | None] = so.mapped_column(
        sa.Numeric(10, 4),  # e.g 999999.9999 hectares
        nullable=True,
    )
    soil_type: so.Mapped[str | None] = so.mapped_column(sa.String(100))
    crop_type: so.Mapped[str | None] = so.mapped_column(sa.String(100))
    irrigation_type: so.Mapped[str | None] = so.mapped_column(
        sa.String(50), comment="rainfed, irrigated, mixed"
    )

    created_at: so.Mapped[datetime] = so.mapped_column(
        sa.DateTime, default=datetime.now(UTC), nullable=False
    )
    updated_at: so.Mapped[datetime] = so.mapped_column(
        sa.DateTime,
        default=datetime.now(UTC),
        onupdate=datetime.now(UTC),
        nullable=False,
    )
    is_active: so.Mapped[bool] = so.mapped_column(
        sa.Boolean, default=True, comment="Whether to actively monitor this parcel"
    )

    last_data_synced_at: so.Mapped[datetime | None] = so.mapped_column(
        sa.DateTime,
        nullable=True,
        comment="Timestamp of last successful data sync(any job)",
    )
    latest_acquisition_date: so.Mapped[date | None] = so.mapped_column(
        sa.Date, nullable=True, comment="Most recent acquisition_date in raster_stats"
    )
    next_sync_scheduled_at: so.Mapped[datetime | None] = so.mapped_column(
        sa.DateTime,
        nullable=True,
        index=True,
        comment="When to schedule next ingestion job",
    )

    auto_sync_enabled: so.Mapped[bool] = so.mapped_column(
        sa.Boolean, default=True, nullable=True
    )

    raster_stats: so.Mapped[list["RasterStats"]] = so.relationship(  # noqa: F821
        back_populates="parcel", cascade="all, delete-orphan"
    )
    ingestion_jobs: so.Mapped[list["IngestionJob"]] = so.relationship(  # noqa
        back_populates="parcel", cascade="all, delete-orphan"
    )
    time_series: so.Mapped[list["TimeSeries"]] = so.relationship(  # noqa: F821
        back_populates="parcel", cascade="all, delete-orphan"
    )
    alerts: so.Mapped[list["Alerts"]] = so.relationship(  # noqa: F821
        back_populates="parcel", cascade="all, delete-orphan"
    )


@sa.event.listens_for(Parcel, "before_insert")
# @sa.event.listens_for(Parcel, "before_update")
def calculate_parcel_area(mapper, connection, target):
    """Calculate area in hectares from geometry."""
    if target.geometry is not None:
        result = connection.execute(
            sa.select(sa.func.ST_Area(sa.cast(target.geometry, Geography)) / 10000)
        ).scalar()
        target.area_hectares = round(float(result), 4) if result else None
