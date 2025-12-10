import uuid
from datetime import UTC, datetime

import sqlalchemy as sa
import sqlalchemy.orm as so

from app.core.database import Base


class TimeSeries(Base):
    __tablename__ = "time_series"
    uid: so.Mapped[str] = so.mapped_column(
        sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    parcel_id: so.Mapped[str] = so.mapped_column(
        sa.String(36),
        sa.ForeignKey("parcels.uid", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    metric_type: so.Mapped[str] = so.mapped_column(
        sa.String(50),
        nullable=False,
        comment="ndvi_avg, ndmi_avg, rainfall_total, temperature_avg, etc.",
    )

    time_period: so.Mapped[str] = so.mapped_column(
        sa.String(20), nullable=False, comment="daily, weekly, monthly"
    )
    start_date: so.Mapped[datetime] = so.mapped_column(
        sa.Date, nullable=False, index=True
    )
    end_date: so.Mapped[datetime] = so.mapped_column(
        sa.Date, nullable=False, index=True
    )
    value: so.Mapped[float] = so.mapped_column(sa.Numeric(10, 6), nullable=False)
    change_from_previous: so.Mapped[float | None] = so.mapped_column(
        sa.Numeric(10, 6), comment="Percentage change from previous period"
    )
    is_anomaly: so.Mapped[bool] = so.mapped_column(
        sa.Boolean, default=False, comment="Flagged as statistically unusual"
    )
    created_at: so.Mapped[datetime] = so.mapped_column(
        sa.DateTime, default=datetime.now(UTC), nullable=False
    )
    parcel: so.Mapped["Parcel"] = so.relationship(back_populates="time_series")  # noqa
    __table_args__ = (
        sa.UniqueConstraint(
            "parcel_id",
            "metric_type",
            "time_period",
            "start_date",
            name="uq_timeseries_parcel_metric_period_date",
        ),
        sa.Index("idx_timeseries_parcel_dates", "parcel_id", "start_date", "end_date"),
    )
