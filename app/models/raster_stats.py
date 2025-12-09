import uuid
from datetime import UTC, date, datetime

import sqlalchemy as sa
import sqlalchemy.orm as so
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import Base


class RasterStats(Base):
    """Raw statistics from satellite imagery processing"""

    __tablename__ = "raster_stats"

    uid: so.Mapped[str] = so.mapped_column(
        sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    parcel_id: so.Mapped[str] = so.mapped_column(
        sa.String(36),
        sa.ForeignKey("parcels.uid", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # When was this data acquired?
    acquisition_date: so.Mapped[date] = so.mapped_column(
        sa.Date,
        nullable=False,
        index=True,  # Index for time-range queries
    )

    # What metric are we looking for?
    metric_type: so.Mapped[str] = so.mapped_column(
        sa.String(50), nullable=False, comment="NDVI, EVI, NDMI, SAVI, LAI"
    )

    # The actual statistics
    mean_value: so.Mapped[float] = so.mapped_column(
        sa.Numeric(10, 6),  # 6 decimal places for precision
        nullable=False,
    )
    min_value: so.Mapped[float] = so.mapped_column(sa.Numeric(10, 6))
    max_value: so.Mapped[float] = so.mapped_column(sa.Numeric(10, 6))
    std_dev: so.Mapped[float | None] = so.mapped_column(sa.Numeric(10, 6))

    # Data quality info
    cloud_cover_percent: so.Mapped[float | None] = so.mapped_column(
        sa.Numeric(5, 2),  # 0.00 to 100.00
        comment="Percentage of cloud cover in the image",
    )
    pixel_count: so.Mapped[int | None] = so.mapped_column(
        sa.Integer, comment="Number of valid pixels processed"
    )

    # Processing metadata
    processed_at: so.Mapped[datetime] = so.mapped_column(
        sa.DateTime, default=datetime.now(UTC), nullable=False
    )

    # Optional: store raw response for debugging
    raw_metadata: so.Mapped[dict | None] = so.mapped_column(
        JSONB, comment="Store full response for debugging"
    )

    # Relationships
    parcel: so.Mapped["Parcel"] = so.relationship(back_populates="raster_stats")  # noqa
    # Which satellite?
    data_source_id: so.Mapped[str] = so.mapped_column(
        sa.String(36), sa.ForeignKey("data_sources.uid"), nullable=False, index=True
    )

    # Composite unique constraint - prevent duplicate entries
    __table_args__ = (
        sa.UniqueConstraint(
            "parcel_id", "acquisition_date", "metric_type", name="uq_parcel_date_index"
        ),
        sa.Index("idx_raster_parcel_date", "parcel_id", "acquisition_date"),
    )
