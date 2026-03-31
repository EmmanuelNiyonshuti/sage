import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import ValidationError

from app.api.crud import add_parcel_boundary, find_parcel_by_id, list_parcels
from app.api.deps import CurrentUser, SessionDep
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
    db_session: SessionDep,
    user: CurrentUser,
    parcel_data: ParcelCreate,
    background_tasks: BackgroundTasks,
    trigger_backfill: bool = Query(
        True, description="Automatically trigger historical data backfill"
    ),
):
    parcel_data.owner_id = user.uid
    parcel_data = parcel_data.model_dump()
    new_parcel = await add_parcel_boundary(db_session, parcel_data)
    logger.info(f"Created parcel: {new_parcel.uid} - {new_parcel.name}")
    if trigger_backfill:
        background_tasks.add_task(
            trigger_backfill_for_parcel,
            new_parcel.uid,
            lookback_days=90,
        )
        logger.info(f"Queued backfill job for parcel {new_parcel.name}")
    return ParcelResponse.model_validate(new_parcel)


@router.get(
    "/parcels",
    response_model=ParcelListResponse,
    status_code=200,
    summary="List all parcels",
    description="Get a paginated list of parcels",
)
async def get_parcels(
    db_session: SessionDep,
    user: CurrentUser,
    limit: int = Query(50, ge=1, le=100, description="Number of results to return"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    is_active: bool | None = Query(None, description="Filter by active status"),
    crop_type: str | None = Query(None, description="Filter by crop type"),
    search: str | None = Query(
        None, description="Search by parcel name (case-insensitive)"
    ),
):
    try:
        parcels, total = await list_parcels(
            db_session,
            user.uid,
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
async def get_parcel(parcel_id: str, user: CurrentUser, db_session: SessionDep):
    parcel = await find_parcel_by_id(user.uid, parcel_id, db_session)
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
