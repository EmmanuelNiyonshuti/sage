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
    title="Spatial Agronomic Geo Engine API",
    summary="""
    A backend that ingests geospatial data about agricultural land parcels,
    processes it into useful agricultural insights, stores the results,
    and exposes them via REST API for internal tools, dashboards, or other services that needs them.
    """,
    lifespan=lifespan,
)

app.add_middleware(CorrelationIdMiddleware)


app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
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
