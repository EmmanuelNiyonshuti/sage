from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
import sqlalchemy.orm as so

from app.core.database import Base

if TYPE_CHECKING:
    from .parcel import Parcel


class User(Base):
    """Represents someone who adds a parcel boundary"""

    __tablename__ = "users"

    uid: so.Mapped[str] = so.mapped_column(
        sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    email: so.Mapped[str] = so.mapped_column(sa.String(255), nullable=False)
    api_key_hash: so.Mapped[str] = so.mapped_column(sa.String)
    is_verified: so.Mapped[bool] = so.mapped_column(sa.Boolean, default=False)

    parcels: so.Mapped[list[Parcel]] = so.relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )

    created_at: so.Mapped[datetime] = so.mapped_column(
        sa.DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    # class EmailVerification(Base):
    """
    Represents an email verification table, for all email verifications for a user.
    """

    # __tablename__ = "email_verifications"

    # uid: so.Mapped[str] = so.mapped_column(
    #     sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    # )
    # token: so.Mapped[str] = so.mapped_column(
    #     sa.String,
    # )
