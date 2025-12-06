from fastapi import APIRouter

router = APIRouter()


@router.post("/ingest")
async def raster_stats():  # field_id, start_date, end_date
    return {"stats": {}}
