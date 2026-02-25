"""
Authentication API

Handles Telegram Mini App authentication with real database
"""
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import jwt

from ..models.partner import Partner, PartnerStatus
from ..services.telegram_auth import TelegramAuthService
from ..config import settings
from ..database import get_db

router = APIRouter(prefix="/auth", tags=["Authentication"])


# Pydantic models
class AuthRequest(BaseModel):
    """Request body for authentication"""
    init_data: str


class PartnerInfo(BaseModel):
    """Partner information in auth response"""
    id: int
    telegram_id: int
    username: Optional[str]
    first_name: str
    last_name: Optional[str]
    status: str
    segment: str
    total_channels: int
    total_posts: int
    total_subscribers: int
    total_leads: int
    created_at: datetime


class AuthResponse(BaseModel):
    """Response for successful authentication"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    partner: PartnerInfo


async def get_current_partner(
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db),
) -> Partner:
    """
    Get current partner from JWT token

    Usage:
        @router.get("/me")
        async def get_me(partner: Partner = Depends(get_current_partner)):
            return partner
    """
    try:
        # Extract token from "Bearer <token>"
        if not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid authorization header")

        token = authorization.replace("Bearer ", "")

        # Decode JWT
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=["HS256"]
        )

        telegram_id = payload.get("sub")
        if not telegram_id:
            raise HTTPException(status_code=401, detail="Invalid token")

        # Get partner from DB
        result = await db.execute(
            select(Partner).where(Partner.telegram_id == int(telegram_id))
        )
        partner = result.scalar_one_or_none()

        if not partner:
            raise HTTPException(status_code=404, detail="Partner not found")

        # Update last activity
        partner.last_activity_at = datetime.utcnow()
        await db.commit()

        return partner

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def create_access_token(telegram_id: int, expires_delta: Optional[timedelta] = None) -> tuple[str, int]:
    """
    Create JWT access token

    Returns:
        tuple[token: str, expires_in: int]
    """
    if expires_delta is None:
        expires_delta = timedelta(days=7)

    expire = datetime.utcnow() + expires_delta
    expires_in = int(expires_delta.total_seconds())

    payload = {
        "sub": str(telegram_id),
        "exp": expire,
        "iat": datetime.utcnow(),
    }

    token = jwt.encode(payload, settings.secret_key, algorithm="HS256")
    return token, expires_in


@router.post("/telegram", response_model=AuthResponse)
async def authenticate_telegram(
    request: AuthRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticate user via Telegram Mini App initData

    This endpoint:
    1. Validates the initData from Telegram WebApp
    2. Creates or updates the partner record in database
    3. Returns a JWT token for subsequent API calls
    """
    # Validate initData
    auth_service = TelegramAuthService()
    init_data = auth_service.validate_init_data(request.init_data)

    if not init_data:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired initData"
        )

    # Check if data is fresh (not older than 24 hours)
    if not auth_service.is_data_fresh(init_data):
        raise HTTPException(
            status_code=401,
            detail="initData expired"
        )

    user = init_data.user

    # Check if partner exists in DB
    result = await db.execute(
        select(Partner).where(Partner.telegram_id == user.id)
    )
    partner = result.scalar_one_or_none()

    if partner:
        # Update existing partner
        partner.telegram_username = user.username
        partner.telegram_first_name = user.first_name
        partner.telegram_last_name = user.last_name
        partner.telegram_photo_url = user.photo_url
        partner.last_activity_at = datetime.utcnow()
    else:
        # Create new partner
        partner = Partner(
            telegram_id=user.id,
            telegram_username=user.username,
            telegram_first_name=user.first_name,
            telegram_last_name=user.last_name,
            telegram_photo_url=user.photo_url,
            status=PartnerStatus.PENDING,
            segment="zozh",
            total_channels=0,
            total_posts=0,
            total_subscribers=0,
            total_leads=0,
        )
        db.add(partner)

    await db.commit()
    await db.refresh(partner)

    # Create JWT token
    access_token, expires_in = create_access_token(user.id)

    return AuthResponse(
        access_token=access_token,
        expires_in=expires_in,
        partner=PartnerInfo(
            id=partner.id,
            telegram_id=partner.telegram_id,
            username=partner.telegram_username,
            first_name=partner.telegram_first_name or "Partner",
            last_name=partner.telegram_last_name,
            status=partner.status.value,
            segment=partner.segment,
            total_channels=partner.total_channels,
            total_posts=partner.total_posts,
            total_subscribers=partner.total_subscribers,
            total_leads=partner.total_leads,
            created_at=partner.created_at,
        )
    )


@router.get("/me", response_model=PartnerInfo)
async def get_current_user(
    partner: Partner = Depends(get_current_partner),
):
    """
    Get current authenticated partner info
    """
    return PartnerInfo(
        id=partner.id,
        telegram_id=partner.telegram_id,
        username=partner.telegram_username,
        first_name=partner.telegram_first_name or "Partner",
        last_name=partner.telegram_last_name,
        status=partner.status.value,
        segment=partner.segment,
        total_channels=partner.total_channels,
        total_posts=partner.total_posts,
        total_subscribers=partner.total_subscribers,
        total_leads=partner.total_leads,
        created_at=partner.created_at,
    )
