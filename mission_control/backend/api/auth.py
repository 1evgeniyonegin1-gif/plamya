"""
Authentication API — Telegram Mini App auth with JWT.
Admin-only access (checked against settings.admin_ids).
"""
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, HTTPException, Header
import jwt

from ..auth.telegram_auth import TelegramAuthService
from ..config import settings
from ..schemas import AuthRequest, AuthResponse, UserInfo

router = APIRouter(prefix="/auth", tags=["Auth"])


def create_access_token(
    telegram_id: int,
    first_name: str = "User",
    username: Optional[str] = None,
    expires_delta: Optional[timedelta] = None,
) -> tuple[str, int]:
    """Create a JWT access token embedding user info for stateless auth."""
    if expires_delta is None:
        expires_delta = timedelta(days=7)
    expire = datetime.utcnow() + expires_delta
    expires_in = int(expires_delta.total_seconds())
    payload = {
        "sub": str(telegram_id),
        "first_name": first_name,
        "username": username,
        "exp": expire,
        "iat": datetime.utcnow(),
    }
    token = jwt.encode(payload, settings.secret_key, algorithm="HS256")
    return token, expires_in


async def get_current_user(authorization: str = Header(...)) -> UserInfo:
    """Extract and validate JWT token. Returns UserInfo."""
    try:
        if not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid authorization header")
        token = authorization.replace("Bearer ", "")
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        telegram_id = payload.get("sub")
        if not telegram_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        tid = int(telegram_id)
        return UserInfo(
            telegram_id=tid,
            first_name=payload.get("first_name", "User"),
            username=payload.get("username"),
            is_admin=tid in settings.admin_ids,
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


@router.post("/telegram", response_model=AuthResponse)
async def authenticate_telegram(request: AuthRequest):
    """Validate Telegram initData, check admin access, issue JWT."""
    auth_service = TelegramAuthService()
    init_data = auth_service.validate_init_data(request.init_data)

    if not init_data:
        raise HTTPException(status_code=401, detail="Invalid initData")

    if not auth_service.is_data_fresh(init_data):
        raise HTTPException(status_code=401, detail="initData expired")

    user = init_data.user

    # Admin-only check
    if user.id not in settings.admin_ids:
        raise HTTPException(status_code=403, detail="Access denied. Admin only.")

    is_admin = True  # Already checked above

    token, expires_in = create_access_token(
        telegram_id=user.id,
        first_name=user.first_name,
        username=user.username,
    )

    return AuthResponse(
        access_token=token,
        expires_in=expires_in,
        user=UserInfo(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name,
            is_admin=is_admin,
        ),
    )


@router.get("/me", response_model=UserInfo)
async def get_me(authorization: str = Header(...)):
    """Get current authenticated user info."""
    return await get_current_user(authorization)
