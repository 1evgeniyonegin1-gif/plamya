"""
Channels API

Manages partner's Telegram channels with real database
"""
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from enum import Enum
import random

from ..models.partner import Partner, PartnerCredentials, PartnerChannel, ChannelStatus as DBChannelStatus
from ..database import get_db
from .auth import get_current_partner

router = APIRouter(prefix="/channels", tags=["Channels"])


# Pydantic models
class ChannelStatus(str, Enum):
    CREATING = "creating"
    WARMING = "warming"
    ACTIVE = "active"
    PAUSED = "paused"
    BANNED = "banned"


class Segment(str, Enum):
    ZOZH = "zozh"
    MAMA = "mama"
    BUSINESS = "business"


# Personas per segment
PERSONAS = {
    "zozh": ["Марина", "Анна", "Елена", "Наталья", "Ольга"],
    "mama": ["Катя", "Юля", "Света", "Настя", "Маша"],
    "business": ["Виктор", "Александр", "Дмитрий", "Андрей", "Михаил"],
}


class ChannelCreate(BaseModel):
    """Request to create a new channel"""
    credentials_id: int = Field(..., description="ID of credentials to use")
    title: Optional[str] = Field(None, description="Channel title (auto-generated if not provided)")
    segment: Segment = Field(Segment.ZOZH, description="Content segment")
    referral_link: Optional[str] = Field(None, description="Your NL referral link")
    posts_per_day: int = Field(2, ge=1, le=5, description="Posts per day")


class ChannelUpdate(BaseModel):
    """Request to update channel settings"""
    title: Optional[str] = None
    posting_enabled: Optional[bool] = None
    posts_per_day: Optional[int] = Field(None, ge=1, le=5)
    posting_times: Optional[List[str]] = Field(None, description="Times in HH:MM format")
    referral_link: Optional[str] = None


class ChannelResponse(BaseModel):
    """Response for channel info"""
    id: int
    channel_id: int
    channel_username: Optional[str]
    channel_title: str
    segment: str
    persona_name: str
    status: ChannelStatus
    posting_enabled: bool
    posts_per_day: int
    posting_times: List[str]
    referral_link: Optional[str]
    curator_deeplink: str
    subscribers_count: int
    posts_count: int
    avg_views: int
    total_clicks: int
    created_at: datetime
    last_post_at: Optional[datetime]


class ChannelStats(BaseModel):
    """Detailed channel statistics"""
    channel_id: int
    period: str  # "day", "week", "month"
    subscribers_gained: int
    subscribers_lost: int
    posts_published: int
    total_views: int
    avg_views_per_post: int
    total_reactions: int
    total_clicks: int
    click_through_rate: float


def _channel_to_response(channel: PartnerChannel, partner_id: int) -> ChannelResponse:
    """Convert DB model to response"""
    raw_times = channel.posting_times
    # Handle various JSONB formats from PostgreSQL
    if raw_times is None:
        posting_times: list[str] = ["10:00", "18:00"]
    elif isinstance(raw_times, dict):
        posting_times = list(raw_times.values()) if raw_times else ["10:00", "18:00"]
    elif isinstance(raw_times, list):
        posting_times = raw_times
    else:
        posting_times = ["10:00", "18:00"]

    return ChannelResponse(
        id=channel.id,
        channel_id=channel.channel_id,
        channel_username=channel.channel_username,
        channel_title=channel.channel_title,
        segment=channel.segment,
        persona_name=channel.persona_name,
        status=ChannelStatus(channel.status.value),
        posting_enabled=channel.posting_enabled,
        posts_per_day=channel.posts_per_day,
        posting_times=posting_times,
        referral_link=channel.referral_link,
        curator_deeplink=channel.curator_deeplink or f"https://t.me/nl_curator_bot?start=partner_{partner_id}",
        subscribers_count=channel.subscribers_count,
        posts_count=channel.posts_count,
        avg_views=channel.avg_views,
        total_clicks=channel.total_clicks,
        created_at=channel.created_at,
        last_post_at=channel.last_post_at,
    )


