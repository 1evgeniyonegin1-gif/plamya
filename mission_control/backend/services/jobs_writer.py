"""
JobsWriter — edit cron/jobs.json to toggle and trigger jobs.

jobs.json is hot-reloaded by the PLAMYA gateway, so changes take effect
immediately without restarting.
"""
import json
import os
import time

from ..config import settings


def _jobs_path() -> str:
    return os.path.join(settings.plamya_dir, "cron", "jobs.json")


def _read_jobs() -> dict:
    path = _jobs_path()
    if not os.path.isfile(path):
        return {"version": 1, "jobs": []}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_jobs(data: dict) -> None:
    path = _jobs_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def toggle_job(job_id: str) -> dict | None:
    """Toggle a cron job's enabled state. Returns updated job or None."""
    data = _read_jobs()
    for job in data.get("jobs", []):
        if job.get("id") == job_id:
            job["enabled"] = not job.get("enabled", True)
            _write_jobs(data)
            return {"id": job_id, "enabled": job["enabled"], "name": job.get("name")}
    return None


def trigger_job(job_id: str) -> dict | None:
    """Set nextRunAtMs to now so the gateway picks it up immediately."""
    data = _read_jobs()
    now_ms = int(time.time() * 1000)
    for job in data.get("jobs", []):
        if job.get("id") == job_id:
            state = job.setdefault("state", {})
            state["nextRunAtMs"] = now_ms
            _write_jobs(data)
            return {"id": job_id, "triggered": True, "name": job.get("name")}
    return None
