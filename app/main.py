import logging
from contextlib import asynccontextmanager

from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI

from app.api.main import api_router
from app.core.config import config
from app.logging_config import configure_logging
from app.scheduler.ingestion_scheduler import ingestion_scheduler

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    if config.ENABLE_SCHEDULER:
        try:
            ingestion_scheduler.start(
                check_interval_hours=config.SHEDULER_INTERVAL_HOURS
            )
        except Exception as e:
            logger.exception(f"Failed to start scheduler: {str(e)}")
    yield
    if ingestion_scheduler.is_running():
        try:
            ingestion_scheduler.stop()
            logger.exception("scheduler stopped")
        except Exception as e:
            logger.exception(f"failed stopping scheduler, {str(e)}")


app = FastAPI(
    title="sage",
    summary="Spatial Agronomic Geo Engine API",
    description="""
    A backend that utilize sentinel hub api to fetch agronomic data through scheduled jobs for a particular farm boundary(drawn on a map) referred to in the application as parcels,
    stores the data in relational database, builds time series and alerts over those data and expose them via a REST API for internal tools, dashboards, or other services.
    """,
    lifespan=lifespan,
)

app.add_middleware(CorrelationIdMiddleware)


app.include_router(api_router, prefix="/api/v1")


@app.get("/ping")
def health_check():
    """Health check endpoint."""
    return {
        "status": "up",
        "scheduler_running": ingestion_scheduler.is_running(),
    }


@app.get("/scheduler/status")
def scheduler_status():
    """Get scheduler status (for monitoring)."""
    jobs = ingestion_scheduler.get_jobs()
    return {
        "running": ingestion_scheduler.is_running(),
        "jobs": [
            {
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat()
                if job.next_run_time
                else None,
            }
            for job in jobs
        ],
    }
