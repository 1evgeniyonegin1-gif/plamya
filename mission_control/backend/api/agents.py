"""
Agents API — list all agents and get individual agent details.
"""
from fastapi import APIRouter, HTTPException, Request

from ..schemas import AgentDetail, AgentsResponse

router = APIRouter(prefix="/agents", tags=["Agents"])


@router.get("", response_model=AgentsResponse)
async def list_agents(request: Request):
    """Return summary status of all known agents."""
    agents_service = request.app.state.agents_service
    return agents_service.get_all_agents()


@router.get("/{agent_id}", response_model=AgentDetail)
async def get_agent(agent_id: str, request: Request):
    """Return detailed info for a single agent."""
    agents_service = request.app.state.agents_service
    detail = agents_service.get_agent_detail(agent_id)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    return detail
