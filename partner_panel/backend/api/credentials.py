"""
Credentials API

Handles partner credentials (session strings, proxies) with real database
"""
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from enum import Enum

from ..models.partner import Partner, PartnerCredentials
from ..database import get_db
from .auth import get_current_partner

router = APIRouter(prefix="/credentials", tags=["Credentials"])


# Pydantic models
class ProxyType(str, Enum):
    SOCKS5 = "socks5"
    HTTP = "http"


class CredentialsCreate(BaseModel):
    """Request to add new credentials"""
    phone: str = Field(..., description="Phone number with country code", examples=["+79001234567"])
    session_string: str = Field(..., description="Telethon session string")
    api_id: Optional[int] = Field(None, description="Telegram API ID (optional)")
    api_hash: Optional[str] = Field(None, description="Telegram API Hash (optional)")
    proxy_type: Optional[ProxyType] = Field(None, description="Proxy type")
    proxy_host: Optional[str] = Field(None, description="Proxy host")
    proxy_port: Optional[int] = Field(None, description="Proxy port")
    proxy_username: Optional[str] = Field(None, description="Proxy username")
    proxy_password: Optional[str] = Field(None, description="Proxy password")


class CredentialsResponse(BaseModel):
    """Response for credentials"""
    id: int
    phone: str
    is_active: bool
    is_banned: bool
    warmup_day: int
    warmup_completed: bool
    created_at: datetime
    last_used_at: Optional[datetime]


class CredentialsValidateRequest(BaseModel):
    """Request to validate credentials"""
    session_string: str


class CredentialsValidateResponse(BaseModel):
    """Response for credentials validation"""
    valid: bool
    error: Optional[str] = None
    telegram_id: Optional[int] = None
    username: Optional[str] = None
    first_name: Optional[str] = None


class SetupStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class SetupProgress(BaseModel):
    """Progress of credentials setup"""
    status: SetupStatus
    step: str
    progress: int  # 0-100
    message: str
    error: Optional[str] = None


@router.post("/", response_model=CredentialsResponse, status_code=201)
async def add_credentials(
    credentials: CredentialsCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    partner: Partner = Depends(get_current_partner),
):
    """
    Add new credentials for the partner

    This will:
    1. Validate the session string
    2. Check proxy if provided
    3. Store credentials in database
    4. Start background setup process
    """
    # Validate session string format
    if len(credentials.session_string) < 100:
        raise HTTPException(
            status_code=400,
            detail="Invalid session string format"
        )

    # Check if phone already exists
    result = await db.execute(
        select(PartnerCredentials).where(PartnerCredentials.phone == credentials.phone)
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Phone number already registered"
        )

    # Create credentials record
    cred = PartnerCredentials(
        partner_id=partner.id,
        phone=credentials.phone,
        session_string=credentials.session_string,  # TODO: Encrypt this
        api_id=credentials.api_id,
        api_hash=credentials.api_hash,
        proxy_type=credentials.proxy_type.value if credentials.proxy_type else None,
        proxy_host=credentials.proxy_host,
        proxy_port=credentials.proxy_port,
        proxy_username=credentials.proxy_username,
        proxy_password=credentials.proxy_password,
        is_active=True,
        is_banned=False,
        warmup_day=0,
        warmup_completed=False,
    )

    db.add(cred)
    await db.commit()
    await db.refresh(cred)

    # TODO: Start background setup process
    # background_tasks.add_task(run_setup, cred.id)

    return CredentialsResponse(
        id=cred.id,
        phone=cred.phone,
        is_active=cred.is_active,
        is_banned=cred.is_banned,
        warmup_day=cred.warmup_day,
        warmup_completed=cred.warmup_completed,
        created_at=cred.created_at,
        last_used_at=cred.last_used_at,
    )


