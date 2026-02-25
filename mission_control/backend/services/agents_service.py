"""
AgentsService — aggregates data from plamya.json, STATUS.md,
jobs.json, auth-profiles.json and INBOX.md into unified agent views.
"""
import os
from datetime import datetime, timezone
from typing import Any, Optional

from ..config import settings
from ..schemas import AgentDetail, AgentStatus, AgentsResponse, InboxMessage
from .file_watcher import FileWatcher
from .inbox_parser import ParsedInboxMessage, parse_inbox_md
from .jobs_parser import get_next_job_from_raw, parse_jobs_json
from .status_parser import AGENT_ID_TO_NAME, parse_status_md


class AgentsService:
    """Reads PLAMYA files and aggregates them into agent status objects."""

    def __init__(self, file_watcher: FileWatcher, plamya_dir: Optional[str] = None):
        self.fw = file_watcher
        self.base = plamya_dir or settings.plamya_dir

    # ── path helpers ─────────────────────────────────

    def _path(self, *parts: str) -> str:
        return os.path.join(self.base, *parts)

    # ── public API ───────────────────────────────────

    def get_all_agents(self) -> AgentsResponse:
        """Return a summary of every known agent."""
        plamya_cfg = self.fw.read_json(self._path("plamya.json")) or {}
        status_entries = self._read_status()
        jobs_data = self.fw.read_json(self._path("cron", "jobs.json")) or {}
        inbox_msgs = self._read_inbox()

        agents_cfg = plamya_cfg.get("agents", {})
        defaults = agents_cfg.get("defaults", {})
        agent_list = agents_cfg.get("list", [])

        # Pre-index status by agent_id
        status_map = {e.agent_id: e for e in status_entries}

        # Pre-index cron jobs by agent_id
        parsed_jobs = parse_jobs_json(jobs_data)
        jobs_by_agent: dict[str, list] = {}
        total_cron_errors = 0
        for j in parsed_jobs:
            aid = j.agent_id or "main"
            jobs_by_agent.setdefault(aid, []).append(j)
            total_cron_errors += j.consecutive_errors

        # Pre-index inbox messages by agent (recipient or sender)
        inbox_by_agent: dict[str, int] = {}
        for msg in inbox_msgs:
            for name, aid in _NAME_TO_ID.items():
                if name.upper() in msg.sender.upper() or name.upper() in msg.recipient.upper():
                    inbox_by_agent[aid] = inbox_by_agent.get(aid, 0) + 1

        result: list[AgentStatus] = []
        seen_ids: set[str] = set()

        for agent_cfg in agent_list:
            aid = agent_cfg.get("id", "unknown")
            seen_ids.add(aid)
            status = self._build_agent_status(
                agent_cfg, defaults, status_map, jobs_by_agent, inbox_by_agent,
            )
            result.append(status)

        # Also include agents from STATUS.md that aren't in plamya.json
        for entry in status_entries:
            if entry.agent_id not in seen_ids:
                result.append(
                    AgentStatus(
                        id=entry.agent_id,
                        name=entry.agent_name,
                        status=entry.status,
                        status_emoji=entry.status_emoji,
                        last_heartbeat=entry.last_heartbeat,
                        current_task=entry.current_task,
                        inbox_messages_count=inbox_by_agent.get(entry.agent_id, 0),
                    )
                )

        next_job_name, next_job_in = get_next_job_from_raw(jobs_data)

        return AgentsResponse(
            agents=result,
            total_cron_jobs=len(parsed_jobs),
            total_cron_errors=total_cron_errors,
            total_inbox_messages=len(inbox_msgs),
            last_updated=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        )

    def get_agent_detail(self, agent_id: str) -> Optional[AgentDetail]:
        """Return detailed info for a single agent."""
        plamya_cfg = self.fw.read_json(self._path("plamya.json")) or {}
        status_entries = self._read_status()
        jobs_data = self.fw.read_json(self._path("cron", "jobs.json")) or {}
        inbox_msgs = self._read_inbox()

        agents_cfg = plamya_cfg.get("agents", {})
        defaults = agents_cfg.get("defaults", {})
        agent_list = agents_cfg.get("list", [])

        # Find agent config
        agent_cfg = None
        for a in agent_list:
            if a.get("id") == agent_id:
                agent_cfg = a
                break

        status_map = {e.agent_id: e for e in status_entries}

        # Cron jobs for this agent
        parsed_jobs = parse_jobs_json(jobs_data)
        agent_jobs = [
            j for j in parsed_jobs
            if (j.agent_id or "main") == agent_id
        ]

        # Inbox messages involving this agent
        agent_name_ru = AGENT_ID_TO_NAME.get(agent_id, agent_id).upper()
        agent_inbox: list[InboxMessage] = []
        for i, msg in enumerate(inbox_msgs):
            if agent_name_ru in msg.sender.upper() or agent_name_ru in msg.recipient.upper():
                agent_inbox.append(
                    InboxMessage(
                        id=msg.id,
                        timestamp=msg.timestamp,
                        sender=msg.sender,
                        recipient=msg.recipient,
                        subject=msg.subject,
                        preview=msg.preview,
                        full_text=msg.full_text,
                        priority=msg.priority,
                    )
                )
            if len(agent_inbox) >= 10:
                break

        # Jobs count / errors
        jobs_by_agent: dict[str, list] = {}
        for j in parsed_jobs:
            aid = j.agent_id or "main"
            jobs_by_agent.setdefault(aid, []).append(j)

        inbox_by_agent: dict[str, int] = {}
        for msg in inbox_msgs:
            for name, aid in _NAME_TO_ID.items():
                if name.upper() in msg.sender.upper() or name.upper() in msg.recipient.upper():
                    inbox_by_agent[aid] = inbox_by_agent.get(aid, 0) + 1

        if agent_cfg is not None:
            base_status = self._build_agent_status(
                agent_cfg, defaults, status_map, jobs_by_agent, inbox_by_agent,
            )
        elif agent_id in status_map:
            entry = status_map[agent_id]
            base_status = AgentStatus(
                id=entry.agent_id,
                name=entry.agent_name,
                status=entry.status,
                status_emoji=entry.status_emoji,
                last_heartbeat=entry.last_heartbeat,
                current_task=entry.current_task,
                inbox_messages_count=inbox_by_agent.get(agent_id, 0),
            )
        else:
            return None

        # Special data for chappie
        chappie_data = None
        if agent_id == "chappie":
            chappie_data = self._read_chappie_data()

        # Special data for producer
        producer_data = None
        if agent_id == "producer":
            producer_data = self._read_producer_data()

        # Special data for hunter (CRM)
        hunter_data = None
        if agent_id == "hunter":
            hunter_data = self._read_hunter_data()

        # CRM summary (if CRM.sqlite exists)
        crm_summary = None
        crm_path = self._path("shared", "CRM.sqlite")
        if os.path.isfile(crm_path):
            crm_summary = {"path": crm_path, "exists": True}

        return AgentDetail(
            **base_status.model_dump(),
            cron_jobs=agent_jobs,
            recent_inbox=agent_inbox,
            chappie_data=chappie_data,
            producer_data=producer_data,
            hunter_data=hunter_data,
            crm_summary=crm_summary,
        )

    # ── internal helpers ─────────────────────────────

    def _read_status(self) -> list:
        raw = self.fw.read_text(self._path("shared", "STATUS.md"))
        if not raw:
            return []
        return parse_status_md(raw)

    def _read_inbox(self) -> list[ParsedInboxMessage]:
        raw = self.fw.read_text(self._path("shared", "INBOX.md"))
        if not raw:
            return []
        return parse_inbox_md(raw)

    def _build_agent_status(
        self,
        agent_cfg: dict,
        defaults: dict,
        status_map: dict,
        jobs_by_agent: dict,
        inbox_by_agent: dict,
    ) -> AgentStatus:
        """Build an AgentStatus from config + status + jobs + inbox."""
        aid = agent_cfg.get("id", "unknown")

        # Model info (merge agent-level with defaults)
        model_cfg = agent_cfg.get("model", defaults.get("model", {}))
        if isinstance(model_cfg, str):
            model_primary = model_cfg
            model_fallbacks = []
        elif isinstance(model_cfg, dict):
            model_primary = model_cfg.get("primary")
            model_fallbacks = model_cfg.get("fallbacks", [])
        else:
            model_primary = None
            model_fallbacks = []

        # Human name
        name = AGENT_ID_TO_NAME.get(aid, agent_cfg.get("name", aid))

        # Status from STATUS.md
        entry = status_map.get(aid)
        status = entry.status if entry else None
        status_emoji = entry.status_emoji if entry else None
        last_heartbeat = entry.last_heartbeat if entry else None
        current_task = entry.current_task if entry else None

        # Cron jobs
        agent_jobs = jobs_by_agent.get(aid, [])
        cron_count = len(agent_jobs)
        cron_errors = sum(j.consecutive_errors for j in agent_jobs)

        # Inbox
        inbox_count = inbox_by_agent.get(aid, 0)

        # API usage from auth-profiles
        api_usage = self._read_api_usage(aid)

        return AgentStatus(
            id=aid,
            name=name,
            model_primary=model_primary,
            model_fallbacks=model_fallbacks,
            status=status,
            status_emoji=status_emoji,
            last_heartbeat=last_heartbeat,
            current_task=current_task,
            cron_jobs_count=cron_count,
            cron_errors=cron_errors,
            inbox_messages_count=inbox_count,
            api_usage=api_usage,
        )

    def _read_api_usage(self, agent_id: str) -> dict:
        """Read auth-profiles.json for an agent and extract usage stats."""
        # Try agent-specific path first, then main
        agent_dir = self._path("agents", agent_id, "agent")
        profile_path = os.path.join(agent_dir, "auth-profiles.json")
        data = self.fw.read_json(profile_path)
        if not data:
            return {}

        usage_stats = data.get("usageStats", {})
        result = {}
        for profile_key, stats in usage_stats.items():
            provider = profile_key.split(":")[0] if ":" in profile_key else profile_key
            result[provider] = {
                "last_used": stats.get("lastUsed"),
                "error_count": stats.get("errorCount", 0),
                "last_failure_at": stats.get("lastFailureAt"),
            }
        return result

    def _read_chappie_data(self) -> Optional[dict]:
        """Read Chappie-specific shared state files."""
        result = {}

        # Goals
        goals = self.fw.read_json(self._path("shared", "CHAPPIE_GOALS.json"))
        if goals:
            result["goals"] = goals

        # State
        state = self.fw.read_json(self._path("shared", "CHAPPIE_STATE.json"))
        if state:
            result["state"] = state

        # Knowledge
        knowledge = self.fw.read_json(self._path("shared", "CHAPPIE_KNOWLEDGE.json"))
        if knowledge:
            result["knowledge_items"] = (
                len(knowledge) if isinstance(knowledge, list)
                else len(knowledge.get("items", [])) if isinstance(knowledge, dict)
                else 0
            )

        # Problems
        problems = self.fw.read_json(self._path("shared", "CHAPPIE_PROBLEMS.json"))
        if problems:
            result["problems_count"] = (
                len(problems) if isinstance(problems, list)
                else len(problems.get("problems", [])) if isinstance(problems, dict)
                else 0
            )

        return result if result else None

    def _read_producer_data(self) -> Optional[dict]:
        """Read Producer-specific shared state files."""
        result = {}

        state = self.fw.read_json(self._path("shared", "PRODUCER_STATE.json"))
        if state:
            result["state"] = state

        niches = self.fw.read_json(self._path("shared", "PRODUCER_NICHES.json"))
        if niches:
            niche_list = niches if isinstance(niches, list) else niches.get("niches", [])
            result["total_niches"] = len(niche_list)
            result["qualified_niches"] = sum(
                1 for n in niche_list
                if isinstance(n, dict) and n.get("score", 0) >= 70
            )

        products = self.fw.read_json(self._path("shared", "PRODUCER_PRODUCTS.json"))
        if products:
            prod_list = products if isinstance(products, list) else products.get("products", [])
            result["total_products"] = len(prod_list)
            result["products"] = prod_list[:5]  # Last 5

        pipeline = self.fw.read_json(self._path("shared", "PRODUCER_PIPELINE.json"))
        if pipeline:
            result["pipeline"] = pipeline

        return result if result else None

    def _read_hunter_data(self) -> Optional[dict]:
        """Read Hunter CRM data from CRM.sqlite."""
        import sqlite3

        crm_path = self._path("shared", "CRM.sqlite")
        if not os.path.isfile(crm_path):
            return None

        try:
            conn = sqlite3.connect(crm_path)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            # Count leads by status
            cur.execute("SELECT status, COUNT(*) as cnt FROM leads GROUP BY status")
            counts = {row["status"]: row["cnt"] for row in cur.fetchall()}

            cur.execute("SELECT COUNT(*) FROM leads")
            total = cur.fetchone()[0]

            # Last 5 leads
            cur.execute(
                "SELECT id, title, source, score, status, created_at "
                "FROM leads ORDER BY created_at DESC LIMIT 5"
            )
            recent = [dict(row) for row in cur.fetchall()]

            conn.close()

            return {
                "total_leads": total,
                "qualified": counts.get("qualified", 0),
                "proposed": counts.get("proposed", 0),
                "won": counts.get("won", 0),
                "recent_leads": recent,
            }
        except Exception:
            return None


# Helper name-to-id map (lowercase keys)
_NAME_TO_ID: dict[str, str] = {
    "альтрон": "main",
    "данил": "admin",
    "хантер": "hunter",
    "кодер": "coder",
    "сканер": "scanner",
    "чаппи": "chappie",
    "эмпат": "empat",
    "продюсер": "producer",
}
