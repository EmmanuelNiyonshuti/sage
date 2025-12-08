from fastapi import APIRouter

from app.api.routes import parcels, raster_stats

api_router = APIRouter()


@api_router.get("/")
def home():
    return {"message": "Spatial Agronomic Geo Engine API is running"}


api_router.include_router(parcels.router)
api_router.include_router(raster_stats.router)
