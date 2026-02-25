"""
Traffic Engine Statistics API

Real analytics from traffic_actions, traffic_target_channels,
traffic_strategy_effectiveness tables via raw SQL.
"""
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from .auth import get_current_partner

router = APIRouter(prefix="/traffic", tags=["Traffic Analytics"])


# --- Pydantic models ---

class TrafficOverview(BaseModel):
    comments_today: int = 0
    comments_week: int = 0
    total_comments: int = 0
    replies_today: int = 0
    replies_week: int = 0
    reply_rate: float = 0.0
    stories_today: int = 0
    stories_week: int = 0
    accounts_active: int = 0
    accounts_total: int = 0


class ChannelStats(BaseModel):
    username: Optional[str] = None
    title: str = ""
    segment: Optional[str] = None
    is_active: bool = True
    comments_today: int = 0
    comments_total: int = 0
    replies: int = 0
    reply_rate: float = 0.0
    avg_relevance: Optional[float] = None
    posts_processed: int = 0


class StrategyStats(BaseModel):
    strategy: str
    segment: str = "all"
    attempts: int = 0
    successes: float = 0.0
    score: float = 0.5


class DailyTraffic(BaseModel):
    date: date
    comments: int = 0
    stories: int = 0
    replies: int = 0
    avg_relevance: Optional[float] = None


class RecentComment(BaseModel):
    content: Optional[str] = None
    strategy: Optional[str] = None
    got_reply: bool = False
    reply_count: int = 0
    relevance_score: Optional[float] = None
    post_topic: Optional[str] = None
    created_at: datetime


class ChannelDetail(BaseModel):
    username: Optional[str] = None
    title: str = ""
    segment: Optional[str] = None
    comments_today: int = 0
    comments_total: int = 0
    replies: int = 0
    reply_rate: float = 0.0
    avg_relevance: Optional[float] = None
    recent_comments: List[RecentComment] = []
    strategy_distribution: List[StrategyStats] = []


# --- Endpoints ---

@router.get("/overview", response_model=TrafficOverview)
async def get_traffic_overview(
    db: AsyncSession = Depends(get_db),
    partner=Depends(get_current_partner),
):
    """Overall Traffic Engine statistics"""
    now_utc = datetime.now(timezone.utc)
    today_start = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)

    # Comments & replies
    result = await db.execute(text("""
        SELECT
            COUNT(*) FILTER (WHERE action_type = 'comment') as total_comments,
            COUNT(*) FILTER (WHERE action_type = 'comment' AND created_at >= :today) as comments_today,
            COUNT(*) FILTER (WHERE action_type = 'comment' AND created_at >= :week) as comments_week,
            COUNT(*) FILTER (WHERE action_type = 'comment' AND got_reply = true) as total_replies,
            COUNT(*) FILTER (WHERE action_type = 'comment' AND got_reply = true AND created_at >= :today) as replies_today,
            COUNT(*) FILTER (WHERE action_type = 'comment' AND got_reply = true AND created_at >= :week) as replies_week,
            COUNT(*) FILTER (WHERE action_type = 'story_view') as total_stories,
            COUNT(*) FILTER (WHERE action_type = 'story_view' AND created_at >= :today) as stories_today,
            COUNT(*) FILTER (WHERE action_type = 'story_view' AND created_at >= :week) as stories_week
        FROM traffic_actions
        WHERE status = 'success'
    """), {"today": today_start, "week": week_start})
    row = result.fetchone()

    total_comments = row.total_comments if row else 0
    replies_total = row.total_replies if row else 0
    reply_rate = (replies_total / total_comments * 100) if total_comments > 0 else 0.0

    # Active accounts
    acc_result = await db.execute(text("""
        SELECT
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE status = 'active') as active
        FROM traffic_userbot_accounts
    """))
    acc_row = acc_result.fetchone()

    return TrafficOverview(
        comments_today=row.comments_today if row else 0,
        comments_week=row.comments_week if row else 0,
        total_comments=total_comments,
        replies_today=row.replies_today if row else 0,
        replies_week=row.replies_week if row else 0,
        reply_rate=round(reply_rate, 1),
        stories_today=row.stories_today if row else 0,
        stories_week=row.stories_week if row else 0,
        accounts_active=acc_row.active if acc_row else 0,
        accounts_total=acc_row.total if acc_row else 0,
    )


