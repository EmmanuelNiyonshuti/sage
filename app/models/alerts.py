import uuid
from datetime import UTC, datetime

import sqlalchemy as sa
import sqlalchemy.orm as so
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import Base


class Alerts(Base):
    """Detected anomalies and issues requiring attention"""

    __tablename__ = "alerts"

    # Primary key
    uid: so.Mapped[str] = so.mapped_column(
        sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # Foreign key
    field_id: so.Mapped[str] = so.mapped_column(
        sa.String(36),
        sa.ForeignKey("fields.uid", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Alert classification
    alert_type: so.Mapped[str] = so.mapped_column(
        sa.String(100),
        nullable=False,
        comment="drought_risk, vegetation_decline, anomaly, pest_stress, etc.",
    )

    severity: so.Mapped[str] = so.mapped_column(
        sa.String(20), nullable=False, comment="low, medium, high, critical"
    )

    # Human-readable message
    message: so.Mapped[str] = so.mapped_column(sa.Text, nullable=False)

    # Lifecycle
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

    # Additional context (flexible storage)
    alerts_data: so.Mapped[dict | None] = so.mapped_column(
        JSONB, comment="Store alert-specific data like thresholds, values, etc."
    )

    # Relationships
    field: so.Mapped["Field"] = so.relationship(back_populates="alerts")  # noqa 821

    __table_args__ = (
        sa.Index("idx_alerts_status", "status"),
        sa.Index("idx_alerts_field_status", "field_id", "status"),
    )
