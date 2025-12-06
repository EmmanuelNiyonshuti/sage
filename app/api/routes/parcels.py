"""API endpoints for field resources."""

from fastapi import APIRouter, HTTPException, Query
from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import shape

from app.api.deps import SessionDep
from app.models import Parcel
from app.models.schemas import ParcelCreate, ParcelListResponse, ParcelResponse

# from app.schemas.raster_stats import (
#     IngestRequest,
#     IngestResponse,
#     RasterStatsListResponse,
#     RasterStatsResponse,
# )

router = APIRouter(prefix="/parcels", tags=["parcels"])


@router.post("/", response_model=ParcelResponse, status_code=201)
def create_field(parcel_data: ParcelCreate, db: SessionDep):
    """
    Create a new parcel with geometry.

    The geometry must be a valid GeoJSON Polygon.
    """
    # Convert GeoJSON to Shapely geometry
    geom_dict = parcel_data.geometry.model_dump()
    shapely_geom = shape(geom_dict)

    # Create parcel
    parcel = Parcel(
        name=parcel_data.name,
        geometry=from_shape(shapely_geom, srid=4326),
        crop_type=parcel_data.crop_type,
        soil_type=parcel_data.soil_type,
        irrigation_type=parcel_data.irrigation_type,
    )

    db.add(parcel)
    db.commit()
    db.refresh(parcel)

    # Convert geometry back to GeoJSON for response
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
def get_field(parcel_id: str, db: SessionDep):
    """Get a single field by ID."""
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


# @router.post("/{field_id}/ingest", response_model=IngestResponse)
# def ingest_field_data(
#     parcel_id: str,
#     ingest_data: IngestRequest,
#     db: SessionDep,
# ):
#     """
#     Trigger satellite data ingestion for a field.

#     This will fetch NDVI data from Sentinel Hub for the specified date range.
#     Note: This operation can take 10-15 seconds.
#     """
#     service = IngestionService(db)

#     try:
#         result = service.ingest_parcel_ndvi(
#             parcel_id=parcel_id,
#             start_date=ingest_data.start_date,
#             end_date=ingest_data.end_date,
#         )
#         return IngestResponse(**result)
#     except ValueError as e:
#         raise HTTPException(status_code=404, detail=str(e))
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


# @router.get("/{parcel_id}/stats", response_model=RasterStatsListResponse)
# def get_field_stats(
#     db: SessionDep,
#     parcel_id: str,
#     start_date: date | None = Query(None),
#     end_date: date | None = Query(None),
#     metric_type: str = Query("NDVI"),
# ):
#     """Get raster statistics for a parcel."""
#     # Check field exists
#     parcel = db.get(Parcel, parcel_id)
#     if not parcel:
#         raise HTTPException(status_code=404, detail="parcel not found")

#     # Build query
#     query = db.query(RasterStats).filter(
#         RasterStats.parcel_id == parcel_id,
#         RasterStats.metric_type == metric_type,
#     )

#     if start_date:
#         query = query.filter(RasterStats.acquisition_date >= start_date)
#     if end_date:
#         query = query.filter(RasterStats.acquisition_date <= end_date)

#     stats = query.order_by(RasterStats.acquisition_date.desc()).all()

#     return RasterStatsListResponse(
#         stats=[RasterStatsResponse.model_validate(s) for s in stats],
#         total=len(stats),
#         parcel_id=parcel_id,
#     )
