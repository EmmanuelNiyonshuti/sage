import logging
from datetime import date

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import and_, desc, select

from app.api.deps import SessionDep
from app.models import Parcel, RasterStats
from app.models.schemas import (
    ParcelStatsListResponse,
    RasterStatsOut,
)

router = APIRouter(prefix="/parcels", tags=["Parcel Statistics"])
logger = logging.getLogger(__name__)


def find_parcel_by_id(parcel_id: str, db: SessionDep) -> Parcel:
    stmt = select(Parcel).where(Parcel.uid == parcel_id)
    parcel = db.execute(stmt).scalars().first()
    if not parcel:
        raise HTTPException(
            status_code=404, detail=f"parcel with id {parcel_id} is not found"
        )
    return parcel


@router.get(
    "/{parcel_id}/stats",
    response_model=ParcelStatsListResponse,
    summary="Get parcel statistics",
    description="Get time-series statistics for a parcel with optional filtering",
)
def get_parcel_stats(
    parcel_id: str,
    db: SessionDep,
    metric_type: str | None = Query(
        None, description="Filter by metric type (NDVI currently)"
    ),
    start_date: date | None = Query(None, description="Filter from this date"),
    end_date: date | None = Query(None, description="Filter until this date"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
):
    logger.info(f"Getting stats for parcel {parcel_id}")

    parcel = find_parcel_by_id(parcel_id, db)
    conditions = [RasterStats.parcel_id == parcel.uid]

    if metric_type:
        conditions.append(RasterStats.metric_type == metric_type)
    if start_date:
        conditions.append(RasterStats.acquisition_date >= start_date)
    if end_date:
        conditions.append(RasterStats.acquisition_date <= end_date)

    count_stmt = select(RasterStats).where(and_(*conditions))
    total = len(db.execute(count_stmt).scalars().all())

    stmt = (
        select(RasterStats)
        .where(and_(*conditions))
        .order_by(desc(RasterStats.acquisition_date))
        .limit(limit)
        .offset(offset)
    )

    stats = db.execute(stmt).scalars().all()

    return ParcelStatsListResponse(
        parcel_id=parcel_id,
        stats=[RasterStatsOut.model_validate(s) for s in stats],
        total=total,
        limit=limit,
        offset=offset,
    )
