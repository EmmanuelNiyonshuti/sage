import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException
from geoalchemy2.shape import from_shape
from shapely.geometry import shape

from app.api.deps import SessionDep
from app.models import Parcel
from app.models.schemas import ParcelCreate, ParcelResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/parcels", tags=["Land Parcels"])


@router.post("/", response_model=ParcelResponse, status_code=201)
def add_parcel(parcel_data: ParcelCreate, db: SessionDep, task: BackgroundTasks):
    """
    Create a new farm boundary with polygon coordinates.

    The geometry must be a valid GeoJSON Polygon.
    """
    # Convert GeoJSON to Shapely geometry
    try:
        geom_dict = parcel_data.geometry.model_dump()
        shapely_geom = shape(geom_dict)
    except Exception as e:
        logger.error(f"Invalid geometry provided: {str(e)}")
        raise HTTPException(
            status_code=400, detail=f"Invalid geometry format: {str(e)}"
        )
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
        # task.add_task() # run a scheduler task
        return ParcelResponse.model_validate(parcel)
    except Exception as e:
        db.rollback()
        logger.exception(f"Database error creating parcel: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to create a parcel. Please try again"
        )
