import logging
from datetime import date, timedelta

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models import Alerts, Parcel, RasterStats, TimeSeries

logger = logging.getLogger(__name__)


class GenerateAlerts:
    """
    Generates alerts based on vegetation index

    - Vegetation decline: NDVI dropped significantly
    - Drought stress: Sustained low NDVI
    - Anomaly: Statistical outlier detected
    - No data: Missing recent satellite data
    """

    def __init__(self, session_factory):
        self.session_factory = session_factory

    def generate_alerts_for_parcel(self, db_session: Session, parcel_id: str) -> int:
        """
        Generate all applicable alerts for a parcel.

        Checks multiple conditions and creates alerts as needed.

        Args:
            parcel_id: Parcel UUID

        Returns:
            Number of new alerts created
        """
        logger.info(f"Generating alerts for parcel {parcel_id}")

        created_count = 0

        if self._check_vegetation_decline(db_session, parcel_id):
            created_count += 1

        if self._check_drought_stress(db_session, parcel_id):
            created_count += 1
        if self._check_anomalies(db_session, parcel_id):
            created_count += 1
        if self._check_stale_data(db_session, parcel_id):
            created_count += 1

        logger.info(f"Created {created_count} alerts for parcel {parcel_id}")
        return created_count

    def process_all_parcels(self) -> dict:
        """
        Generate alerts for all active parcels.

        Called by scheduler.

        Returns:
            Summary
        """
        logger.info("Generating alerts for all parcels")
        with self.session_factory() as db_s:
            stmt = select(Parcel).where(Parcel.is_active.is_(True))
            parcels = db_s.execute(stmt).scalars().all()

            results = {
                "total_parcels": len(parcels),
                "alerts_created": 0,
            }

            for parcel in parcels:
                try:
                    count = self.generate_alerts_for_parcel(db_s, parcel.uid)
                    results["alerts_created"] += count
                except Exception:
                    logger.exception(
                        f"Failed to generate alerts for parcel {parcel.uid}"
                    )

            logger.info(
                f"Alerts generation complete: {results['alerts_created']} alerts created"
            )

            return results

    def _check_vegetation_decline(self, db_session: Session, parcel_id: str) -> bool:
        """
        Alert if NDVI dropped >15% in last 2 weeks compared to previous 2 weeks.
        """
        # Get last 4 weeks of weekly time series
        stmt = (
            select(TimeSeries)
            .where(
                TimeSeries.parcel_id == parcel_id,
                TimeSeries.metric_type == "NDVI_avg",
                TimeSeries.time_period == "weekly",
            )
            .order_by(desc(TimeSeries.start_date))
            .limit(4)
        )

        recent_weeks = list(db_session.execute(stmt).scalars().all())
        if len(recent_weeks) < 2:
            return False

        current_avg = sum(w.value for w in recent_weeks[:2]) / 2
        if len(recent_weeks) >= 4:
            previous_avg = sum(w.value for w in recent_weeks[2:4]) / 2
        else:
            return False

        percent_change = ((current_avg - previous_avg) / previous_avg) * 100

        if percent_change < -15:
            if not self._active_alert_exists(parcel_id, "vegetation_decline"):
                self._create_alert(
                    parcel_id=parcel_id,
                    alert_type="vegetation_decline",
                    severity="high",
                    message=(
                        f"Vegetation declined {abs(percent_change):.1f}% in last 2 weeks. "
                        f"NDVI dropped from {previous_avg:.2f} to {current_avg:.2f}."
                    ),
                    metadata={
                        "current_ndvi": current_avg,
                        "previous_ndvi": previous_avg,
                        "percent_change": percent_change,
                    },
                )
                return True

        return False

    def _check_drought_stress(self, db_session: Session, parcel_id: str) -> bool:
        """
        Check for low NDVI (drought stress).

        Alerts if NDVI has been below 0.4 for 3+ weeks.
        """
        stmt = (
            select(TimeSeries)
            .where(
                TimeSeries.parcel_id == parcel_id,
                TimeSeries.metric_type == "NDVI_avg",
                TimeSeries.time_period == "weekly",
            )
            .order_by(desc(TimeSeries.start_date))
            .limit(3)
        )

        recent_weeks = list(db_session.execute(stmt).scalars().all())

        if len(recent_weeks) < 3:
            return False
        threshold = 0.4
        all_low = all(week.value < threshold for week in recent_weeks)

        if all_low:
            avg_ndvi = sum(w.value for w in recent_weeks) / len(recent_weeks)

            if not self._active_alert_exists(parcel_id, "drought_stress"):
                self._create_alert(
                    parcel_id=parcel_id,
                    alert_type="drought_stress",
                    severity="critical",
                    message=(
                        f"Sustained low vegetation for 3+ weeks. "
                        f"Average NDVI: {avg_ndvi:.2f} (threshold: {threshold}). "
                        f"Possible drought stress."
                    ),
                    metadata={
                        "avg_ndvi": avg_ndvi,
                        "threshold": threshold,
                        "weeks_below": 3,
                    },
                )
                return True

        return False

    def _check_anomalies(self, db_session: Session, parcel_id: str) -> bool:
        """
        Check for detected anomalies in time series.

        Alerts if anomaly was detected in recent time series.
        """
        stmt = select(TimeSeries).where(
            TimeSeries.parcel_id == parcel_id,
            TimeSeries.is_anomaly.is_(True),
            TimeSeries.start_date >= date.today() - timedelta(days=14),
        )

        anomalies = list(db_session.execute(stmt).scalars().all())

        if anomalies:
            latest_anomaly = max(anomalies, key=lambda a: a.start_date)

            if not self._active_alert_exists(parcel_id, "anomaly"):
                self._create_alert(
                    parcel_id=parcel_id,
                    alert_type="anomaly",
                    severity="medium",
                    message=(
                        f"Unusual vegetation pattern detected. "
                        f"{latest_anomaly.metric_type}: {latest_anomaly.value:.2f} "
                        f"on {latest_anomaly.start_date.isoformat()}."
                    ),
                    metadata={
                        "value": latest_anomaly.value,
                        "metric": latest_anomaly.metric_type,
                        "date": latest_anomaly.start_date.isoformat(),
                    },
                )
                return True

        return False

    def _check_stale_data(self, db_session: Session, parcel_id: str) -> bool:
        """
        Check if parcel has missing recent data.

        Alerts if no data in last 14 days.
        """
        stmt = (
            select(RasterStats)
            .where(RasterStats.parcel_id == parcel_id)
            .order_by(desc(RasterStats.acquisition_date))
            .limit(1)
        )

        latest = db_session.execute(stmt).scalar_one_or_none()

        if not latest:
            if not self._active_alert_exists(parcel_id, "no_data"):
                self._create_alert(
                    parcel_id=parcel_id,
                    alert_type="no_data",
                    severity="low",
                    message="No satellite data available for this parcel.",
                    metadata={},
                )
                return True

        elif (date.today() - latest.acquisition_date).days > 14:
            if not self._active_alert_exists(parcel_id, "stale_data"):
                self._create_alert(
                    parcel_id=parcel_id,
                    alert_type="stale_data",
                    severity="low",
                    message=(
                        f"No new satellite data for {(date.today() - latest.acquisition_date).days} days. "
                        f"Last data: {latest.acquisition_date.isoformat()}."
                    ),
                    metadata={
                        "last_date": latest.acquisition_date.isoformat(),
                        "days_ago": (date.today() - latest.acquisition_date).days,
                    },
                )
                return True

        return False

    # helpers
    def _active_alert_exists(
        self, db_session: Session, parcel_id: str, alert_type: str
    ) -> bool:
        """Check if active alert of this type already exists."""

        stmt = select(Alerts).where(
            Alerts.parcel_id == parcel_id,
            Alerts.alert_type == alert_type,
            Alerts.status == "active",
        )

        return db_session.execute(stmt).scalar_one_or_none() is not None

    def _create_alert(
        self,
        db_session: Session,
        parcel_id: str,
        alert_type: str,
        severity: str,
        message: str,
        metadata: dict,
    ):
        """Create a new alert."""

        alert = Alerts(
            parcel_id=parcel_id,
            alert_type=alert_type,
            severity=severity,
            message=message,
            status="active",
            alerts_data=metadata,
        )

        db_session.add(alert)
        db_session.commit()

        logger.info(f"Created {severity} alert for parcel {parcel_id}: {alert_type}")