@router.post("/", response_model=ChannelResponse, status_code=201)
async def create_channel(
    channel: ChannelCreate,
    db: AsyncSession = Depends(get_db),
    partner: Partner = Depends(get_current_partner),
):
    """
    Create a new channel

    This will:
    1. Create a Telegram channel using the specified credentials
    2. Generate a persona based on the segment
    3. Configure automatic posting
    4. Set up referral link tracking
    """
    # Check if credentials belong to this partner
    result = await db.execute(
        select(PartnerCredentials).where(
            PartnerCredentials.id == channel.credentials_id,
            PartnerCredentials.partner_id == partner.id
        )
    )
    cred = result.scalar_one_or_none()

    if not cred:
        raise HTTPException(status_code=404, detail="Credentials not found")

    if cred.is_banned:
        raise HTTPException(status_code=400, detail="Credentials are banned")

    # Generate persona for segment
    persona_name = random.choice(PERSONAS.get(channel.segment.value, PERSONAS["zozh"]))

    # Generate default title if not provided
    title = channel.title or f"Здоровье и красота | {persona_name}"

    # TODO: Create real Telegram channel with Telethon
    # For now, generate a placeholder channel_id
    channel_id = random.randint(1000000000, 9999999999)

    # Create channel record
    new_channel = PartnerChannel(
        partner_id=partner.id,
        credentials_id=cred.id,
        channel_id=channel_id,
        channel_username=None,  # Will be set after actual creation
        channel_title=title,
        segment=channel.segment.value,
        persona_name=persona_name,
        status=DBChannelStatus.CREATING,
        posting_enabled=False,
        posts_per_day=channel.posts_per_day,
        posting_times=["10:00", "18:00"],
        referral_link=channel.referral_link,
        curator_deeplink=f"https://t.me/nl_curator_bot?start=partner_{partner.id}",
        subscribers_count=0,
        posts_count=0,
        avg_views=0,
        total_clicks=0,
    )

    db.add(new_channel)

    # Update partner stats
    partner.total_channels += 1

    await db.commit()
    await db.refresh(new_channel)

    # TODO: Start background task to create actual Telegram channel

    return _channel_to_response(new_channel, partner.id)


@router.get("/", response_model=List[ChannelResponse])
async def list_channels(
    db: AsyncSession = Depends(get_db),
    partner: Partner = Depends(get_current_partner),
):
    """
    List all channels for the partner
    """
    result = await db.execute(
        select(PartnerChannel).where(PartnerChannel.partner_id == partner.id)
    )
    channels = result.scalars().all()

    return [_channel_to_response(ch, partner.id) for ch in channels]


@router.get("/{channel_id}", response_model=ChannelResponse)
async def get_channel(
    channel_id: int,
    db: AsyncSession = Depends(get_db),
    partner: Partner = Depends(get_current_partner),
):
    """
    Get channel details
    """
    result = await db.execute(
        select(PartnerChannel).where(
            PartnerChannel.id == channel_id,
            PartnerChannel.partner_id == partner.id
        )
    )
    channel = result.scalar_one_or_none()

    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    return _channel_to_response(channel, partner.id)


@router.patch("/{channel_id}", response_model=ChannelResponse)
async def update_channel(
    channel_id: int,
    update: ChannelUpdate,
    db: AsyncSession = Depends(get_db),
    partner: Partner = Depends(get_current_partner),
):
    """
    Update channel settings
    """
    result = await db.execute(
        select(PartnerChannel).where(
            PartnerChannel.id == channel_id,
            PartnerChannel.partner_id == partner.id
        )
    )
    channel = result.scalar_one_or_none()

    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    # Update fields
    if update.title is not None:
        channel.channel_title = update.title
    if update.posting_enabled is not None:
        channel.posting_enabled = update.posting_enabled
    if update.posts_per_day is not None:
        channel.posts_per_day = update.posts_per_day
    if update.posting_times is not None:
        channel.posting_times = update.posting_times  # type: ignore[assignment]
    if update.referral_link is not None:
        channel.referral_link = update.referral_link

    await db.commit()
    await db.refresh(channel)

    return _channel_to_response(channel, partner.id)


@router.delete("/{channel_id}")
async def delete_channel(
    channel_id: int,
    db: AsyncSession = Depends(get_db),
    partner: Partner = Depends(get_current_partner),
):
    """
    Delete a channel

    Note: This will stop posting but won't delete the Telegram channel itself.
    """
    result = await db.execute(
        select(PartnerChannel).where(
            PartnerChannel.id == channel_id,
            PartnerChannel.partner_id == partner.id
        )
    )
    channel = result.scalar_one_or_none()

    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    await db.delete(channel)

    # Update partner stats
    partner.total_channels = max(0, partner.total_channels - 1)

    await db.commit()

    return {"status": "deleted", "id": channel_id}


