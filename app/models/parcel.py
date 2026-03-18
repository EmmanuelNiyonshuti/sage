from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
import sqlalchemy.orm as so
from geoalchemy2 import Geometry

from app.core.database import Base

if TYPE_CHECKING:
    from .alerts import Alerts
    from .ingestion_job import IngestionJob
    from .raster_stats import RasterStats
    from .time_series import TimeSeries
    from .user import User


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
        sa.DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: so.Mapped[datetime] = so.mapped_column(
        sa.DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
    is_active: so.Mapped[bool] = so.mapped_column(
        sa.Boolean, default=True, comment="Whether to actively monitor this parcel"
    )

    last_data_synced_at: so.Mapped[datetime | None] = so.mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
        comment="Timestamp of last successful data sync(any job)",
    )
    latest_acquisition_date: so.Mapped[date | None] = so.mapped_column(
        sa.Date, nullable=True, comment="Most recent acquisition_date in raster_stats"
    )
    next_sync_scheduled_at: so.Mapped[datetime | None] = so.mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="When to schedule next ingestion job",
    )

    auto_sync_enabled: so.Mapped[bool] = so.mapped_column(
        sa.Boolean, default=True, nullable=True
    )
    owner_id: so.Mapped[str] = so.mapped_column(
        sa.String(36),
        sa.ForeignKey("users.uid", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    owner: so.Mapped[User] = so.relationship(back_populates="parcels")

    raster_stats: so.Mapped[list[RasterStats]] = so.relationship(
        back_populates="parcel", cascade="all, delete-orphan"
    )
    ingestion_jobs: so.Mapped[list[IngestionJob]] = so.relationship(
        back_populates="parcel", cascade="all, delete-orphan"
    )
    time_series: so.Mapped[list[TimeSeries]] = so.relationship(
        back_populates="parcel", cascade="all, delete-orphan"
    )
    alerts: so.Mapped[list[Alerts]] = so.relationship(
        back_populates="parcel", cascade="all, delete-orphan"
    )


# #  be replaced by a trigger instead, was shifted to the database level, gotta run migrations to add the trigger and function, see alembic/versions/2025_12_06_1339-b06b792da046_initial_migration.py
# @sa.event.listens_for(Parcel, "before_insert")
# # @sa.event.listens_for(Parcel, "before_update")
# def calculate_parcel_area(mapper, connection, target):
#     """need to intercept before insert into parcels table and ask postgis to calculate real world area of a polygon geometry, and store it in hectares divides by 10_000 to get hectares (1 hectare = 10,000 sqm)


#     """
#     if target.geometry is not None:
#         result = connection.execute(
#             sa.select(sa.func.ST_Area(sa.cast(target.geometry, Geography)) / 10_000)
#         ).scalar()
#         target.area_hectares = round(float(result), 4) if result else None