@router.get("/channels", response_model=List[ChannelStats])
async def get_traffic_channels(
    db: AsyncSession = Depends(get_db),
    partner=Depends(get_current_partner),
):
    """Per-channel analytics"""
    now_utc = datetime.now(timezone.utc)
    today_start = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)

    result = await db.execute(text("""
        SELECT
            tc.username,
            tc.title,
            tc.segment,
            tc.is_active,
            tc.posts_processed,
            tc.comments_posted,
            COUNT(ta.id) FILTER (
                WHERE ta.created_at >= :today
            ) as comments_today,
            COUNT(ta.id) as comments_joined,
            COUNT(ta.id) FILTER (WHERE ta.got_reply = true) as replies,
            AVG(ta.relevance_score) FILTER (
                WHERE ta.relevance_score IS NOT NULL
            ) as avg_relevance
        FROM traffic_target_channels tc
        LEFT JOIN traffic_actions ta
            ON ta.target_channel_id = tc.channel_id
            AND ta.action_type = 'comment'
            AND ta.status = 'success'
        GROUP BY tc.id
        ORDER BY tc.is_active DESC, comments_today DESC, tc.comments_posted DESC
    """), {"today": today_start})

    channels = []
    for row in result.fetchall():
        total = row.comments_posted or row.comments_joined or 0
        replies = row.replies or 0
        channels.append(ChannelStats(
            username=row.username,
            title=row.title,
            segment=row.segment,
            is_active=row.is_active,
            comments_today=row.comments_today or 0,
            comments_total=total,
            replies=replies,
            reply_rate=round(replies / total * 100, 1) if total > 0 else 0.0,
            avg_relevance=round(row.avg_relevance, 2) if row.avg_relevance else None,
            posts_processed=row.posts_processed or 0,
        ))

    return channels


@router.get("/strategies", response_model=List[StrategyStats])
async def get_traffic_strategies(
    db: AsyncSession = Depends(get_db),
    partner=Depends(get_current_partner),
):
    """MAB strategy effectiveness"""
    result = await db.execute(text("""
        SELECT
            comment_strategy,
            segment,
            SUM(attempts) as attempts,
            SUM(successes) as successes,
            AVG(score) as score
        FROM traffic_strategy_effectiveness
        GROUP BY comment_strategy, segment
        ORDER BY segment, score DESC
    """))

    strategies = []
    for row in result.fetchall():
        strategies.append(StrategyStats(
            strategy=row.comment_strategy,
            segment=row.segment or "all",
            attempts=row.attempts or 0,
            successes=row.successes or 0.0,
            score=round(row.score, 3) if row.score else 0.5,
        ))

    return strategies


