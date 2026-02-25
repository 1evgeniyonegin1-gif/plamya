"""
AI Director API — plans, reviews, insights, competitors.
Reuses director modules from content_manager_bot.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..api.auth import get_current_user
from ..schemas import (
    PlanResponse, PlanSlot, ReviewResponse,
    InsightsResponse, InsightItem, CompetitorsResponse, UserInfo,
)

router = APIRouter(prefix="/director", tags=["AI Director"])


@router.get("/plan/{segment}", response_model=PlanResponse)
async def get_plan(
    segment: str,
    db: AsyncSession = Depends(get_db),
    user: UserInfo = Depends(get_current_user),
):
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin only")

    from content_manager_bot.director import get_editorial_planner
    planner = get_editorial_planner()
    plan = await planner.get_active_plan(segment)

    if not plan:
        return PlanResponse(slots=[], used=0, total=0)

    slots = []
    for item in (plan.get("slots") or []):
        slots.append(PlanSlot(
            day=str(item.get("day", "")),
            post_type=item.get("post_type", ""),
            topic=item.get("topic_hint") or item.get("topic"),
            status=item.get("status", "planned"),
        ))

    return PlanResponse(
        plan_id=plan.get("plan_id"),
        week_start=plan.get("week_start"),
        slots=slots,
        used=plan.get("used", 0),
        total=plan.get("total", 0),
    )


@router.post("/plan/{segment}/generate", response_model=PlanResponse)
async def generate_plan(
    segment: str,
    db: AsyncSession = Depends(get_db),
    user: UserInfo = Depends(get_current_user),
):
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin only")

    from content_manager_bot.director import get_editorial_planner
    planner = get_editorial_planner()
    result = await planner.generate_weekly_plan(segment)

    if not result:
        raise HTTPException(status_code=500, detail="Не удалось сгенерировать план")

    # Re-fetch the active plan to get full data
    plan = await planner.get_active_plan(segment)
    if not plan:
        raise HTTPException(status_code=500, detail="План создан, но не найден")

    slots = []
    for item in (plan.get("slots") or []):
        slots.append(PlanSlot(
            day=str(item.get("day", "")),
            post_type=item.get("post_type", ""),
            topic=item.get("topic_hint") or item.get("topic"),
            status=item.get("status", "planned"),
        ))

    return PlanResponse(
        plan_id=plan.get("plan_id"),
        week_start=plan.get("week_start"),
        slots=slots,
        used=plan.get("used", 0),
        total=plan.get("total", 0),
    )


@router.get("/review/{segment}", response_model=ReviewResponse)
async def get_review(
    segment: str,
    db: AsyncSession = Depends(get_db),
    user: UserInfo = Depends(get_current_user),
):
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin only")

    from content_manager_bot.director import get_self_reviewer
    reviewer = get_self_reviewer()
    review_data = await reviewer.get_last_review(segment)

    if not review_data:
        # Try generating a new review
        review_data = await reviewer.run_review(segment)

    if not review_data:
        return ReviewResponse(
            posts_reviewed=0,
            strengths=[], weaknesses=[], recommendations=[],
            topics=[], avoid=[],
        )

    review = review_data.get("review", {})
    created_at_str = review_data.get("created_at")
    created_at = None
    if created_at_str:
        try:
            from datetime import datetime
            created_at = datetime.fromisoformat(created_at_str)
        except (ValueError, TypeError):
            pass

    return ReviewResponse(
        posts_reviewed=review_data.get("posts_reviewed", 0),
        created_at=created_at,
        strengths=review.get("strengths", []),
        weaknesses=review.get("weaknesses", []),
        recommendations=review.get("recommendations", []),
        topics=review.get("topic_suggestions", review.get("topics", [])),
        avoid=review.get("avoid", []),
    )


@router.get("/insights/{segment}", response_model=InsightsResponse)
async def get_insights(
    segment: str,
    db: AsyncSession = Depends(get_db),
    user: UserInfo = Depends(get_current_user),
):
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin only")

    from content_manager_bot.director import get_performance_analyzer
    analyzer = get_performance_analyzer()

    # get_insights returns a formatted string, not dict
    # We need to query DB directly for structured data
    from sqlalchemy import select, func, and_
    from datetime import datetime, timedelta
    from content_manager_bot.database.models import Post

    cutoff = datetime.utcnow() - timedelta(days=30)
    result = await db.execute(
        select(
            Post.post_type,
            func.avg(Post.engagement_rate),
            func.count(Post.id),
        ).where(
            and_(
                Post.status == "published",
                Post.published_at >= cutoff,
                Post.engagement_rate.isnot(None),
            )
        ).group_by(Post.post_type)
    )
    rows = result.all()

    type_perf = []
    best_type = None
    best_eng = 0.0

    for post_type, avg_eng, count in rows:
        avg_eng = float(avg_eng or 0)
        type_perf.append(InsightItem(
            type=post_type,
            avg_engagement=round(avg_eng, 2),
            count=count,
        ))
        if avg_eng > best_eng:
            best_eng = avg_eng
            best_type = post_type

    # Best hours
    hour_result = await db.execute(
        select(
            func.extract('hour', Post.published_at).label('hour'),
            func.avg(Post.engagement_rate),
        ).where(
            and_(
                Post.status == "published",
                Post.published_at >= cutoff,
                Post.engagement_rate.isnot(None),
            )
        ).group_by('hour').order_by(func.avg(Post.engagement_rate).desc()).limit(5)
    )
    best_hours = [int(r[0]) for r in hour_result.all() if r[0] is not None]

    return InsightsResponse(
        type_performance=type_perf,
        best_hours=best_hours,
        recommended_type=best_type,
    )


@router.get("/competitors/{segment}", response_model=CompetitorsResponse)
async def get_competitors(
    segment: str,
    db: AsyncSession = Depends(get_db),
    user: UserInfo = Depends(get_current_user),
):
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin only")

    from content_manager_bot.director import get_competitor_analyzer, get_trend_detector
    competitor_analyzer = get_competitor_analyzer()
    trend_detector = get_trend_detector()

    comp_data = await competitor_analyzer.analyze(segment)
    trend_context = await trend_detector.get_trend_context(segment)

    if not comp_data:
        return CompetitorsResponse(
            trending_topics=[], winning_formats=[], hooks=[],
            trend_context=trend_context,
        )

    return CompetitorsResponse(
        trending_topics=comp_data.get("trending_topics", []),
        winning_formats=comp_data.get("winning_formats", []),
        hooks=comp_data.get("hooks_that_work", comp_data.get("hooks", [])),
        our_angle=comp_data.get("our_angle"),
        trend_context=trend_context,
    )
