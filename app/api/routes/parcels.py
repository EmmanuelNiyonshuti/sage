import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import shape

from app.api.deps import SessionDep
from app.core.database import session_factory
from app.models import Parcel
from app.models.schemas import (
    ParcelCreate,
    ParcelResponse,
)
from app.services.ingestion_engine import IngestionEngine

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
        geom_dict = parcel_data.geometry.model_dump()
        shapely_geom = shape(geom_dict)
    except Exception as e:
        logger.error(f"Invalid geometry provided: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid geometry: {str(e)}")
    parcel = Parcel(
        name=parcel_data.name,
        geometry=from_shape(shapely_geom, srid=4326),
        crop_type=parcel_data.crop_type,
        soil_type=parcel_data.soil_type,
        irrigation_type=parcel_data.irrigation_type,
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
            logger.info(f"Queued backfill job for parcel {parcel.uid}")

    except Exception as e:
        db.rollback()
        logger.exception(f"Failed to create parcel: {e}")
        raise HTTPException(status_code=500, detail="Failed to create parcel")

    # Convert geometry for response
    shape_obj = to_shape(parcel.geometry)

    return ParcelResponse(
        uid=parcel.uid,
        name=parcel.name,
        geometry={
            "type": "Polygon",
            "coordinates": [list(shape_obj.exterior.coords)],
        },
        area_hectares=parcel.area_hectares,
        crop_type=parcel.crop_type,
        soil_type=parcel.soil_type,
        irrigation_type=parcel.irrigation_type,
        is_active=parcel.is_active,
        auto_sync_enabled=parcel.auto_sync_enabled,
        last_data_synced_at=parcel.last_data_synced_at,
        latest_acquisition_date=parcel.latest_acquisition_date,
        next_sync_scheduled_at=parcel.next_sync_scheduled_at,
        created_at=parcel.created_at,
        updated_at=parcel.updated_at,
    )


def trigger_backfill_for_parcel(parcel_id: str, lookback_days: int = 90):
    logger.info(f"Starting background backfill for parcel {parcel_id}")
    try:
        engine = IngestionEngine(session_factory)
        job = engine.trigger_initial_backfill(parcel_id, lookback_days=lookback_days)
        logger.info(
            f"Backfill completed for parcel {parcel_id}: "
            f"{job.records_created} records created"
        )
    except Exception as e:
        logger.exception(f" Backfill failed for parcel {parcel_id}: {e}")
