"""
Traffic Engine API — overview and errors monitoring.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..api.auth import get_current_user
from ..schemas import (
    TrafficOverviewResponse, AccountOut, TodayStats, LastComment,
    TrafficErrorsResponse, ErrorGroup, UserInfo,
)
from ..services.traffic_service import get_overview, get_errors

router = APIRouter(prefix="/traffic", tags=["Traffic Engine"])


@router.get("/overview", response_model=TrafficOverviewResponse)
async def traffic_overview(
    db: AsyncSession = Depends(get_db),
    user: UserInfo = Depends(get_current_user),
):
    if not user.is_admin:
        return TrafficOverviewResponse(accounts=[], today_stats=TodayStats(comments_ok=0, comments_fail=0, stories=0, invites=0, replies=0))

    data = await get_overview(db)
    accounts = [
        AccountOut(
            id=a.id,
            phone=a.phone[-4:].rjust(len(a.phone), '*'),  # mask phone
            first_name=a.first_name,
            username=a.username,
            segment=a.segment,
            status=a.status,
            daily_comments=a.daily_comments,
            daily_invites=a.daily_invites,
            daily_story_views=a.daily_story_views,
            daily_story_reactions=a.daily_story_reactions,
            last_used_at=a.last_used_at,
            warmup_completed=a.warmup_completed,
            linked_channel_username=a.linked_channel_username,
        )
        for a in data["accounts"]
    ]

    last_comment = None
    if data["last_comment"]:
        lc = data["last_comment"]
        last_comment = LastComment(text=lc["text"], channel=lc["channel"], strategy=lc["strategy"], time=lc["time"])

    return TrafficOverviewResponse(
        accounts=accounts,
        today_stats=TodayStats(**data["today_stats"]),
        last_comment=last_comment,
    )


@router.get("/errors", response_model=TrafficErrorsResponse)
async def traffic_errors(
    hours: int = Query(24, ge=1, le=168),
    db: AsyncSession = Depends(get_db),
    user: UserInfo = Depends(get_current_user),
):
    if not user.is_admin:
        return TrafficErrorsResponse(total=0, groups=[])

    data = await get_errors(db, hours=hours)
    return TrafficErrorsResponse(
        total=data["total"],
        groups=[ErrorGroup(**g) for g in data["groups"]],
    )
