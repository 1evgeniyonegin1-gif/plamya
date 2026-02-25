"""
Traffic Engine service — queries TE tables for monitoring.
"""
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc

from traffic_engine.database.models import UserBotAccount, TrafficAction, TargetChannel


async def get_overview(db: AsyncSession, tenant_id: int = 1) -> dict:
    """Get all accounts + today's action stats + last comment."""
    # Accounts
    result = await db.execute(
        select(UserBotAccount).where(UserBotAccount.tenant_id == tenant_id)
        .order_by(UserBotAccount.id)
    )
    accounts = list(result.scalars().all())

    # Today's stats
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    base = and_(TrafficAction.tenant_id == tenant_id, TrafficAction.created_at >= today_start)

    comments_ok = (await db.execute(
        select(func.count()).where(and_(base, TrafficAction.action_type == "comment", TrafficAction.status == "success"))
    )).scalar() or 0

    comments_fail = (await db.execute(
        select(func.count()).where(and_(base, TrafficAction.action_type == "comment", TrafficAction.status != "success"))
    )).scalar() or 0

    stories = (await db.execute(
        select(func.count()).where(and_(base, TrafficAction.action_type.in_(["story_view", "story_react"])))
    )).scalar() or 0

    invites = (await db.execute(
        select(func.count()).where(and_(base, TrafficAction.action_type == "invite", TrafficAction.status == "success"))
    )).scalar() or 0

    replies = (await db.execute(
        select(func.count()).where(and_(base, TrafficAction.action_type == "comment", TrafficAction.got_reply == True))
    )).scalar() or 0

    # Last comment
    last_action = (await db.execute(
        select(TrafficAction)
        .where(and_(TrafficAction.tenant_id == tenant_id, TrafficAction.action_type == "comment", TrafficAction.status == "success"))
        .order_by(desc(TrafficAction.created_at))
        .limit(1)
    )).scalar_one_or_none()

    last_comment = None
    if last_action:
        # Get channel title
        channel_title = None
        if last_action.target_channel_id:
            ch = (await db.execute(
                select(TargetChannel.title).where(TargetChannel.channel_id == last_action.target_channel_id)
            )).scalar_one_or_none()
            channel_title = ch

        last_comment = {
            "text": (last_action.content or "")[:200],
            "channel": channel_title,
            "strategy": last_action.strategy_used,
            "time": last_action.created_at,
        }

    return {
        "accounts": accounts,
        "today_stats": {
            "comments_ok": comments_ok,
            "comments_fail": comments_fail,
            "stories": stories,
            "invites": invites,
            "replies": replies,
        },
        "last_comment": last_comment,
    }


async def get_errors(db: AsyncSession, hours: int = 24, tenant_id: int = 1) -> dict:
    """Get grouped errors from the last N hours."""
    since = datetime.utcnow() - timedelta(hours=hours)

    result = await db.execute(
        select(TrafficAction).where(
            and_(
                TrafficAction.tenant_id == tenant_id,
                TrafficAction.status != "success",
                TrafficAction.created_at >= since,
            )
        ).order_by(desc(TrafficAction.created_at))
    )
    actions = list(result.scalars().all())

    # Group by error pattern
    groups: dict[str, dict] = {}
    for a in actions:
        error = a.error_message or "Unknown error"
        # Categorize
        if "flood" in error.lower():
            cat = "FloodWait"
        elif "banned" in error.lower() or "forbidden" in error.lower():
            cat = "Banned/Forbidden"
        elif "timeout" in error.lower():
            cat = "Timeout"
        elif "not found" in error.lower() or "deleted" in error.lower():
            cat = "Not Found"
        else:
            cat = "Other"

        if cat not in groups:
            groups[cat] = {"category": cat, "count": 0, "last_at": None, "diagnosis": error[:200], "accounts": set(), "channels": set()}

        g = groups[cat]
        g["count"] += 1
        if not g["last_at"] or a.created_at > g["last_at"]:
            g["last_at"] = a.created_at
        # Try to get account phone
        g["accounts"].add(str(a.account_id))
        if a.target_channel_id:
            g["channels"].add(str(a.target_channel_id))

    result_groups = [
        {**g, "accounts": list(g["accounts"])[:5], "channels": list(g["channels"])[:5]}
        for g in groups.values()
    ]

    return {"total": len(actions), "groups": result_groups}
