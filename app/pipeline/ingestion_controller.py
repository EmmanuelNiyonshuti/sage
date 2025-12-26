"""
Trigger and manage ingestion jobs for parcels.
"""

import logging
from datetime import UTC, date, datetime, timedelta
from typing import List

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.models import DataSource, IngestionJob, Parcel

from .ingestion_engine import IngestionEngine

logger = logging.getLogger(__name__)


class UpToDateError(Exception):
    pass


class IngestionController:
    """
    Orchestrates/organize or coordinates ingestion jobs for parcels.
    - Calculate what data to fetch and when
    - Create ingestion jobs
    - Execute jobs through Ingestion
    """

    def __init__(self, session_factory):
        self.session_factory = session_factory
        self.ingestion_engine = IngestionEngine(self.session_factory)

    def trigger_initial_backfill(
        self, parcel_id: str, lookback_days: int = 90
    ) -> IngestionJob:
        """
        Trigger initial historical data backfill for a newly created parcel.

        This creates and executes a job to fetch historical data.

        Args:
            parcel_id: Parcel UUID
            lookback_days: How many days of history to fetch (default: 90)

        Returns:
            Completed IngestionJob

        Raises:
            ValueError: If parcel not found
        """
        with self.session_factory() as db_s:
            parcel = db_s.get(Parcel, parcel_id)
            if parcel is None:
                raise ValueError(f"parcel with {parcel_id} not found")
            data_source = self._get_active_data_source(db_s)
            safe_end_dt = self._calculate_safe_end_date(data_source)
            start_dt = safe_end_dt - timedelta(days=lookback_days)

            job = IngestionJob(
                parcel_id=parcel_id,
                requested_start_date=start_dt,
                requested_end_date=safe_end_dt,
                job_type="backfill",
                data_source_id=data_source.uid,
            )
            db_s.add(job)
            db_s.commit()
            logger.info(f"Created backfill job {job.uid}")

            # Execute job
            try:
                completed_job = self.ingestion_engine.ingest_with_job_tracking(
                    db_s, job
                )
                logger.info(
                    f"Backfill completed for {parcel.name}: "
                    f"{completed_job.records_created} records created"
                )
                return completed_job
            except Exception:
                logger.exception(f"Backfill failed for parcel {parcel_id}")
                raise

    def process_due_parcels(self) -> dict:
        """
        Process all parcels that are due for ingestion.

        This is called by the scheduler to check for parcels needing updates.

        Returns:
            Summary dict with counts: total, succeeded, failed, skipped
        """
        logger.info("Starting scheduled ingestion check")

        with self.session_factory() as db_s:
            due_parcels = self._get_due_parcels(db_s)

            due_parcels_len = len(due_parcels)
            logger.info(f"Found {due_parcels_len} parcels due for ingestion")

            results = {
                "total": due_parcels_len,
                "succeeded": 0,
                "failed": 0,
                "skipped": 0,
            }

            for parcel in due_parcels:
                try:
                    self._process_single_parcel(db_s, parcel)
                    results["succeeded"] += 1

                except UpToDateError:
                    results["skipped"] += 1

                except Exception:
                    logger.exception(f"Failed to process parcel {parcel.uid}")
                    results["failed"] += 1

            logger.info(
                f"Scheduled ingestion complete: "
                f"{results['succeeded']} succeeded, "
                f"{results['failed']} failed, "
                f"{results['skipped']} skipped"
            )

            return results

    def _get_due_parcels(self, db_s: Session) -> List[Parcel]:
        """
        Get list of parcels that need ingestion.

        Returns parcels where:
        - Active and sync enabled
        - Next sync time is in the past (or null for new parcels)

        Returns:
            List of Parcel instances
        """
        now = datetime.now(UTC)
        stmt = select(Parcel).where(
            and_(
                Parcel.is_active,
                Parcel.auto_sync_enabled,
                (Parcel.next_sync_scheduled_at <= now)
                | (Parcel.next_sync_scheduled_at.is_(None)),
            )
        )

        return list(db_s.execute(stmt).scalars().all())

    def _process_single_parcel(self, db_s: Session, parcel: Parcel):
        """
        Process ingestion for a single parcel.

        Creates a job and executes it.

        Args:
            parcel: Parcel to process

        Raises:
            UpToDateError: If parcel is already current
        """

        try:
            data_source = self._get_active_data_source(db_s)
            start_dt, end_dt = self._determine_fetch_window(parcel, data_source)
            logger.info(
                f"Processing parcel {parcel.uid} ({parcel.name}) from data_source {data_source.name}"
            )
        except UpToDateError as e:
            logger.info(str(e))
            # Schedule next check
            self._schedule_next_sync(parcel, data_source)
            raise
        job = IngestionJob(
            parcel_id=parcel.uid,
            requested_start_date=start_dt,
            requested_end_date=end_dt,
            job_type="periodic",
            data_source_id=data_source.uid,
        )
        db_s.add(job)
        db_s.commit()
        try:
            completed_job = self.ingestion_engine.ingest_with_job_tracking(db_s, job)
            self._schedule_next_sync(db_s, parcel, data_source)

            logger.info(
                f"Processed {parcel.name}: {completed_job.records_created} records"
            )

        except Exception:
            logger.exception(f"Failed to process parcel {parcel.uid}")
            raise

    def _get_active_data_source(
        self, db_s, data_source_name: str = "sentinel-2-l2a"
    ) -> DataSource:
        """
        Get the active data source (currently sentinel-2-l2a).

        Returns:
            DataSource instance

        Raises:
            ValueError: If no active data source found
        """
        stmt = select(DataSource).where(
            DataSource.name == data_source_name, DataSource.is_active.is_(True)
        )
        data_source = db_s.scalar(stmt)
        if not data_source:
            raise ValueError("No active data source found. Run seeds first.")
        return data_source

    def _calculate_safe_end_date(self, data_source: DataSource) -> date:
        """
        Calculate safe end date accounting for availability lag.

        Example:
        - Today: Dec 10
        - Sentinel-2 has 2-day lag
        - Safe end date: Dec 8 (today - 2 days)
        Args:
            data_source: DataSource configuration

        Returns:
            Safe end date
        """
        today = date.today()
        safe_end_date = today - timedelta(days=data_source.availability_lag_days)

        logger.debug(
            f"Calculated safe end date: {safe_end_date} "
            f"(today={today}, lag={data_source.availability_lag_days} for {data_source.name})"
        )

        return safe_end_date

    def _determine_fetch_window(
        self, parcel: Parcel, data_source: DataSource
    ) -> tuple[date, date]:
        """
        Determine what date range to fetch for a parcel.

        1. If parcel has data, fetch from (latest_date + 1) to safe_end_date
        2. If no data, backfill from (today - 90 days) to safe_end_date
        3. If already up-to-date, raise UpToDateError

        Args:
            parcel: Parcel to fetch data for
            data_source: DataSource configuration

        Returns:
            tuple: (start_date, end_date)

        Raises:
            UpToDateError: If parcel is already up-to-date
        """
        safe_end_dt = self._calculate_safe_end_date(data_source)

        if parcel.latest_acquisition_date:
            # Incremental fetch
            start_dt = parcel.latest_acquisition_date + timedelta(days=1)
        else:
            # Initial backfill: get last 90 days default
            start_dt = safe_end_dt - timedelta(days=90)

        if start_dt > safe_end_dt:
            raise UpToDateError(
                f"Parcel {parcel.uid} is already up-to-date "
                f"(latest: {parcel.latest_acquisition_date}, "
                f"safe_end: {safe_end_dt})"
            )

        return start_dt, safe_end_dt

    def _schedule_next_sync(
        self, db_s: Session, parcel: Parcel, data_source: DataSource
    ):
        """
        Schedule the next sync time for a parcel.

        Args:
            parcel: Parcel to schedule
            data_source: DataSource configuration
        """
        next_sync = datetime.now(UTC) + timedelta(days=data_source.sync_frequency_days)
        parcel.next_sync_scheduled_at = next_sync
        logger.debug(f"Scheduled next sync for {parcel.uid} at {next_sync}")
