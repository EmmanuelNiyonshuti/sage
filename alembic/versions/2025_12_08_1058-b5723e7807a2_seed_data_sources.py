"""seed data_sources

Revision ID: b5723e7807a2
Revises: 7b2476fba1e8
Create Date: 2025-12-08 10:58:56.241911+00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.sql import column, table

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b5723e7807a2"
down_revision: Union[str, Sequence[str], None] = "7b2476fba1e8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Seed data sources."""

    # Define table structure for raw SQL insert
    data_sources = table(
        "data_sources",
        column("uid", sa.String),
        column("name", sa.String),
        column("revisit_frequency_days", sa.Integer),
        column("availability_lag_days", sa.Integer),
        column("sync_frequency_days", sa.Integer),
        column("api_endpoint", sa.String),
        column("max_cloud_coverage", sa.Integer),
        column("is_active", sa.Boolean),
    )

    # Insert seed data
    conn = op.get_bind()

    seeds = [
        {
            "uid": "sentinel-2-l2a",  # Uses name as uid for simplicity
            "name": "sentinel-2-l2a",
            "revisit_frequency_days": 5,
            "availability_lag_days": 2,
            "sync_frequency_days": 7,
            "api_endpoint": "https://services.sentinel-hub.com/api/v1/statistics",
            "max_cloud_coverage": 30,
            "is_active": True,
        },
        {
            "uid": "landsat-ot-l1",
            "name": "landsat-ot-l1",
            "revisit_frequency_days": 16,
            "availability_lag_days": 1,
            "sync_frequency_days": 16,
            "api_endpoint": "https://services-uswest2.sentinel-hub.com/api/v1/statistics",
            "max_cloud_coverage": 30,
            "is_active": True,
        },
    ]

    # Check what already exists
    existing = conn.execute(sa.text("SELECT name FROM data_sources")).fetchall()
    existing_names = {row[0] for row in existing}

    # Insert only new ones
    to_insert = [s for s in seeds if s["name"] not in existing_names]

    if to_insert:
        op.bulk_insert(data_sources, to_insert)
        print(f"Seeded {len(to_insert)} data sources")
    else:
        print("All data sources already exist, skipping")


def downgrade() -> None:
    """Remove seed data (optional)."""
    op.execute(
        """
        DELETE FROM data_sources 
        WHERE name IN ('sentinel-2-l2a', 'landsat-ot-l1')
        """
    )
