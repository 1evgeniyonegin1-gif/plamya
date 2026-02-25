"""
Leads API — CRUD for biz_scanner leads + AI dialog.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..services.leads_service import (
    get_leads,
    get_lead,
    get_dialog_history,
    get_leads_stats,
    update_lead_status,
    generate_dialog_response,
)

router = APIRouter(prefix="/leads", tags=["leads"])


class StatusUpdate(BaseModel):
    status: str
    notes: str = ""


class DialogRequest(BaseModel):
    client_message: str
    platform: str = "telegram"


# ── List leads ──────────────────────────────────

@router.get("")
async def list_leads(
    status: str = None,
    city: str = None,
    category: str = None,
    priority: str = None,
    limit: int = 50,
    offset: int = 0,
):
    """Get leads list with filters."""
    return get_leads(
        status=status,
        city=city,
        category=category,
        priority=priority,
        limit=limit,
        offset=offset,
    )


# ── Lead detail ─────────────────────────────────

@router.get("/stats")
async def leads_stats():
    """Get leads statistics."""
    return get_leads_stats()


@router.get("/{lead_id}")
async def lead_detail(lead_id: int):
    """Get single lead with contacts, proposals, dialog history."""
    lead = get_lead(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    # Add dialog history
    lead["dialog_history"] = get_dialog_history(lead_id)
    return lead


# ── Update status ───────────────────────────────

@router.post("/{lead_id}/status")
async def change_status(lead_id: int, body: StatusUpdate):
    """Update lead status."""
    ok = update_lead_status(lead_id, body.status, body.notes)
    if not ok:
        raise HTTPException(status_code=404, detail="Lead not found")
    return {"ok": True, "status": body.status}


# ── AI Dialog ───────────────────────────────────

@router.post("/{lead_id}/dialog")
async def dialog(lead_id: int, body: DialogRequest):
    """Send client message, get AI-generated response.

    Flow:
    1. Client message saved to outreach_log
    2. AI generates response based on lead context + dialog history
    3. AI response saved to outreach_log
    4. Returns: ai_response + tips for Danil
    """
    result = await generate_dialog_response(
        lead_id=lead_id,
        client_message=body.client_message,
        platform=body.platform,
    )

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result


# ── Dialog history ──────────────────────────────

@router.get("/{lead_id}/history")
async def dialog_history(lead_id: int):
    """Get dialog history for a lead."""
    lead = get_lead(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    history = get_dialog_history(lead_id)
    return {"lead_id": lead_id, "messages": history}
