"""
ErrorsService — aggregates errors from cron jobs and auth-profiles.

Sources:
  1. cron/jobs.json  — consecutiveErrors > 0 or lastError set
  2. agents/*/agent/auth-profiles.json — errorCount > 0 in usageStats
"""
import os
from datetime import datetime, timezone
from typing import Any, Optional

from ..config import settings
from ..schemas import ErrorItem, ErrorsResponse
from .file_watcher import FileWatcher
from .jobs_parser import AGENT_ID_TO_NAME


class ErrorsService:
    """Collects and classifies errors across the PLAMYA system."""

    def __init__(self, file_watcher: FileWatcher, plamya_dir: Optional[str] = None):
        self.fw = file_watcher
        self.base = plamya_dir or settings.plamya_dir

    def _path(self, *parts: str) -> str:
        return os.path.join(self.base, *parts)

    def get_all_errors(self) -> ErrorsResponse:
        """Aggregate errors from cron jobs and API auth profiles."""
        errors: list[ErrorItem] = []

        # 1. Cron job errors
        errors.extend(self._collect_cron_errors())

        # 2. API auth-profile errors
        errors.extend(self._collect_api_errors())

        # Sort: highest severity first, then by consecutive count descending
        severity_order = {"error": 0, "warning": 1, "info": 2}
        errors.sort(key=lambda e: (severity_order.get(e.severity, 3), -e.consecutive))

        return ErrorsResponse(
            total_errors=len(errors),
            groups=errors,
        )

    # ── cron errors ──────────────────────────────────

    def _collect_cron_errors(self) -> list[ErrorItem]:
        """Read jobs.json for any cron job with errors."""
        data = self.fw.read_json(self._path("cron", "jobs.json"))
        if not data or not isinstance(data, dict):
            return []

        results: list[ErrorItem] = []
        for job in data.get("jobs", []):
            state = job.get("state", {})
            consecutive = state.get("consecutiveErrors", 0)
            last_error = state.get("lastError")

            if consecutive <= 0 and not last_error:
                continue

            agent_id = job.get("agentId") or "main"
            agent_name = AGENT_ID_TO_NAME.get(agent_id, agent_id)

            # Determine severity
            if consecutive > 3:
                severity = "error"
            elif consecutive > 0:
                severity = "warning"
            else:
                severity = "info"

            last_run_ms = state.get("lastRunAtMs")
            last_at = _ms_to_iso(last_run_ms)

            results.append(
                ErrorItem(
                    source="cron",
                    job_name=job.get("name", "unknown"),
                    agent=agent_id,
                    agent_name=agent_name,
                    error=last_error,
                    consecutive=consecutive,
                    last_at=last_at,
                    severity=severity,
                )
            )

        return results

    # ── API auth-profile errors ──────────────────────

    def _collect_api_errors(self) -> list[ErrorItem]:
        """Scan all agent auth-profiles for API errors."""
        results: list[ErrorItem] = []

        agents_dir = self._path("agents")
        if not os.path.isdir(agents_dir):
            return results

        try:
            agent_dirs = os.listdir(agents_dir)
        except OSError:
            return results

        for agent_id in agent_dirs:
            profile_path = os.path.join(agents_dir, agent_id, "agent", "auth-profiles.json")
            data = self.fw.read_json(profile_path)
            if not data:
                continue

            usage_stats = data.get("usageStats", {})
            agent_name = AGENT_ID_TO_NAME.get(agent_id, agent_id)

            for profile_key, stats in usage_stats.items():
                error_count = stats.get("errorCount", 0)
                if error_count <= 0:
                    continue

                provider = profile_key.split(":")[0] if ":" in profile_key else profile_key

                last_failure_ms = stats.get("lastFailureAt")
                last_at = _ms_to_iso(last_failure_ms)

                # API errors are generally informational unless persistent
                severity = "info"
                if error_count > 5:
                    severity = "warning"
                if error_count > 20:
                    severity = "error"

                results.append(
                    ErrorItem(
                        source="api",
                        agent=agent_id,
                        agent_name=agent_name,
                        provider=provider,
                        error=f"{error_count} API error(s)",
                        consecutive=error_count,
                        last_at=last_at,
                        severity=severity,
                    )
                )

        return results


def _ms_to_iso(ms: Optional[int]) -> Optional[str]:
    """Convert epoch milliseconds to ISO 8601 string."""
    if not ms:
        return None
    try:
        dt = datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except (OSError, ValueError):
        return None
