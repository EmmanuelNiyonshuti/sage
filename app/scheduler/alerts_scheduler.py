"""
TimeSeries scheduler using APScheduler.

Runs background jobs to process parcels that need data updates.
"""

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.core.database import session_factory
from app.pipeline.generate_alerts import GenerateAlerts

logger = logging.getLogger(__name__)


class GenerateAlertsScheduler:
    """
    Manages scheduled Alerts jobs.

    - Start/stop the scheduler
    - Schedule periodic parcel processing
    - Handle job failures
    """

    def __init__(self, interval_duration: dict = {"weeks": 4}):
        self.scheduler: BackgroundScheduler | None = None
        self._is_running = False
        self.interval_duration = interval_duration

    def start(self, interval: dict | None = None):
        if self._is_running:
            logger.warning("Scheduler already running, ignoring start request")
            return

        logger.info("Starting Alerts scheduler")
        self.scheduler = BackgroundScheduler(
            job_defaults={
                "coalesce": True,
                "max_instances": 1,
                "misfire_grace_time": 300,
            },
            timezone="UTC",
        )

        interval_trigger = interval or self.interval_duration
        self.scheduler.add_job(
            func=self._process_parcels_job,
            trigger=IntervalTrigger(**interval_trigger),
            id="generate_alerts",
            name="Generate Alerts",
            replace_existing=True,
        )

        self.scheduler.start()
        self._is_running = True
        interval_name, interval_duration = next(iter(interval_trigger.items()))
        logger.info(
            f"Scheduler started - generating alerts for all parcels every {interval_duration} {interval_name}"
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
            generate_alerts = GenerateAlerts(session_factory)
            results = generate_alerts.process_all_parcels()

            logger.info(
                f"Scheduled job completed: "
                f"{results['alerts_created']} alerts was created"
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


generate_alerts_scheduler = GenerateAlertsScheduler()