@router.post("/{channel_id}/pause")
async def pause_channel(
    channel_id: int,
    db: AsyncSession = Depends(get_db),
    partner: Partner = Depends(get_current_partner),
):
    """
    Pause posting to channel
    """
    result = await db.execute(
        select(PartnerChannel).where(
            PartnerChannel.id == channel_id,
            PartnerChannel.partner_id == partner.id
        )
    )
    channel = result.scalar_one_or_none()

    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    channel.posting_enabled = False
    channel.status = DBChannelStatus.PAUSED
    await db.commit()

    return {"status": "paused", "id": channel_id}


@router.post("/{channel_id}/resume")
async def resume_channel(
    channel_id: int,
    db: AsyncSession = Depends(get_db),
    partner: Partner = Depends(get_current_partner),
):
    """
    Resume posting to channel
    """
    result = await db.execute(
        select(PartnerChannel).where(
            PartnerChannel.id == channel_id,
            PartnerChannel.partner_id == partner.id
        )
    )
    channel = result.scalar_one_or_none()

    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    channel.posting_enabled = True
    channel.status = DBChannelStatus.ACTIVE
    await db.commit()

    return {"status": "resumed", "id": channel_id}


@router.get("/{channel_id}/stats", response_model=ChannelStats)
async def get_channel_stats(
    channel_id: int,
    period: str = "week",
    db: AsyncSession = Depends(get_db),
    partner: Partner = Depends(get_current_partner),
):
    """
    Get channel statistics for a period
    """
    result = await db.execute(
        select(PartnerChannel).where(
            PartnerChannel.id == channel_id,
            PartnerChannel.partner_id == partner.id
        )
    )
    channel = result.scalar_one_or_none()

    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    # TODO: Calculate real stats from traffic_sources table
    # For now, return based on channel metrics
    multiplier = {"day": 1, "week": 7, "month": 30}.get(period, 7)

    return ChannelStats(
        channel_id=channel_id,
        period=period,
        subscribers_gained=channel.subscribers_count // 4 * multiplier // 7,
        subscribers_lost=channel.subscribers_count // 20 * multiplier // 7,
        posts_published=channel.posts_per_day * multiplier,
        total_views=channel.avg_views * channel.posts_per_day * multiplier,
        avg_views_per_post=channel.avg_views,
        total_reactions=channel.avg_views // 10 * multiplier,
        total_clicks=channel.total_clicks * multiplier // 30,
        click_through_rate=round(channel.total_clicks / max(channel.avg_views, 1) * 100, 2),
    )


@router.post("/{channel_id}/generate-post")
async def generate_post(
    channel_id: int,
    db: AsyncSession = Depends(get_db),
    partner: Partner = Depends(get_current_partner),
):
    """
    Manually generate a new post for the channel

    Returns the generated post for preview before publishing.
    """
    result = await db.execute(
        select(PartnerChannel).where(
            PartnerChannel.id == channel_id,
            PartnerChannel.partner_id == partner.id
        )
    )
    channel = result.scalar_one_or_none()

    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    # TODO: Call ContentGenerator
    # from content_manager_bot.ai.content_generator import ContentGenerator
    # generator = ContentGenerator()
    # post = await generator.generate_post(channel.segment)

    return {
        "id": 1,
        "content": f"Сгенерированный пост для канала '{channel.channel_title}'...\n\n{channel.referral_link or ''}",
        "status": "draft",
        "segment": channel.segment,
        "persona": channel.persona_name,
    }


@router.post("/{channel_id}/publish-now")
async def publish_now(
    channel_id: int,
    post_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    partner: Partner = Depends(get_current_partner),
):
    """
    Publish a post immediately

    If post_id is provided, publishes that specific post.
    Otherwise, generates and publishes a new post.
    """
    result = await db.execute(
        select(PartnerChannel).where(
            PartnerChannel.id == channel_id,
            PartnerChannel.partner_id == partner.id
        )
    )
    channel = result.scalar_one_or_none()

    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    if channel.status == DBChannelStatus.BANNED:
        raise HTTPException(status_code=400, detail="Channel is banned")

    # TODO: Actually publish via Telethon

    # Update stats
    channel.posts_count += 1
    channel.last_post_at = datetime.utcnow()
    partner.total_posts += 1

    await db.commit()

    return {
        "status": "published",
        "channel_id": channel_id,
        "message_id": random.randint(1, 99999),
    }
