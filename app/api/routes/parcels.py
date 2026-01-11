import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import ValidationError

from app.api.deps import SessionDep
from app.crud import find_parcel_by_id, list_parcels
from app.models import Parcel
from app.models.schemas import ParcelCreate, ParcelListResponse, ParcelResponse
from app.utils import (
    trigger_backfill_for_parcel,
)

router = APIRouter(tags=["Parcels"])
logger = logging.getLogger(__name__)


@router.post(
    "/parcels",
    response_model=ParcelResponse,
    status_code=201,
    summary="Create a new parcel",
    description="Create a new parcel and trigger automatic data backfill",
)
async def create_parcel(
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


@router.get(
    "/parcels",
    response_model=ParcelListResponse,
    status_code=200,
    summary="List all parcels",
    description="Get a paginated list of parcels",
)
async def get_parcels(
    db: SessionDep,
    limit: int = Query(50, ge=1, le=100, description="Number of results to return"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    is_active: bool | None = Query(None, description="Filter by active status"),
    crop_type: str | None = Query(None, description="Filter by crop type"),
    search: str | None = Query(
        None, description="Search by parcel name (case-insensitive)"
    ),
):
    try:
        parcels, total = list_parcels(
            db,
            limit=limit,
            offset=offset,
            is_active=is_active,
            crop_type=crop_type,
            search=search,
        )
        parcel_responses = [ParcelResponse.model_validate(p) for p in parcels]

        return ParcelListResponse(
            parcels=parcel_responses,
            total=total,
            limit=limit,
            offset=offset,
        )

    except ValidationError as e:
        logger.exception(e)
        raise HTTPException(
            status_code=500,
            detail="Failed to serialize parcel data",
        )
    except Exception as e:
        logger.exception(f"Failed to list parcels: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred retrieving parcels: {str(e)}",
        )


@router.get("/{parcel_id}")
async def get_parcel(parcel_id: str, db: SessionDep):
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
