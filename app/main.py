import logging
from contextlib import asynccontextmanager

from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI

from app.api.main import api_router
from app.core.config import config
from app.logging_config import configure_logging
from app.scheduler.alerts_scheduler import generate_alerts_scheduler
from app.scheduler.ingestion_scheduler import ingestion_scheduler
from app.scheduler.time_series_scheduler import time_series_scheduler

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    if config.ENABLE_SCHEDULER:
        try:
            ingestion_scheduler.start()
            time_series_scheduler.start()
            generate_alerts_scheduler.start()
        except Exception as e:
            logger.exception(f"Failed to start scheduler: {str(e)}")
    yield
    if ingestion_scheduler.is_running():
        try:
            ingestion_scheduler.stop()
        except Exception as e:
            logger.exception(f"failed stopping scheduler, {str(e)}")
    if time_series_scheduler.is_running():
        time_series_scheduler.stop()


app = FastAPI(
    title="spatial agronomic geo engine(sage)",
    summary="""
    fetch NDVI data from sentinel hub statistical api run scheduled jobs for a particular farm boundary(drawn on a map) referred to in the application as parcels,
    stores the data in relational database, builds time series and alerts over those data and expose them via a REST API.
    """,
    lifespan=lifespan,
)


app.add_middleware(CorrelationIdMiddleware)


app.include_router(api_router)
