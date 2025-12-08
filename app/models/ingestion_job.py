import uuid
from datetime import UTC, date, datetime

import sqlalchemy as sa
import sqlalchemy.orm as so
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import Base


class IngestionJob(Base):
    """
    Represents a single ingestion job execution.

    Each job attempts to fetch data for a specific time window.
    Job can succeed, fail, partially complete, or be retried.
    """

    __tablename__ = "ingestion_jobs"
    uid: so.Mapped[str] = so.mapped_column(
        sa.String(60), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    parcel_id: so.Mapped[str] = so.mapped_column(
        sa.String(60),
        sa.ForeignKey("parcels.uid", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # What date range did we REQUEST?
    requested_start_date: so.Mapped[date] = so.mapped_column(
        sa.Date, nullable=False, comment="Start of requested window"
    )

    requested_end_date: so.Mapped[date] = so.mapped_column(
        sa.Date, nullable=False, comment="End of requested window"
    )

    # What date range did we ACTUALLY get?
    actual_start_date: so.Mapped[date | None] = so.mapped_column(
        sa.Date, nullable=True, comment="Earliest acquisition date retrieved"
    )

    actual_end_date: so.Mapped[date | None] = so.mapped_column(
        sa.Date, nullable=True, comment="Latest acquisition date retrieved"
    )

    # JOB STATE
    status: so.Mapped[str] = so.mapped_column(
        sa.String(20),
        nullable=False,
        default="pending",
        index=True,
        comment="pending, running, completed, partial, failed",
    )

    records_created: so.Mapped[int] = so.mapped_column(
        sa.Integer,
        default=0,
        nullable=False,
        comment="Number of raster_stats records created",
    )

    records_skipped: so.Mapped[int] = so.mapped_column(
        sa.Integer,
        default=0,
        nullable=False,
        comment="Number of records skipped (already exist)",
    )

    error_message: so.Mapped[str | None] = so.mapped_column(
        sa.Text, nullable=True, comment="Error message if job failed"
    )

    retry_count: so.Mapped[int] = so.mapped_column(
        sa.Integer, default=0, nullable=False, comment="Number of retry attempts"
    )

    # ============ TIMING ============

    created_at: so.Mapped[datetime] = so.mapped_column(
        sa.DateTime, default=datetime.now(UTC), nullable=False
    )

    started_at: so.Mapped[datetime | None] = so.mapped_column(
        sa.DateTime, nullable=True, comment="When job execution started"
    )

    completed_at: so.Mapped[datetime | None] = so.mapped_column(
        sa.DateTime, nullable=True, comment="When job finished (success or failure)"
    )

    # ============ METADATA ============

    job_type: so.Mapped[str] = so.mapped_column(
        sa.String(20), nullable=False, comment="backfill, periodic, manual, retry"
    )

    data_source_id: so.Mapped[str] = so.mapped_column(
        sa.String(36), sa.ForeignKey("data_sources.uid"), nullable=False, index=True
    )

    # available in raster stats
    metric_type: so.Mapped[str] = so.mapped_column(
        sa.String(20), default="NDVI", nullable=False, comment="Which index to compute"
    )

    # Store full context for debugging
    execution_metadata: so.Mapped[dict | None] = so.mapped_column(
        JSONB, comment="Full execution context, API responses, etc."
    )

    # Relationships
    parcel: so.Mapped["Parcel"] = so.relationship(back_populates="ingestion_jobs")  # noqa

    __table_args__ = (
        sa.Index("idx_jobs_status_created", "status", "created_at"),
        sa.Index("idx_jobs_parcel_status", "parcel_id", "status"),
    )
