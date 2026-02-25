"""
Tasks API — CRUD for TASKS.md task board.
"""
import os

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from ..config import settings
from ..services.tasks_service import (
    create_task,
    delete_task,
    parse_tasks_md,
    update_task_done,
)

router = APIRouter(prefix="/tasks", tags=["Tasks"])


# ── Schemas ──────────────────────────────────────────

class TaskItem(BaseModel):
    id: int
    text: str
    assignee: str
    assignee_id: str
    priority: str
    done: bool
    section: str


class TasksListResponse(BaseModel):
    tasks: list[TaskItem]
    total: int
    done_count: int


class CreateTaskRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=1000)
    assignee_id: str = Field(..., description="Agent ID to assign to")
    priority: str = Field(default="СРЕДНИЙ", pattern=r"^(КРИТИЧНО|ВЫСОКИЙ|СРЕДНИЙ|НИЗКИЙ)$")


class CreateTaskResponse(BaseModel):
    ok: bool
    task_position: int


# ── Endpoints ────────────────────────────────────────

@router.get("", response_model=TasksListResponse)
async def list_tasks(request: Request, assignee: str | None = None):
    """List all tasks from TASKS.md."""
    fw = request.app.state.file_watcher
    path = os.path.join(settings.plamya_dir, "shared", "TASKS.md")
    raw = fw.read_text(path) or ""
    tasks = parse_tasks_md(raw)

    if assignee:
        tasks = [t for t in tasks if t.assignee_id == assignee]

    return TasksListResponse(
        tasks=[
            TaskItem(
                id=t.id,
                text=t.text,
                assignee=t.assignee,
                assignee_id=t.assignee_id,
                priority=t.priority,
                done=t.done,
                section=t.section,
            )
            for t in tasks
        ],
        total=len(tasks),
        done_count=sum(1 for t in tasks if t.done),
    )


@router.post("", response_model=CreateTaskResponse)
async def create_new_task(body: CreateTaskRequest):
    """Create a new task in TASKS.md."""
    pos = create_task(body.text, body.assignee_id, body.priority)
    return CreateTaskResponse(ok=True, task_position=pos)


@router.put("/{task_id}/status")
async def toggle_task_status(task_id: int, done: bool = True):
    """Mark a task as done or undone."""
    ok = update_task_done(task_id, done)
    return {"ok": ok, "task_id": task_id, "done": done}


@router.delete("/{task_id}")
async def remove_task(task_id: int):
    """Delete a task from TASKS.md."""
    ok = delete_task(task_id)
    return {"ok": ok, "task_id": task_id}