@router.get("/daily", response_model=List[DailyTraffic])
async def get_traffic_daily(
    days: int = Query(default=7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    partner=Depends(get_current_partner),
):
    """Daily traffic trends"""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    result = await db.execute(text("""
        SELECT
            DATE(created_at) as day,
            COUNT(*) FILTER (WHERE action_type = 'comment') as comments,
            COUNT(*) FILTER (WHERE action_type = 'story_view') as stories,
            COUNT(*) FILTER (WHERE got_reply = true) as replies,
            AVG(relevance_score) FILTER (
                WHERE relevance_score IS NOT NULL
            ) as avg_relevance
        FROM traffic_actions
        WHERE status = 'success' AND created_at >= :cutoff
        GROUP BY DATE(created_at)
        ORDER BY day
    """), {"cutoff": cutoff})

    daily = []
    for row in result.fetchall():
        daily.append(DailyTraffic(
            date=row.day,
            comments=row.comments or 0,
            stories=row.stories or 0,
            replies=row.replies or 0,
            avg_relevance=round(row.avg_relevance, 2) if row.avg_relevance else None,
        ))

    return daily


@router.get("/channel/{username}", response_model=ChannelDetail)
async def get_channel_detail(
    username: str,
    db: AsyncSession = Depends(get_db),
    partner=Depends(get_current_partner),
):
    """Detailed analytics for a single channel"""
    now_utc = datetime.now(timezone.utc)
    today_start = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)

    # Channel info
    ch_result = await db.execute(text("""
        SELECT id, channel_id, username, title, segment, is_active,
               posts_processed, comments_posted
        FROM traffic_target_channels
        WHERE username = :username
        LIMIT 1
    """), {"username": username})
    ch_row = ch_result.fetchone()

    if not ch_row:
        raise HTTPException(status_code=404, detail="Channel not found")

    channel_id = ch_row.channel_id

    # Comments stats
    stats_result = await db.execute(text("""
        SELECT
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE created_at >= :today) as today,
            COUNT(*) FILTER (WHERE got_reply = true) as replies,
            AVG(relevance_score) FILTER (
                WHERE relevance_score IS NOT NULL
            ) as avg_relevance
        FROM traffic_actions
        WHERE target_channel_id = :channel_id
          AND action_type = 'comment'
          AND status = 'success'
    """), {"channel_id": channel_id, "today": today_start})
    stats_row = stats_result.fetchone()

    total = stats_row.total if stats_row else 0
    replies = stats_row.replies if stats_row else 0

    # Recent comments (last 10)
    comments_result = await db.execute(text("""
        SELECT content, strategy_used, got_reply, reply_count,
               relevance_score, post_topic, created_at
        FROM traffic_actions
        WHERE target_channel_id = :channel_id
          AND action_type = 'comment'
          AND status = 'success'
        ORDER BY created_at DESC
        LIMIT 10
    """), {"channel_id": channel_id})

    recent_comments = []
    for row in comments_result.fetchall():
        recent_comments.append(RecentComment(
            content=row.content[:200] if row.content else None,
            strategy=row.strategy_used,
            got_reply=row.got_reply or False,
            reply_count=row.reply_count or 0,
            relevance_score=round(row.relevance_score, 2) if row.relevance_score else None,
            post_topic=row.post_topic,
            created_at=row.created_at,
        ))

    # Strategy distribution for this channel
    strat_result = await db.execute(text("""
        SELECT
            strategy_used as strategy,
            COUNT(*) as attempts,
            COUNT(*) FILTER (WHERE got_reply = true) as successes
        FROM traffic_actions
        WHERE target_channel_id = :channel_id
          AND action_type = 'comment'
          AND status = 'success'
          AND strategy_used IS NOT NULL
        GROUP BY strategy_used
        ORDER BY attempts DESC
    """), {"channel_id": channel_id})

    strategy_distribution = []
    for row in strat_result.fetchall():
        att = row.attempts or 1
        succ = row.successes or 0
        strategy_distribution.append(StrategyStats(
            strategy=row.strategy,
            attempts=att,
            successes=float(succ),
            score=round(succ / att, 3) if att > 0 else 0.0,
        ))

    return ChannelDetail(
        username=ch_row.username,
        title=ch_row.title,
        segment=ch_row.segment,
        comments_today=stats_row.today if stats_row else 0,
        comments_total=total,
        replies=replies,
        reply_rate=round(replies / total * 100, 1) if total > 0 else 0.0,
        avg_relevance=round(stats_row.avg_relevance, 2) if stats_row and stats_row.avg_relevance else None,
        recent_comments=recent_comments,
        strategy_distribution=strategy_distribution,
    )
