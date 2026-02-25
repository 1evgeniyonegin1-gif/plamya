"""
Diary API — read and create diary entries.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from ..database import get_db
from ..api.auth import get_current_user
from ..schemas import DiaryListResponse, DiaryEntryOut, DiaryCreateRequest, UserInfo
from content_manager_bot.database.models import DiaryEntry

router = APIRouter(prefix="/diary", tags=["Diary"])


@router.get("", response_model=DiaryListResponse)
async def list_diary(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    user: UserInfo = Depends(get_current_user),
):
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin only")

    result = await db.execute(
        select(DiaryEntry)
        .where(DiaryEntry.admin_id == user.telegram_id)
        .order_by(desc(DiaryEntry.created_at))
        .limit(limit)
    )
    entries = list(result.scalars().all())

    return DiaryListResponse(
        entries=[
            DiaryEntryOut(id=e.id, entry_text=e.entry_text, created_at=e.created_at)
            for e in entries
        ]
    )


@router.post("", response_model=DiaryEntryOut)
async def create_diary_entry(
    req: DiaryCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: UserInfo = Depends(get_current_user),
):
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin only")

    entry = DiaryEntry(
        admin_id=user.telegram_id,
        entry_text=req.text,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)

    return DiaryEntryOut(id=entry.id, entry_text=entry.entry_text, created_at=entry.created_at)
