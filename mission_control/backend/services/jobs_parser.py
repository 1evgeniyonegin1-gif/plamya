"""
Parse ~/.plamya/cron/jobs.json — enriched cron job list.

Converts raw schedule definitions into human-readable Russian strings
and calculates time-until-next-run.
"""
import time
from datetime import datetime, timezone
from typing import Any, Optional

from ..schemas import CronJob


# Agent ID -> human-readable Russian name
AGENT_ID_TO_NAME: dict[str, str] = {
    "main": "Альтрон",
    "hunter": "Хантер",
    "coder": "Кодер",
    "scanner": "Сканер",
    "chappie": "Чаппи",
    "empat": "Эмпат",
    "growth": "Гроус",
}


def _schedule_to_human(schedule: dict) -> str:
    """Convert a schedule object to human-readable Russian string."""
    kind = schedule.get("kind", "")

    if kind == "every":
        every_ms = schedule.get("everyMs", 0)
        if every_ms <= 0:
            return "неизвестно"
        minutes = every_ms // 60_000
        if minutes < 60:
            return f"каждые {minutes} мин"
        hours = minutes // 60
        if hours == 1:
            return "каждый час"
        if hours < 24:
            return f"каждые {hours}ч"
        days = hours // 24
        return f"каждые {days}д"

    if kind == "cron":
        expr = schedule.get("expr", "")
        return _cron_expr_to_human(expr)

    return kind


def _cron_expr_to_human(expr: str) -> str:
    """Best-effort conversion of a cron expression to Russian."""
    parts = expr.strip().split()
    if len(parts) < 5:
        return f"cron: {expr}"

    minute, hour, dom, month, dow = parts[:5]

    # "0 6 * * *" -> "ежедневно в 06:00 MSK"
    if dom == "*" and month == "*" and dow == "*":
        try:
            h = int(hour)
            m = int(minute)
            # Cron is stored in UTC; plamya runs UTC, display in MSK (+3)
            msk_h = (h + 3) % 24
            return f"ежедневно в {msk_h:02d}:{m:02d} MSK"
        except ValueError:
            pass

    # "0 */2 * * *" -> "каждые 2ч"
    if hour.startswith("*/"):
        try:
            interval = int(hour[2:])
            return f"каждые {interval}ч"
        except ValueError:
            pass

    return f"cron: {expr}"


def _ms_to_iso(ms: Optional[int]) -> Optional[str]:
    """Convert epoch milliseconds to ISO 8601 string."""
    if not ms:
        return None
    try:
        dt = datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except (OSError, ValueError):
        return None


def _time_until(ms: Optional[int]) -> Optional[str]:
    """Human-readable time until a future epoch-ms timestamp."""
    if not ms:
        return None
    now_ms = int(time.time() * 1000)
    diff_ms = ms - now_ms
    if diff_ms <= 0:
        return "сейчас"
    diff_s = diff_ms // 1000
    if diff_s < 60:
        return f"{diff_s}с"
    diff_m = diff_s // 60
    if diff_m < 60:
        return f"{diff_m} мин"
    diff_h = diff_m // 60
    remaining_m = diff_m % 60
    if diff_h < 24:
        if remaining_m:
            return f"{diff_h}ч {remaining_m}мин"
        return f"{diff_h}ч"
    diff_d = diff_h // 24
    return f"{diff_d}д {diff_h % 24}ч"


def parse_jobs_json(data: Any) -> list[CronJob]:
    """Parse the jobs.json dict into a list of enriched CronJob models."""
    if not isinstance(data, dict):
        return []

    jobs_raw = data.get("jobs", [])
    result: list[CronJob] = []

    for job in jobs_raw:
        agent_id = job.get("agentId")  # None means main agent
        agent_name = AGENT_ID_TO_NAME.get(agent_id or "main", agent_id or "main")

        schedule = job.get("schedule", {})
        schedule_human = _schedule_to_human(schedule)

        state = job.get("state", {})
        last_run_ms = state.get("lastRunAtMs")
        next_run_ms = state.get("nextRunAtMs")

        result.append(
            CronJob(
                id=job.get("id", ""),
                name=job.get("name", ""),
                agent_id=agent_id,
                agent_name=agent_name,
                enabled=job.get("enabled", True),
                schedule_human=schedule_human,
                last_status=state.get("lastStatus"),
                last_run_at=_ms_to_iso(last_run_ms),
                last_duration_ms=state.get("lastDurationMs"),
                next_run_at=_ms_to_iso(next_run_ms),
                consecutive_errors=state.get("consecutiveErrors", 0),
                last_error=state.get("lastError"),
            )
        )

    return result


def get_next_job(jobs: list[CronJob]) -> tuple[Optional[str], Optional[str]]:
    """Return (next_job_name, time_until_next) for the soonest enabled job."""
    if not jobs:
        return None, None

    # Re-parse raw data isn't available, but we stored next_run_at as ISO.
    # Instead, use the raw ms from the original data.  Since we don't keep
    # the raw ms in CronJob, we'll need the caller to pass it.
    # For now, return the first enabled job by next_run_at lexicographic order.
    enabled_with_next = [
        j for j in jobs
        if j.enabled and j.next_run_at
    ]
    if not enabled_with_next:
        return None, None

    soonest = min(enabled_with_next, key=lambda j: j.next_run_at or "")
    return soonest.name, None  # time_until calculated at response time


def get_next_job_from_raw(data: Any) -> tuple[Optional[str], Optional[str]]:
    """Return (next_job_name, human_time_until) from raw jobs.json data."""
    if not isinstance(data, dict):
        return None, None

    jobs_raw = data.get("jobs", [])
    enabled = [j for j in jobs_raw if j.get("enabled", True)]
    if not enabled:
        return None, None

    def _next_ms(j):
        return j.get("state", {}).get("nextRunAtMs", float("inf"))

    soonest = min(enabled, key=_next_ms)
    next_ms = _next_ms(soonest)
    name = soonest.get("name", "unknown")
    human_until = _time_until(next_ms if next_ms != float("inf") else None)
    return name, human_until
