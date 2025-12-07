from contextlib import asynccontextmanager

from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI

from app.api.main import api_router
from app.logging_config import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    yield


app = FastAPI(
    title="Spatial Agronomic Geo Engine API",
    summary="""
    A backend that ingests geospatial data about agricultural land parcel,
    processes it into useful agricultural insights, stores the results,
    and exposes them via REST APIs for internal tools, dashboards, or other services.
    """,
    lifespan=lifespan,
)

app.add_middleware(CorrelationIdMiddleware)

app.include_router(api_router, prefix="/api")
