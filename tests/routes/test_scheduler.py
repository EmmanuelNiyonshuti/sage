from unittest.mock import patch

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
@patch("app.scheduler.time_series_scheduler.TimeSeriesScheduler._process_parcels_job")
async def test_timeseries_scheduler_runs(mock_job, async_client: AsyncClient):
    from app.scheduler.time_series_scheduler import time_series_scheduler

    time_series_scheduler.start({"seconds": 1})
    for job in time_series_scheduler.get_jobs():
        job.func()
    assert mock_job.called
    assert time_series_scheduler.is_running()


@pytest.mark.anyio
@patch("app.scheduler.ingestion_scheduler.IngestionScheduler._process_due_parcels_job")
async def test_ingestion_scheduler_runs(mock_job, async_client: AsyncClient):
    from app.scheduler.ingestion_scheduler import ingestion_scheduler

    ingestion_scheduler.start({"seconds": 1})
    for job in ingestion_scheduler.get_jobs():
        job.func()
    assert mock_job.called
    assert ingestion_scheduler.is_running()
