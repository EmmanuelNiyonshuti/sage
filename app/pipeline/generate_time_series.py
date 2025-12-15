import logging
from datetime import date, timedelta
from typing import List

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.models import Parcel, RasterStats, TimeSeries

logger = logging.getLogger(__name__)


class GenerateTimeSeries:
    """
    Processes raw statistics into time series aggregations.

    - collects daily data into weekly/monthly periods
    - Calculate period-over-period changes
    - Detect statistical anomalies
    """

    def __init__(self, session_factory):
        self.session_factory = session_factory

    def generate_weekly_time_series(
        self,
        db_session: Session,
        parcel_id: str,
        metric_type: str = "NDVI",
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> int:
        """
        Generate weekly time series for a parcel.

        Groups raw daily stats into weekly averages.
        start and end date will be in the range of the raw raster stats acquisition dates

        Args:
            parcel_id: Parcel UUID
            metric_type: The index type to aggregate (default: NDVI)
            start_date: Start of range (default: earliest data)
            end_date: End of range (default: latest data)

        Returns:
            Number of time series records created
        """
        logger.info(
            f"Generating weekly time series for parcel {parcel_id}, metric {metric_type}"
        )
        raw_stats = self._get_raw_stats(
            db_session, parcel_id, metric_type, start_date, end_date
        )

        if not raw_stats:
            logger.warning(f"No raw stats found for parcel {parcel_id}")
            return 0

        weekly_groups = self._group_by_week(raw_stats)

        created_count = 0
        previous_value = None

        for week_start, week_data in sorted(weekly_groups.items()):
            week_end = week_start + timedelta(days=6)

            # avg for the week
            mean_value = sum(s.mean_value for s in week_data) / len(week_data)
            # % change from previous week
            change_from_previous = None
            if previous_value is not None:
                change_from_previous = (
                    (mean_value - previous_value) / previous_value
                ) * 100

            is_anomaly = self._is_anomaly(
                db_session,
                parcel_id,
                metric_type,
                mean_value,
                week_start,
            )
            exists = self._time_series_exists(
                db_session,
                parcel_id,
                metric_type,
                "weekly",
                week_start,
            )

            if not exists:
                # Create time series record
                ts = TimeSeries(
                    parcel_id=parcel_id,
                    metric_type=f"{metric_type}_avg",
                    time_period="weekly",
                    start_date=week_start,
                    end_date=week_end,
                    value=mean_value,
                    change_from_previous=change_from_previous,
                    is_anomaly=is_anomaly,
                )

                db_session.add(ts)
                created_count += 1

            previous_value = mean_value

        db_session.commit()

        logger.info(f"Created {created_count} weekly time series records")
        return created_count

    def generate_monthly_time_series(
        self,
        db_session: Session,
        parcel_id: str,
        metric_type: str = "NDVI",
    ) -> int:
        """
        Generate monthly time series for a parcel.
        """
        logger.info(f"Generating monthly time series for parcel {parcel_id}")

        raw_stats = self._get_raw_stats(db_session, parcel_id, metric_type)

        if not raw_stats:
            return 0
        monthly_groups = self._group_by_month(raw_stats)

        created_count = 0
        previous_value = None

        for (year, month), month_data in sorted(monthly_groups.items()):
            month_start = date(year, month, 1)
            if month == 12:
                month_end = date(year + 1, 1, 1) - timedelta(days=1)
            else:
                month_end = date(year, month + 1, 1) - timedelta(days=1)
            mean_value = sum(s.mean_value for s in month_data) / len(month_data)

            change_from_previous = None
            if previous_value is not None:
                change_from_previous = (
                    (mean_value - previous_value) / previous_value
                ) * 100

            is_anomaly = self._is_anomaly(
                db_session,
                parcel_id,
                metric_type,
                mean_value,
                month_start,
            )

            if not self._time_series_exists(
                db_session, parcel_id, metric_type, "monthly", month_start
            ):
                ts = TimeSeries(
                    parcel_id=parcel_id,
                    metric_type=f"{metric_type}_avg",
                    time_period="monthly",
                    start_date=month_start,
                    end_date=month_end,
                    value=mean_value,
                    change_from_previous=change_from_previous,
                    is_anomaly=is_anomaly,
                )

                db_session.add(ts)
                created_count += 1

            previous_value = mean_value

        db_session.commit()

        logger.info(f"Created {created_count} monthly time series records")
        return created_count

    def process_all_parcels(self) -> dict:
        """
        Process time series for all active parcels.

        Called by scheduler to keep time series up-to-date.

        Returns:
            Summary of processing
        """
        logger.info("Processing time series for all parcels")
        with self.session_factory() as db_s:
            stmt = select(Parcel).where(Parcel.is_active.is_(True))
            parcels = db_s.execute(stmt).scalars().all()
            results = {
                "total_parcels": len(parcels),
                "succeeded": 0,
                "failed": 0,
                "weekly_created": 0,
                "monthly_created": 0,
            }

            for parcel in parcels:
                try:
                    weekly = self.generate_weekly_time_series(db_s, parcel.uid)
                    results["weekly_created"] += weekly
                    monthly = self.generate_monthly_time_series(db_s, parcel.uid)
                    results["monthly_created"] += monthly
                    results["succeeded"] += 1

                except Exception:
                    logger.exception(
                        f"Failed to process time series for parcel {parcel.uid}"
                    )
                    results["failed"] += 1

            logger.info(
                f"Time series processing complete: "
                f"{results['succeeded']} succeeded, {results['failed']} failed, "
                f"{results['weekly_created']} weekly, {results['monthly_created']} monthly"
            )

            return results

    # helpers
    def _get_raw_stats(
        self,
        db_session: Session,
        parcel_id: str,
        metric_type: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> List[RasterStats]:
        """Get raw statistics for a given parcel, metric/index type with optional date ranges."""

        conditions = [
            RasterStats.parcel_id == parcel_id,
            RasterStats.metric_type == metric_type,
        ]
        if start_date:
            conditions.append(RasterStats.acquisition_date >= start_date)
        if end_date:
            conditions.append(RasterStats.acquisition_date <= end_date)
        stmt = (
            select(RasterStats)
            .where(and_(*conditions))
            .order_by(RasterStats.acquisition_date)
        )

        return list(db_session.execute(stmt).scalars().all())

    def _group_by_week(self, stats: List[RasterStats]) -> dict[date, List[RasterStats]]:
        """
        Group stats by week (Monday as start of week).

        Returns:
            Dict mapping week_start_date -> list of stats in that week
        """
        weeks = {}

        for stat in stats:
            week_start_dt = stat.acquisition_date - timedelta(
                days=stat.acquisition_date.weekday()
            )  # zero based weekdays , isoweekday for 1 based!

            if week_start_dt not in weeks:
                weeks[week_start_dt] = []

            weeks[week_start_dt].append(stat)

        return weeks

    def _group_by_month(
        self, stats: List[RasterStats]
    ) -> dict[tuple[int, int], List[RasterStats]]:
        """
        Group stats by month.

        Returns:
            Dict mapping (year, month) -> list of stats in that month
        """
        months = {}

        for stat in stats:
            key = (stat.acquisition_date.year, stat.acquisition_date.month)

            if key not in months:
                months[key] = []

            months[key].append(stat)

        return months

    def _is_anomaly(
        self,
        db_session: Session,
        parcel_id: str,
        metric_type: str,
        current_value: float,
        current_date: date,
    ) -> bool:
        """
        Detect if current value is anomalous.

        - Gets historical average and std dev , past 30 days
        - If current value is >2 standard deviations away, it's an anomaly

        Args:
            parcel_id: Parcel ID
            metric_type: Metric type
            current_value: Current value to check
            current_date: Date of current value, (avg mean_val)

        Returns:
            True if anomalous
        """
        # Get historical data (excluding current period)
        stmt = select(
            func.avg(RasterStats.mean_value).label("avg"),
            func.stddev(RasterStats.mean_value).label("stddev"),
        ).where(
            RasterStats.parcel_id == parcel_id,
            RasterStats.metric_type == metric_type,
            RasterStats.acquisition_date < current_date - timedelta(days=30),
        )

        result = db_session.execute(stmt).first()

        if not result or result.avg is None or result.stddev is None:
            return False

        historical_avg = float(result.avg)
        historical_std = float(result.stddev)

        threshold = 2.0
        lower_bound = historical_avg - (threshold * historical_std)
        upper_bound = historical_avg + (threshold * historical_std)

        is_anomaly = current_value < lower_bound or current_value > upper_bound

        if is_anomaly:
            logger.info(
                f"Anomaly detected for parcel {parcel_id}: "
                f"value={current_value:.3f}, "
                f"expected={historical_avg:.3f}±{historical_std:.3f}"
            )

        return is_anomaly

    def _time_series_exists(
        self,
        db_session: Session,
        parcel_id: str,
        metric_type: str,
        time_period: str,
        start_date: date,
    ) -> bool:
        """Check if time series record already exists."""

        stmt = select(TimeSeries).where(
            TimeSeries.parcel_id == parcel_id,
            TimeSeries.metric_type == f"{metric_type}_avg",
            TimeSeries.time_period == time_period,
            TimeSeries.start_date == start_date,
        )

        return db_session.execute(stmt).scalar_one_or_none() is not None
