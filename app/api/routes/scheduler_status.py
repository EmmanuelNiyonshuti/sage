from fastapi import APIRouter

from app.scheduler.ingestion_scheduler import ingestion_scheduler
from app.scheduler.time_series_scheduler import time_series_scheduler

router = APIRouter(tags=["Scheduler"])


@router.get("/scheduler/status")
async def scheduler_jobs_status():
    ingestion_jobs = ingestion_scheduler.get_jobs()
    time_series_jobs = time_series_scheduler.get_jobs()
    ingestion_jobs.extend(time_series_jobs)
    return {
        "ingestion-running": ingestion_scheduler.is_running(),
        "timeseries-running": time_series_scheduler.is_running(),
        "jobs": [
            {
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat()
                if job.next_run_time
                else None,
            }
            for job in ingestion_jobs
        ],
    }
