import logging

from fastapi import APIRouter, HTTPException, Query
from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import shape

from app.api.deps import SessionDep
from app.models import Parcel
from app.models.schemas import ParcelCreate, ParcelListResponse, ParcelResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/parcels", tags=["Land Parcels"])


@router.post("/", response_model=ParcelResponse, status_code=201)
def add_parcel(parcel_data: ParcelCreate, db: SessionDep):
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
    # Create parcel
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
    except Exception as e:
        db.rollback()
        logger.exception(f"Database error creating parcel: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to create a parcel. Please try again"
        )

    return ParcelResponse.model_validate(parcel)


@router.get("/", response_model=ParcelListResponse)
def list_parcels(
    db: SessionDep,
    is_active: bool | None = Query(None),
    crop_type: str | None = Query(None),
):
    """List all parcels with optional filtering."""
    query = db.query(Parcel)

    if is_active is not None:
        query = query.filter(Parcel.is_active == is_active)
    if crop_type:
        query = query.filter(Parcel.crop_type == crop_type)
    parcels = query.all()

    # Convert geometries to GeoJSON
    parcel_responses = []
    for parcel in parcels:
        shape_obj = to_shape(parcel.geometry)
        parcel_dict = {
            "uid": parcel.uid,
            "name": parcel.name,
            "geometry": {
                "type": "Polygon",
                "coordinates": [list(shape_obj.exterior.coords)],
            },
            "area_hectares": parcel.area_hectares,
            "crop_type": parcel.crop_type,
            "soil_type": parcel.soil_type,
            "irrigation_type": parcel.irrigation_type,
            "is_active": parcel.is_active,
            "created_at": parcel.created_at,
            "updated_at": parcel.updated_at,
        }
        parcel_responses.append(ParcelResponse(**parcel_dict))

    return ParcelListResponse(parcels=parcel_responses, total=len(parcel_responses))


@router.get("/{parcel_id}", response_model=ParcelResponse)
def get_parcel(parcel_id: str, db: SessionDep):
    """Get a single land parcel by ID."""
    parcel = db.get(Parcel, parcel_id)

    if not parcel:
        raise HTTPException(status_code=404, detail="parcel not found")

    shape_obj = to_shape(parcel.geometry)
    parcel_dict = {
        "uid": parcel.uid,
        "name": parcel.name,
        "geometry": {
            "type": "Polygon",
            "coordinates": [list(shape_obj.exterior.coords)],
        },
        "area_hectares": parcel.area_hectares,
        "crop_type": parcel.crop_type,
        "soil_type": parcel.soil_type,
        "irrigation_type": parcel.irrigation_type,
        "is_active": parcel.is_active,
        "created_at": parcel.created_at,
        "updated_at": parcel.updated_at,
    }

    return ParcelResponse(**parcel_dict)
