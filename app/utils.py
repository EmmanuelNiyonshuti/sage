import logging

from geoalchemy2.shape import from_shape, to_shape
from geoalchemy2.types import WKBElement
from shapely.geometry import Polygon, shape

from app.core.database import session_factory
from app.pipeline.ingestion_controller import IngestionController

logger = logging.getLogger(__name__)


def trigger_backfill_for_parcel(parcel_id: str, lookback_days: int = 90):
    logger.info(f"Starting background backfill for parcel {parcel_id}")
    try:
        controller = IngestionController(session_factory)
        job = controller.trigger_initial_backfill(
            parcel_id, lookback_days=lookback_days
        )
        logger.info(
            f"Backfill completed for parcel {parcel_id}: "
            f"{job.records_created} records created"
        )
    except Exception as e:
        logger.exception(f" Backfill failed for parcel {parcel_id}: {e}")


def geojson_to_shapely(geojson: dict) -> Polygon:
    """converts geojson to shapely object"""
    return shape(geojson)


def shapely_to_wkbelement(shapely_obj: Polygon, srid: int = 4326) -> WKBElement:
    return from_shape(shapely_obj, srid=srid)


def wkb_to_geojson(wkb_geom: WKBElement) -> dict:
    polygon = to_shape(wkb_geom)
    return {
        "type": "Polygon",
        "coordinates": [list(polygon.exterior.coords)],
    }
