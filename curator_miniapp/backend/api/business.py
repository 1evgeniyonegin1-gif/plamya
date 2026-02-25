"""
Business API

Бизнес-раздел с моделью APEXFLOW
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..config import settings
from ..models.user import CuratorUser
from ..models.analytics import BusinessInterest
from .auth import get_current_user

router = APIRouter(prefix="/business", tags=["Business"])


# Pydantic models
class ModelComparisonItem(BaseModel):
    """Single item in model comparison"""
    icon: str
    text: str


class ModelComparison(BaseModel):
    """Comparison of business models"""
    title: str
    subtitle: str
    items: list[ModelComparisonItem]


class BusinessStep(BaseModel):
    """Step in the business presentation"""
    number: int
    title: str
    items: list[str]


class CTALinks(BaseModel):
    """Call-to-action links"""
    telegram_chat: str
    registration: str
    telegram_username: str


class BusinessPresentation(BaseModel):
    """Full business presentation data"""
    headline: str
    tagline: str
    traditional_model: ModelComparison
    apexflow_model: ModelComparison
    requirements: BusinessStep
    cta: CTALinks


class ContactRequest(BaseModel):
    """Request when user clicks CTA"""
    action: str  # 'telegram_chat', 'registration'


class PartnerStatusResponse(BaseModel):
    """Partner status response"""
    is_partner: bool
    partner_registered_at: Optional[datetime] = None
    has_access_to_panel: bool


@router.get("/presentation", response_model=BusinessPresentation)
async def get_business_presentation():
    """
    Get business presentation data

    Returns all content for the Business page:
    - Comparison of traditional vs APEXFLOW models
    - Requirements to join
    - CTA links
    """
    return BusinessPresentation(
        headline="БИЗНЕС С APEXFLOW",
        tagline="Масштабируй свой сетевой бизнес",

        traditional_model=ModelComparison(
            title="😓 ОБЫЧНАЯ МОДЕЛЬ",
            subtitle="Ты один ведёшь:",
            items=[
                ModelComparisonItem(icon="📱", text="1 Telegram канал"),
                ModelComparisonItem(icon="📸", text="Stories каждый день"),
                ModelComparisonItem(icon="✍️", text="Пишешь сообщения вручную"),
                ModelComparisonItem(icon="👥", text="Приглашаешь в бизнес сам"),
                ModelComparisonItem(icon="⏰", text="Результат: работаешь 8ч в день"),
                ModelComparisonItem(icon="👤", text="Команда: 3-4 партнёра"),
            ],
        ),

        apexflow_model=ModelComparison(
            title="🚀 МОДЕЛЬ APEXFLOW",
            subtitle="Ты + система:",
            items=[
                ModelComparisonItem(icon="🤖", text="10+ каналов ведут боты"),
                ModelComparisonItem(icon="✨", text="AI пишет контент"),
                ModelComparisonItem(icon="💬", text="Traffic Engine комментирует"),
                ModelComparisonItem(icon="🎯", text="Куратор прогревает лидов"),
                ModelComparisonItem(icon="📈", text="Результат: масштаб x10"),
                ModelComparisonItem(icon="💰", text="Ограничение: только расходники"),
            ],
        ),

        requirements=BusinessStep(
            number=1,
            title="🔥 ЧТО НУЖНО ОТ ТЕБЯ:",
            items=[
                "Зарегистрироваться партнёром NL",
                "Оплачивать расходники (API, sim-карты)",
                "Развивать продукт вместе с нами",
                "",
                "Это НЕ готовое решение — это инструмент, который мы развиваем вместе с партнёрами.",
            ],
        ),

        cta=CTALinks(
            telegram_chat=f"https://t.me/{settings.business_contact_username}",
            registration=settings.referral_registration,
            telegram_username=settings.business_contact_username,
        ),
    )


@router.post("/contact")
async def track_business_contact(
    request: ContactRequest,
    db: AsyncSession = Depends(get_db),
    user: CuratorUser = Depends(get_current_user),
):
    """
    Track when user clicks a CTA button

    This endpoint:
    1. Records the interest in database
    2. Sends notification to owner (via bot)
    3. Returns success

    Actions:
    - **telegram_chat**: User clicked "Написать в Telegram"
    - **registration**: User clicked "Регистрация партнёром"
    """
    # Validate action
    if request.action not in ['telegram_chat', 'registration', 'view_business']:
        raise HTTPException(status_code=400, detail="Invalid action")

    # Create interest record
    interest = BusinessInterest(
        user_id=user.id,
        telegram_id=user.telegram_id,
        action=request.action,
        created_at=datetime.utcnow(),
    )
    db.add(interest)

    # Update user stats
    user.business_section_viewed = True

    await db.commit()

    # Send notification to owner
    await _notify_owner(user, request.action)

    return {
        "success": True,
        "message": "Интерес записан",
        "redirect": _get_redirect_url(request.action),
    }


@router.get("/partner-status", response_model=PartnerStatusResponse)
async def get_partner_status(
    user: CuratorUser = Depends(get_current_user),
):
    """
    Check if current user is a registered partner

    Returns:
    - **is_partner**: Whether user is a partner
    - **partner_registered_at**: When user became a partner
    - **has_access_to_panel**: Whether user has access to Partner Panel
    """
    return PartnerStatusResponse(
        is_partner=user.is_partner,
        partner_registered_at=user.partner_registered_at,
        has_access_to_panel=user.is_partner,  # For now, same as is_partner
    )


@router.post("/mark-partner")
async def mark_as_partner(
    db: AsyncSession = Depends(get_db),
    user: CuratorUser = Depends(get_current_user),
):
    """
    Mark current user as a partner

    Note: This should be called after user confirms they registered on nlstar.com
    In production, this should be verified somehow
    """
    if user.is_partner:
        return {"success": True, "message": "Вы уже партнёр"}

    user.is_partner = True
    user.partner_registered_at = datetime.utcnow()
    await db.commit()

    # Notify owner
    await _notify_owner(user, "became_partner")

    return {
        "success": True,
        "message": "Добро пожаловать в команду!",
        "has_access_to_panel": True,
    }


async def _notify_owner(user: CuratorUser, action: str):
    """
    Send notification to owner about user action

    Uses curator bot to send message
    """
    try:
        # Import here to avoid circular imports
        import sys
        from pathlib import Path
        project_root = Path(__file__).parent.parent.parent.parent
        sys.path.insert(0, str(project_root))

        from aiogram import Bot

        bot = Bot(token=settings.bot_token)

        action_texts = {
            "telegram_chat": "💬 Хочет написать в Telegram",
            "registration": "🚀 Перешёл на регистрацию",
            "view_business": "👀 Просмотрел бизнес-раздел",
            "became_partner": "🎉 СТАЛ ПАРТНЁРОМ!",
        }

        action_text = action_texts.get(action, action)

        message = (
            f"🔥 Активность в Mini App!\n\n"
            f"Действие: {action_text}\n"
            f"Имя: {user.telegram_first_name or 'N/A'}\n"
            f"Username: @{user.telegram_username or 'N/A'}\n"
            f"ID: {user.telegram_id}\n\n"
            f"[Написать](tg://user?id={user.telegram_id})"
        )

        await bot.send_message(
            chat_id=settings.owner_telegram_id,
            text=message,
            parse_mode="Markdown",
        )

        await bot.session.close()

    except Exception as e:
        print(f"Error notifying owner: {e}")


def _get_redirect_url(action: str) -> str:
    """Get redirect URL for action"""
    if action == "telegram_chat":
        return f"https://t.me/{settings.business_contact_username}"
    elif action == "registration":
        return settings.referral_registration
    return ""
