"""
Analytics service — aggregates post metrics from DB.
"""
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case, and_

from content_manager_bot.database.models import Post


async def get_dashboard(db: AsyncSession, days: int = 7) -> dict:
    """Dashboard summary: totals, today's published, pending, type breakdown."""
    since = datetime.utcnow() - timedelta(days=days)
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    # Total posts
    total = (await db.execute(select(func.count(Post.id)))).scalar() or 0

    # Published today
    published_today = (await db.execute(
        select(func.count(Post.id)).where(
            and_(Post.status == "published", Post.published_at >= today_start)
        )
    )).scalar() or 0

    # Pending count
    pending_count = (await db.execute(
        select(func.count(Post.id)).where(Post.status == "pending")
    )).scalar() or 0

    # Average engagement (published posts within period)
    avg_eng = (await db.execute(
        select(func.avg(Post.engagement_rate)).where(
            and_(Post.status == "published", Post.published_at >= since, Post.engagement_rate.isnot(None))
        )
    )).scalar()

    # Type breakdown
    type_rows = (await db.execute(
        select(
            Post.post_type,
            func.count(Post.id).label("cnt"),
            func.avg(Post.engagement_rate).label("avg_eng"),
        ).where(Post.published_at >= since)
        .group_by(Post.post_type)
        .order_by(func.count(Post.id).desc())
    )).all()

    type_breakdown = [
        {"type": row.post_type, "count": row.cnt, "avg_engagement": round(row.avg_eng, 2) if row.avg_eng else None}
        for row in type_rows
    ]

    return {
        "total_posts": total,
        "published_today": published_today,
        "avg_engagement": round(avg_eng, 2) if avg_eng else None,
        "pending_count": pending_count,
        "type_breakdown": type_breakdown,
    }


async def get_engagement_timeline(db: AsyncSession, days: int = 30) -> list[dict]:
    """Daily engagement rate and posts count."""
    since = datetime.utcnow() - timedelta(days=days)

    rows = (await db.execute(
        select(
            func.date(Post.published_at).label("day"),
            func.avg(Post.engagement_rate).label("avg_eng"),
            func.count(Post.id).label("cnt"),
        ).where(
            and_(Post.status == "published", Post.published_at >= since)
        )
        .group_by(func.date(Post.published_at))
        .order_by(func.date(Post.published_at))
    )).all()

    return [
        {
            "date": str(row.day),
            "engagement_rate": round(row.avg_eng, 2) if row.avg_eng else None,
            "posts_count": row.cnt,
        }
        for row in rows
    ]


async def get_top_posts(db: AsyncSession, days: int = 30, limit: int = 10, sort: str = "engagement") -> list[dict]:
    """Top performing posts."""
    since = datetime.utcnow() - timedelta(days=days)

    query = select(Post).where(
        and_(Post.status == "published", Post.published_at >= since)
    )

    if sort == "engagement":
        query = query.order_by(Post.engagement_rate.desc().nullslast())
    elif sort == "views":
        query = query.order_by(Post.views_count.desc().nullslast())
    else:
        query = query.order_by(Post.reactions_count.desc().nullslast())

    query = query.limit(limit)
    result = await db.execute(query)
    posts = result.scalars().all()

    return [
        {
            "id": p.id,
            "post_type": p.post_type,
            "preview": p.content[:120] + "..." if len(p.content) > 120 else p.content,
            "views": p.views_count or 0,
            "reactions": p.reactions_count or 0,
            "engagement_rate": p.engagement_rate,
        }
        for p in posts
    ]
