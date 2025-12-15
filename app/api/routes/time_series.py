import logging
from datetime import date

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import and_, desc, select

from app.api.deps import SessionDep
from app.crud import find_parcel_by_id
from app.models import TimeSeries
from app.models.schemas import TimeSeriesResponse, TimeSeriesStats

router = APIRouter(tags=["time series stats"])

logger = logging.getLogger(__name__)


@router.get(
    "/{parcel_id}/stats",
    response_model=TimeSeriesResponse,
    summary="Get parcel timeseries stats",
)
async def get_parcel_time_series_stats(
    parcel_id: str,
    db: SessionDep,
    metric_type: str = Query(
        "NDVI_avg", description="Filter by metric type (NDVI currently)"
    ),
    time_period: str = Query(
        "weekly", description="Filter by time period(monthly, weekly)"
    ),
    is_anomaly: bool | None = Query(None, description="Filter by anomalities"),
    start_date: date | None = Query(None, description="Filter from this date"),
    end_date: date | None = Query(None, description="Filter until this date"),
    limit: int = Query(50, ge=1, le=1000, description="Maximum number of records"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
):
    logger.info(f"Getting time series stats for parcel {parcel_id}")

    parcel = find_parcel_by_id(parcel_id, db)
    if not parcel:
        raise HTTPException(
            status_code=404, detail=f"parcel with id {parcel_id} is not found"
        )
    conditions = [TimeSeries.parcel_id == parcel.uid]
    conditions.append(TimeSeries.metric_type == metric_type)
    if time_period:
        conditions.append(TimeSeries.time_period == time_period)
    if is_anomaly:
        conditions.append(TimeSeries.is_anomaly <= is_anomaly)
    if start_date:
        conditions.append(TimeSeries.start_date >= start_date)
    if end_date:
        conditions.append(TimeSeries.end_date <= end_date)

    count_stmt = select(TimeSeries).where(and_(*conditions))
    total = len(db.execute(count_stmt).scalars().all())

    stmt = (
        select(TimeSeries)
        .where(and_(*conditions))
        .order_by(desc(TimeSeries.start_date))
        .limit(limit)
        .offset(offset)
    )

    stats = db.execute(stmt).scalars().all()

    return TimeSeriesResponse(
        parcel_id=parcel_id,
        stats=[TimeSeriesStats.model_validate(s) for s in stats],
        total=total,
        limit=limit,
        offset=offset,
    )
