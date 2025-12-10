import sqlalchemy as sa
import sqlalchemy.orm as so

from app.core.database import Base


class DataSource(Base):
    """
    Represent satellite data source entity.
    """

    __tablename__ = "data_sources"

    uid: so.Mapped[str] = so.mapped_column(sa.String(36), primary_key=True)

    name: so.Mapped[str] = so.mapped_column(
        sa.String(50),
        default="sentinel-2-l2a",
        unique=True,
        nullable=False,
        comment="sentinel-2-l2a, landsat-8, modis",
    )
    # How often does new data become available? cadence
    revisit_frequency_days: so.Mapped[int] = so.mapped_column(
        sa.Integer,
        nullable=False,
        comment="Satellite revisit frequency (5 days for Sentinel-2)",
    )

    # How long after capture is data available?
    availability_lag_days: so.Mapped[int] = so.mapped_column(
        sa.Integer,
        nullable=False,
        comment="Processing delay (1-2 days for Sentinel Hub)",
    )

    # How often should we check for new data?
    sync_frequency_days: so.Mapped[int] = so.mapped_column(
        sa.Integer,
        nullable=False,
        default=7,
        comment="How often to run ingestion (7 days default)",
    )
    api_endpoint: so.Mapped[str] = so.mapped_column(sa.String(255))
    max_cloud_coverage: so.Mapped[int] = so.mapped_column(sa.Integer, default=30)

    is_active: so.Mapped[bool] = so.mapped_column(sa.Boolean, default=True)
