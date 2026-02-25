"""
Projects API — CRUD for PROJECTS_REGISTRY.json.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from ..services.projects_service import (
    get_all_projects,
    get_project,
    update_project,
    get_summary,
    get_my_tasks,
    toggle_my_task,
    respond_my_task,
)

router = APIRouter(prefix="/projects", tags=["projects"])


class ProjectUpdate(BaseModel):
    completion_pct: Optional[int] = None
    next_step: Optional[str] = None
    mrr: Optional[int] = None
    category: Optional[str] = None


@router.get("")
async def list_projects():
    """Return all projects with subprojects."""
    return get_all_projects()


@router.get("/summary")
async def projects_summary():
    """Return summary stats for dashboard header."""
    return get_summary()


@router.get("/my-tasks")
async def list_my_tasks():
    """Return tasks that require Danil's personal action."""
    tasks = get_my_tasks()
    pending = [t for t in tasks if not t.get("done", False)]
    return {"tasks": tasks, "total": len(tasks), "pending": len(pending)}


@router.post("/my-tasks/{task_id}/done")
async def mark_my_task_done(task_id: str, done: bool = True):
    """Mark a personal task as done or undone."""
    task = toggle_my_task(task_id, done)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")
    return {"ok": True, "task": task}


class TaskResponse(BaseModel):
    decision: str  # "approve", "reject", or custom text
    message: str = ""


@router.post("/my-tasks/{task_id}/respond")
async def respond_to_task(task_id: str, body: TaskResponse):
    """Respond to a task with approve/reject/custom + optional message. Writes to INBOX.md."""
    task = respond_my_task(task_id, body.decision, body.message)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")
    return {"ok": True, "task": task}


@router.get("/{project_id}")
async def project_detail(project_id: str):
    """Return single project details."""
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")
    return project


@router.put("/{project_id}")
async def update_project_endpoint(project_id: str, body: ProjectUpdate):
    """Update project status fields."""
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    project = update_project(project_id, updates)
    if not project:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")
    return {"ok": True, "project": project}
