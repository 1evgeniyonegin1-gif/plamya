"""
Authentication API

Handles Telegram Mini App authentication
"""
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import jwt

from ..models.user import CuratorUser
from ..services.telegram_auth import TelegramAuthService
from ..config import settings
from ..database import get_db

router = APIRouter(prefix="/auth", tags=["Authentication"])


# Pydantic models
class AuthRequest(BaseModel):
    """Request body for authentication"""
    init_data: str


class UserInfo(BaseModel):
    """User information in auth response"""
    id: int
    telegram_id: int
    username: Optional[str]
    first_name: str
    last_name: Optional[str]
    is_partner: bool
    products_viewed: int
    business_section_viewed: bool
    visits_count: int
    created_at: datetime


class AuthResponse(BaseModel):
    """Response for successful authentication"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserInfo


async def get_current_user(
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db),
) -> CuratorUser:
    """
    Get current user from JWT token

    Usage:
        @router.get("/me")
        async def get_me(user: CuratorUser = Depends(get_current_user)):
            return user
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

        # Get user from DB
        result = await db.execute(
            select(CuratorUser).where(CuratorUser.telegram_id == int(telegram_id))
        )
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Update last activity
        user.last_visit_at = datetime.utcnow()
        await db.commit()

        return user

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
    2. Creates or updates the user record in database
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

    # Check if user exists in DB
    result = await db.execute(
        select(CuratorUser).where(CuratorUser.telegram_id == user.id)
    )
    db_user = result.scalar_one_or_none()

    if db_user:
        # Update existing user
        db_user.telegram_username = user.username
        db_user.telegram_first_name = user.first_name
        db_user.telegram_last_name = user.last_name
        db_user.telegram_photo_url = user.photo_url
        db_user.last_visit_at = datetime.utcnow()
        db_user.visits_count += 1
    else:
        # Create new user
        db_user = CuratorUser(
            telegram_id=user.id,
            telegram_username=user.username,
            telegram_first_name=user.first_name,
            telegram_last_name=user.last_name,
            telegram_photo_url=user.photo_url,
            is_partner=False,
            products_viewed=0,
            business_section_viewed=False,
            last_visit_at=datetime.utcnow(),
            visits_count=1,
        )
        db.add(db_user)

    await db.commit()
    await db.refresh(db_user)

    # Create JWT token
    access_token, expires_in = create_access_token(user.id)

    return AuthResponse(
        access_token=access_token,
        expires_in=expires_in,
        user=UserInfo(
            id=db_user.id,
            telegram_id=db_user.telegram_id,
            username=db_user.telegram_username,
            first_name=db_user.telegram_first_name or "User",
            last_name=db_user.telegram_last_name,
            is_partner=db_user.is_partner,
            products_viewed=db_user.products_viewed,
            business_section_viewed=db_user.business_section_viewed,
            visits_count=db_user.visits_count,
            created_at=db_user.created_at,
        )
    )


@router.get("/me", response_model=UserInfo)
async def get_current_user_info(
    user: CuratorUser = Depends(get_current_user),
):
    """
    Get current authenticated user info
    """
    return UserInfo(
        id=user.id,
        telegram_id=user.telegram_id,
        username=user.telegram_username,
        first_name=user.telegram_first_name or "User",
        last_name=user.telegram_last_name,
        is_partner=user.is_partner,
        products_viewed=user.products_viewed,
        business_section_viewed=user.business_section_viewed,
        visits_count=user.visits_count,
        created_at=user.created_at,
    )
