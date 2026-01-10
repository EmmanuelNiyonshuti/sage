import uuid
from datetime import UTC, datetime

import sqlalchemy as sa
import sqlalchemy.orm as so
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import Base


class Alerts(Base):
    """Represents Detected anomalies and issues"""

    __tablename__ = "alerts"
    uid: so.Mapped[str] = so.mapped_column(
        sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    parcel_id: so.Mapped[str] = so.mapped_column(
        sa.String(36),
        sa.ForeignKey("parcels.uid", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    alert_type: so.Mapped[str] = so.mapped_column(
        sa.String(100),
        nullable=False,
        comment="drought_risk, vegetation_decline.",
    )

    severity: so.Mapped[str] = so.mapped_column(
        sa.String(20), nullable=False, comment="low, medium, high, critical"
    )
    message: so.Mapped[str] = so.mapped_column(sa.Text, nullable=False)

    detected_at: so.Mapped[datetime] = so.mapped_column(
        sa.DateTime, default=datetime.now(UTC), nullable=False, index=True
    )

    status: so.Mapped[str | None] = so.mapped_column(
        sa.String(20),
        default="active",
        nullable=False,
        comment="active, resolved, dismissed",
    )

    resolved_at: so.Mapped[datetime | None] = so.mapped_column(sa.DateTime)

    alerts_data: so.Mapped[dict | None] = so.mapped_column(
        JSONB, comment="Store alert-specific data like thresholds, values, etc."
    )

    parcel: so.Mapped["Parcel"] = so.relationship(back_populates="alerts")  # noqa 821

    __table_args__ = (
        sa.Index("idx_alerts_status", "status"),
        sa.Index("idx_alerts_parcel_status", "parcel_id", "status"),
    )
