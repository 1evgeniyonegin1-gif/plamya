"""
TasksService — parse and write to TASKS.md.

Format:
    # TASKS — Общий таск-борд

    ## SECTION_NAME

    - [ ] [AGENT] Task text (срок: DATE, приоритет: LEVEL)
    - [x] [AGENT] Completed task
"""
import os
import re
from dataclasses import dataclass
from datetime import datetime

from ..config import settings
from .status_parser import AGENT_ID_TO_NAME


@dataclass
class Task:
    id: int
    text: str
    assignee: str  # agent display name
    assignee_id: str  # agent id
    priority: str  # "КРИТИЧНО" | "ВЫСОКИЙ" | "СРЕДНИЙ" | "НИЗКИЙ"
    done: bool
    section: str  # section header it belongs to


_TASK_RE = re.compile(
    r"^-\s+\[([ xX])\]\s+\[([^\]]+)\]\s+(.+)$"
)

_PRIORITY_RE = re.compile(r"приоритет:\s*(КРИТИЧНО|ВЫСОКИЙ|СРЕДНИЙ|НИЗКИЙ)", re.IGNORECASE)


def _tasks_path() -> str:
    return os.path.join(settings.plamya_dir, "shared", "TASKS.md")


def _assignee_to_id(name: str) -> str:
    from .status_parser import AGENT_NAME_TO_ID
    return AGENT_NAME_TO_ID.get(name.upper(), name.lower())


def parse_tasks_md(raw: str) -> list[Task]:
    """Parse TASKS.md into structured tasks."""
    tasks: list[Task] = []
    task_id = 0
    current_section = ""

    for line in raw.splitlines():
        line = line.rstrip()

        # Section headers (## or ###)
        if line.startswith("##"):
            current_section = line.lstrip("#").strip()
            continue

        m = _TASK_RE.match(line.strip())
        if m:
            task_id += 1
            done = m.group(1).lower() == "x"
            assignee = m.group(2).strip()
            rest = m.group(3).strip()

            # Extract priority from inline metadata
            pm = _PRIORITY_RE.search(rest)
            priority = pm.group(1).upper() if pm else "СРЕДНИЙ"

            # Clean task text (remove metadata in parens)
            text = re.sub(r"\s*\(срок:.*?\)", "", rest).strip()

            tasks.append(Task(
                id=task_id,
                text=text,
                assignee=assignee,
                assignee_id=_assignee_to_id(assignee),
                priority=priority,
                done=done,
                section=current_section,
            ))

    return tasks


def create_task(text: str, assignee_id: str, priority: str = "СРЕДНИЙ") -> int:
    """Create a new task in TASKS.md. Returns task position."""
    path = _tasks_path()
    raw = ""
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read()

    assignee_name = AGENT_ID_TO_NAME.get(assignee_id, assignee_id.upper())
    entry = f"- [ ] [{assignee_name}] {text} (приоритет: {priority})\n"

    # Append to file
    if not raw.strip():
        raw = "# TASKS — Общий таск-борд\n\n"

    with open(path, "a", encoding="utf-8") as f:
        f.write(entry)

    tasks = parse_tasks_md(raw + entry)
    return len(tasks)


def update_task_done(task_id: int, done: bool) -> bool:
    """Toggle task completion status by its sequential ID."""
    path = _tasks_path()
    if not os.path.isfile(path):
        return False

    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    current_id = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if _TASK_RE.match(stripped):
            current_id += 1
            if current_id == task_id:
                if done:
                    lines[i] = line.replace("- [ ]", "- [x]", 1)
                else:
                    lines[i] = line.replace("- [x]", "- [ ]", 1).replace("- [X]", "- [ ]", 1)
                with open(path, "w", encoding="utf-8") as f:
                    f.writelines(lines)
                return True

    return False


def delete_task(task_id: int) -> bool:
    """Remove a task by its sequential ID."""
    path = _tasks_path()
    if not os.path.isfile(path):
        return False

    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    current_id = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if _TASK_RE.match(stripped):
            current_id += 1
            if current_id == task_id:
                del lines[i]
                with open(path, "w", encoding="utf-8") as f:
                    f.writelines(lines)
                return True

    return False
