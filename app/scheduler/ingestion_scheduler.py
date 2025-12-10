"""
Ingestion scheduler using APScheduler.

Runs background jobs to process parcels that need data updates.
"""

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.core.database import session_factory
from app.services.ingestion_engine import IngestionEngine

logger = logging.getLogger(__name__)


class IngestionScheduler:
    """
    Manages scheduled ingestion jobs.

    - Start/stop the scheduler
    - Schedule periodic parcel processing
    - Handle job failures gracefully
    """

    def __init__(self):
        self.scheduler: BackgroundScheduler | None = None
        self._is_running = False

    def start(self, check_interval_hours: int = 1):
        if self._is_running:
            logger.warning("Scheduler already running, ignoring start request")
            return

        logger.info("Starting ingestion scheduler")
        self.scheduler = BackgroundScheduler(
            job_defaults={
                "coalesce": True,  # If missed, run once (not multiple times)
                "max_instances": 1,  # Only one instance of each job at a time
                "misfire_grace_time": 300,  # 5 minutes grace for missed jobs
            },
            timezone="UTC",
        )

        # Schedule the periodic job
        self.scheduler.add_job(
            func=self._process_due_parcels_job,
            trigger=IntervalTrigger(hours=check_interval_hours),
            id="process_due_parcels",
            name="Process Due Parcels",
            replace_existing=True,
        )

        self.scheduler.start()
        self._is_running = True

        logger.info(
            f"Scheduler started - checking for due parcels every {check_interval_hours} hour(s)"
        )

    def stop(self):
        """Stop the schedulers."""
        if not self._is_running or not self.scheduler:
            logger.warning("Scheduler not running, ignoring stop request")
            return

        logger.info("Stopping ingestion scheduler")

        self.scheduler.shutdown(wait=True)
        self._is_running = False

        logger.info("Scheduler stopped")

    def _process_due_parcels_job(self):
        """
        Job function that processes due parcels.

        This is called by APScheduler at scheduled intervals.
        Creates its own database session.
        """
        logger.info("Scheduler triggered: checking for due parcels")

        try:
            engine = IngestionEngine(session_factory)
            results = engine.process_due_parcels()

            logger.info(
                f"Scheduled job completed: "
                f"{results['succeeded']} succeeded, "
                f"{results['failed']} failed, "
                f"{results['skipped']} skipped"
            )

        except Exception as e:
            logger.exception(f"Scheduled job failed: {e}")

    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self._is_running

    def get_jobs(self) -> list:
        """Get list of scheduled jobs (for monitoring)."""
        if not self.scheduler:
            return []
        return self.scheduler.get_jobs()


ingestion_scheduler = IngestionScheduler()
