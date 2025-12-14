"""
TimeSeries scheduler using APScheduler.

Runs background jobs to process parcels that need data updates.
"""

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.core.database import session_factory
from app.services.time_series_service import TimeSeriesService

logger = logging.getLogger(__name__)


class TimeSeriesScheduler:
    """
    Manages scheduled TimeSeries jobs.

    - Start/stop the scheduler
    - Schedule periodic parcel processing
    - Handle job failures gracefully
    """

    def __init__(self):
        self.scheduler: BackgroundScheduler | None = None
        self._is_running = False

    def start(self, check_interval_hours: int = 5):
        if self._is_running:
            logger.warning("Scheduler already running, ignoring start request")
            return

        logger.info("Starting TimeSeries scheduler")
        self.scheduler = BackgroundScheduler(
            job_defaults={
                "coalesce": True,
                "max_instances": 1,
                "misfire_grace_time": 300,
            },
            timezone="UTC",
        )

        # Schedule the periodic job
        self.scheduler.add_job(
            func=self._process_parcels_job,
            trigger=IntervalTrigger(seconds=check_interval_hours),
            id="generate_time_series",
            name="Generate Time Series",
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

        logger.info("Stopping TimeSeries scheduler")

        self.scheduler.shutdown(wait=True)
        self._is_running = False

        logger.info("Scheduler stopped")

    def _process_parcels_job(self):
        """
        Job function that processes due parcels.

        This is called by APScheduler at scheduled intervals.
        Creates its own database session.
        """
        logger.info("Scheduler triggered: checking for due parcels")

        try:
            time_series = TimeSeriesService(session_factory)
            results = time_series.process_all_parcels()

            logger.info(
                f"Scheduled job completed: "
                f"{results['total_parcels']} processed, "
                f"{results['failed']} failed, "
                f"{results['weekly_created']} weekly time series added"
                f"{results['monthly_created']} monthly time series added"
            )
        except Exception as e:
            logger.exception(f"Scheduled job failed: {e}")

    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self._is_running

    def get_jobs(self) -> list:
        """Get list of scheduled jobs"""
        if not self.scheduler:
            return []
        return self.scheduler.get_jobs()


time_series_scheduler = TimeSeriesScheduler()
