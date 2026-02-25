"""
Schedule API — view and toggle auto-publishing schedules.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..database import get_db
from ..api.auth import get_current_user
from ..schemas import ScheduleListResponse, ScheduleOut, ScheduleUpdateRequest, UserInfo
from content_manager_bot.database.models import ContentSchedule

router = APIRouter(prefix="/schedule", tags=["Schedule"])


@router.get("", response_model=ScheduleListResponse)
async def list_schedules(
    db: AsyncSession = Depends(get_db),
    user: UserInfo = Depends(get_current_user),
):
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin only")

    result = await db.execute(select(ContentSchedule).order_by(ContentSchedule.id))
    schedules = list(result.scalars().all())

    return ScheduleListResponse(
        schedules=[
            ScheduleOut(
                id=s.id,
                post_type=s.post_type,
                is_active=s.is_active,
                cron_expression=s.cron_expression,
                last_run=s.last_run,
                next_run=s.next_run,
            )
            for s in schedules
        ]
    )


@router.patch("/{schedule_id}", response_model=ScheduleOut)
async def update_schedule(
    schedule_id: int,
    req: ScheduleUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: UserInfo = Depends(get_current_user),
):
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin only")

    result = await db.execute(
        select(ContentSchedule).where(ContentSchedule.id == schedule_id)
    )
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    schedule.is_active = req.is_active
    await db.commit()
    await db.refresh(schedule)

    return ScheduleOut(
        id=schedule.id,
        post_type=schedule.post_type,
        is_active=schedule.is_active,
        cron_expression=schedule.cron_expression,
        last_run=schedule.last_run,
        next_run=schedule.next_run,
    )
