"""
Projects Service — reads PROJECTS_REGISTRY.json from projects root.
"""
import json
import os
from typing import Optional

_REGISTRY_PATH = os.path.join(
    os.path.dirname(__file__),
    "..", "..", "..", "PROJECTS_REGISTRY.json"
)


def _load_registry() -> dict:
    path = os.path.abspath(_REGISTRY_PATH)
    if not os.path.isfile(path):
        return {"projects": [], "archived": [], "category_colors": {}, "updated_at": ""}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_registry(data: dict) -> None:
    path = os.path.abspath(_REGISTRY_PATH)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_all_projects() -> dict:
    return _load_registry()


def get_project(project_id: str) -> Optional[dict]:
    registry = _load_registry()
    for p in registry.get("projects", []):
        if p["id"] == project_id:
            return p
    return None


def update_project(project_id: str, updates: dict) -> Optional[dict]:
    """Update allowed fields: completion_pct, next_step, mrr, category."""
    registry = _load_registry()
    allowed = {"completion_pct", "next_step", "mrr", "category"}
    for p in registry.get("projects", []):
        if p["id"] == project_id:
            for k, v in updates.items():
                if k in allowed:
                    p[k] = v
            _save_registry(registry)
            return p
    return None


def get_my_tasks() -> list:
    """Return my_tasks from registry (tasks requiring Danil's personal action)."""
    registry = _load_registry()
    return registry.get("my_tasks", [])


def toggle_my_task(task_id: str, done: bool) -> Optional[dict]:
    """Mark a my_task as done or undone."""
    registry = _load_registry()
    for task in registry.get("my_tasks", []):
        if task["id"] == task_id:
            task["done"] = done
            _save_registry(registry)
            return task
    return None


def respond_my_task(task_id: str, decision: str, message: str = "") -> Optional[dict]:
    """Respond to a task: approve/reject/custom message. Marks as done."""
    registry = _load_registry()
    for task in registry.get("my_tasks", []):
        if task["id"] == task_id:
            task["done"] = True
            task["response"] = {
                "decision": decision,
                "message": message,
                "responded_at": _now_iso(),
            }
            _save_registry(registry)
            _write_to_inbox(task, decision, message)
            return task
    return None


def _now_iso() -> str:
    from datetime import datetime, timezone, timedelta
    msk = timezone(timedelta(hours=3))
    return datetime.now(msk).strftime("%Y-%m-%d %H:%M MSK")


def _write_to_inbox(task: dict, decision: str, message: str) -> None:
    """Write Danil's response to INBOX.md so NEXUS sees it."""
    import os
    inbox_path = os.path.expanduser("~/.plamya/shared/INBOX.md")
    if not os.path.isfile(inbox_path):
        return
    timestamp = _now_iso()
    decision_text = {"approve": "ОДОБРЕНО", "reject": "ОТКЛОНЕНО"}.get(decision, decision)
    entry = f"\n## [{timestamp}] ДАНИЛ → NEXUS\n"
    entry += f"**Задача:** {task.get('text', task['id'])}\n"
    entry += f"**Решение:** {decision_text}\n"
    if message:
        entry += f"**Комментарий:** {message}\n"
    entry += "\n"
    with open(inbox_path, "a", encoding="utf-8") as f:
        f.write(entry)


def get_summary() -> dict:
    registry = _load_registry()
    projects = registry.get("projects", [])
    total = len(projects)
    by_category = {}
    total_completion = 0
    for p in projects:
        cat = p.get("category", "unknown")
        by_category[cat] = by_category.get(cat, 0) + 1
        total_completion += p.get("completion_pct", 0)
    avg_completion = round(total_completion / total) if total else 0
    return {
        "total": total,
        "avg_completion": avg_completion,
        "by_category": by_category,
        "updated_at": registry.get("updated_at", ""),
    }