@router.get("/", response_model=List[CredentialsResponse])
async def list_credentials(
    db: AsyncSession = Depends(get_db),
    partner: Partner = Depends(get_current_partner),
):
    """
    List all credentials for the partner
    """
    result = await db.execute(
        select(PartnerCredentials).where(PartnerCredentials.partner_id == partner.id)
    )
    credentials = result.scalars().all()

    return [
        CredentialsResponse(
            id=cred.id,
            phone=cred.phone,
            is_active=cred.is_active,
            is_banned=cred.is_banned,
            warmup_day=cred.warmup_day,
            warmup_completed=cred.warmup_completed,
            created_at=cred.created_at,
            last_used_at=cred.last_used_at,
        )
        for cred in credentials
    ]


@router.delete("/{credentials_id}")
async def delete_credentials(
    credentials_id: int,
    db: AsyncSession = Depends(get_db),
    partner: Partner = Depends(get_current_partner),
):
    """
    Delete credentials

    This will also stop all associated channels.
    """
    # Check if credentials belong to this partner
    result = await db.execute(
        select(PartnerCredentials).where(
            PartnerCredentials.id == credentials_id,
            PartnerCredentials.partner_id == partner.id
        )
    )
    cred = result.scalar_one_or_none()

    if not cred:
        raise HTTPException(status_code=404, detail="Credentials not found")

    await db.delete(cred)
    await db.commit()

    return {"status": "deleted", "id": credentials_id}


@router.post("/validate", response_model=CredentialsValidateResponse)
async def validate_credentials(
    request: CredentialsValidateRequest,
    partner: Partner = Depends(get_current_partner),
):
    """
    Validate a session string without saving it

    Returns information about the Telegram account.
    """
    # TODO: Actually validate with Telethon
    # from telethon import TelegramClient
    # from telethon.sessions import StringSession
    #
    # try:
    #     client = TelegramClient(StringSession(request.session_string), api_id, api_hash)
    #     await client.connect()
    #     me = await client.get_me()
    #     await client.disconnect()
    #     return CredentialsValidateResponse(
    #         valid=True,
    #         telegram_id=me.id,
    #         username=me.username,
    #         first_name=me.first_name,
    #     )
    # except Exception as e:
    #     return CredentialsValidateResponse(valid=False, error=str(e))

    # For now: basic validation (Telethon integration later)
    if len(request.session_string) > 100:
        return CredentialsValidateResponse(
            valid=True,
            telegram_id=None,  # Will be filled after Telethon validation
            username=None,
            first_name=None,
        )
    else:
        return CredentialsValidateResponse(
            valid=False,
            error="Session string too short",
        )


@router.get("/{credentials_id}/setup-progress", response_model=SetupProgress)
async def get_setup_progress(
    credentials_id: int,
    db: AsyncSession = Depends(get_db),
    partner: Partner = Depends(get_current_partner),
):
    """
    Get the setup progress for credentials

    Use this to poll the setup status after adding credentials.
    """
    # Check if credentials belong to this partner
    result = await db.execute(
        select(PartnerCredentials).where(
            PartnerCredentials.id == credentials_id,
            PartnerCredentials.partner_id == partner.id
        )
    )
    cred = result.scalar_one_or_none()

    if not cred:
        raise HTTPException(status_code=404, detail="Credentials not found")

    # Determine status based on credentials state
    if cred.is_banned:
        return SetupProgress(
            status=SetupStatus.FAILED,
            step="banned",
            progress=0,
            message="Account is banned",
            error=cred.ban_reason,
        )
    elif cred.warmup_completed:
        return SetupProgress(
            status=SetupStatus.COMPLETED,
            step="completed",
            progress=100,
            message="Setup completed successfully",
        )
    elif cred.warmup_day > 0:
        progress = min(cred.warmup_day * 15, 90)  # ~7 days warmup
        return SetupProgress(
            status=SetupStatus.IN_PROGRESS,
            step=f"warmup_day_{cred.warmup_day}",
            progress=progress,
            message=f"Warming up account (day {cred.warmup_day})",
        )
    else:
        return SetupProgress(
            status=SetupStatus.PENDING,
            step="pending",
            progress=0,
            message="Waiting to start setup",
        )
