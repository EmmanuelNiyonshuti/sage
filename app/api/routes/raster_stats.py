import logging

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.api.deps import SessionDep
from app.models import Parcel, RasterStats
from app.models.schemas import ParcelStatsResponse

router = APIRouter(prefix="/parcels")

logger = logging.getLogger(__name__)


def find_parcel_by_id(parcel_id: str, db):
    stmt = select(Parcel).where(Parcel.uid == parcel_id)
    parcel = db.execute(stmt).scalars().first()
    if not parcel:
        raise HTTPException(
            status_code=404, detail=f"parcel with id {parcel_id} is not found"
        )
    return parcel


@router.get(
    "/stats",
    response_model=ParcelStatsResponse,
)
async def get_stats(parcel_id: str, db: SessionDep):
    logger.info("getting parcel stats")
    parcel = find_parcel_by_id(parcel_id, db)
    try:
        stmt = select(RasterStats).where(RasterStats.parcel_id == parcel.uid)
        stats = db.execute(stmt).scalars().all()
        return ParcelStatsResponse(parcel_id=parcel.uid, stats=stats)
    except Exception as e:
        logger.exception(f" an error occured getting parcel stats: {str(e)}")
        raise HTTPException(status_code=500, detail="something went wrong")
