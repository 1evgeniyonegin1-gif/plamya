"""
Cron API — list all cron jobs with enriched schedule info + controls.
"""
import os

from fastapi import APIRouter, Request

from ..config import settings
from ..schemas import CronResponse
from ..services.jobs_parser import get_next_job_from_raw, parse_jobs_json
from ..services.jobs_writer import toggle_job, trigger_job

router = APIRouter(prefix="/cron", tags=["Cron"])


@router.get("/jobs", response_model=CronResponse)
async def list_cron_jobs(request: Request):
    """Return all cron jobs with human-readable schedules and status."""
    file_watcher = request.app.state.file_watcher
    jobs_path = os.path.join(settings.plamya_dir, "cron", "jobs.json")

    data = file_watcher.read_json(jobs_path)
    if not data:
        return CronResponse(jobs=[], total_enabled=0, total_errors=0)

    jobs = parse_jobs_json(data)
    enabled_jobs = [j for j in jobs if j.enabled]
    total_errors = sum(j.consecutive_errors for j in jobs)

    next_job_name, next_job_in = get_next_job_from_raw(data)

    return CronResponse(
        jobs=jobs,
        total_enabled=len(enabled_jobs),
        total_errors=total_errors,
        next_job_name=next_job_name,
        next_job_in=next_job_in,
    )


@router.post("/jobs/{job_id}/toggle")
async def toggle_cron_job(job_id: str):
    """Toggle a cron job's enabled state. Hot-reloaded by gateway."""
    result = toggle_job(job_id)
    if result is None:
        return {"ok": False, "error": "Job not found"}
    return {"ok": True, **result}


@router.post("/jobs/{job_id}/trigger")
async def trigger_cron_job(job_id: str):
    """Trigger a cron job to run immediately by setting nextRunAtMs=now."""
    result = trigger_job(job_id)
    if result is None:
        return {"ok": False, "error": "Job not found"}
    return {"ok": True, **result}
