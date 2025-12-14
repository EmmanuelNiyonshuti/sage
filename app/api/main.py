from fastapi import APIRouter

from app.api.routes import parcels, raster_stats, scheduler_status

api_router = APIRouter(prefix="/api/v1")


api_router.include_router(parcels.router)
api_router.include_router(raster_stats.router)
api_router.include_router(scheduler_status.router)
