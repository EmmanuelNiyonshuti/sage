import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import ValidationError

from app.api.deps import SessionDep
from app.crud import find_parcel_by_id
from app.models import Parcel
from app.models.schemas import (
    ParcelCreate,
    ParcelResponse,
)
from app.utils import (
    trigger_backfill_for_parcel,
)

router = APIRouter(prefix="/parcels", tags=["Parcels"])
logger = logging.getLogger(__name__)


@router.post(
    "/",
    response_model=ParcelResponse,
    status_code=201,
    summary="Create a new parcel",
    description="Create a new parcel and trigger automatic data backfill",
)
def create_parcel(
    parcel_data: ParcelCreate,
    db: SessionDep,
    background_tasks: BackgroundTasks,
    trigger_backfill: bool = Query(
        True, description="Automatically trigger historical data backfill"
    ),
):
    """
    Create a new parcel with geometry.

    Automatically triggers a background job to fetch historical satellite data
    (default: last 90 days).
    """
    try:
        parcel = Parcel(**parcel_data.model_dump())
    except ValidationError as e:
        logger.exception(e)
        raise HTTPException(
            status_code=400,
            detail="Failed validating request data for adding parcel, please try again",
        )
    try:
        db.add(parcel)
        db.commit()
        db.refresh(parcel)
        logger.info(f"Created parcel: {parcel.uid} - {parcel.name}")
        if trigger_backfill:
            background_tasks.add_task(
                trigger_backfill_for_parcel,
                parcel.uid,
                lookback_days=90,
            )
            logger.info(f"Queued backfill job for parcel {parcel.name}")
        return ParcelResponse.model_validate(parcel)
    except Exception as e:
        db.rollback()
        logger.exception(f"Failed to create parcel, {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"an error occured adding a parcel, please try again. {e}",
        )


@router.get("/{parcel_id}")
def get_parcel(parcel_id: str, db: SessionDep):
    parcel = find_parcel_by_id(parcel_id, db)
    if not parcel:
        raise HTTPException(
            status_code=404, detail=f"parcel with id {parcel_id} is not found"
        )
    try:
        return ParcelResponse.model_validate(parcel)
    except ValidationError as e:
        logger.exception(e)
        raise HTTPException(
            status_code=500,
            detail="an unexpected error occured retrieving parcel, please try again.",
        )
