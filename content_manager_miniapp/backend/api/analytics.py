"""
Analytics API — dashboard, engagement timeline, top posts.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..api.auth import get_current_user
from ..schemas import (
    DashboardResponse, TypeBreakdown,
    EngagementResponse, TimelinePoint,
    TopPostsResponse, TopPostOut, UserInfo,
)
from ..services.analytics_service import get_dashboard, get_engagement_timeline, get_top_posts

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/dashboard", response_model=DashboardResponse)
async def dashboard(
    days: int = Query(7, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    user: UserInfo = Depends(get_current_user),
):
    data = await get_dashboard(db, days=days)
    return DashboardResponse(
        total_posts=data["total_posts"],
        published_today=data["published_today"],
        avg_engagement=data["avg_engagement"],
        pending_count=data["pending_count"],
        type_breakdown=[TypeBreakdown(**t) for t in data["type_breakdown"]],
    )


@router.get("/engagement", response_model=EngagementResponse)
async def engagement(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    user: UserInfo = Depends(get_current_user),
):
    timeline = await get_engagement_timeline(db, days=days)
    return EngagementResponse(timeline=[TimelinePoint(**t) for t in timeline])


@router.get("/top-posts", response_model=TopPostsResponse)
async def top_posts(
    sort: str = Query("engagement"),
    limit: int = Query(10, ge=1, le=50),
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    user: UserInfo = Depends(get_current_user),
):
    posts = await get_top_posts(db, days=days, limit=limit, sort=sort)
    return TopPostsResponse(posts=[TopPostOut(**p) for p in posts])
