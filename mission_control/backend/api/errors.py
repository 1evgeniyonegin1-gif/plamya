"""
Errors API — aggregated errors from cron and API auth profiles.
"""
from fastapi import APIRouter, Request

from ..schemas import ErrorsResponse

router = APIRouter(prefix="/errors", tags=["Errors"])


@router.get("", response_model=ErrorsResponse)
async def list_errors(request: Request):
    """Return aggregated errors from all sources."""
    errors_service = request.app.state.errors_service
    return errors_service.get_all_errors()
