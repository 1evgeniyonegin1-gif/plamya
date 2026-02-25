"""
Статистика воронки продаж
"""
from datetime import datetime, timedelta
from typing import Dict, Any
from sqlalchemy import select, func, and_

from shared.database.base import AsyncSessionLocal
from curator_bot.database.models import User
from loguru import logger


async def get_funnel_stats(period_days: int = 7) -> Dict[str, Any]:
    """
    Получает статистику воронки за период

    Args:
        period_days: Количество дней для статистики

    Returns:
        Словарь со статистикой
    """
    cutoff_date = datetime.utcnow() - timedelta(days=period_days)

    async with AsyncSessionLocal() as session:
        # Общее количество лидов за период
        total_leads = await session.scalar(
            select(func.count(User.id)).where(
                User.funnel_started_at >= cutoff_date
            )
        ) or 0

        # По интентам
        client_leads = await session.scalar(
            select(func.count(User.id)).where(
                and_(
                    User.funnel_started_at >= cutoff_date,
                    User.user_intent == "client"
                )
            )
        ) or 0

        business_leads = await session.scalar(
            select(func.count(User.id)).where(
                and_(
                    User.funnel_started_at >= cutoff_date,
                    User.user_intent == "business"
                )
            )
        ) or 0

        curious_leads = await session.scalar(
            select(func.count(User.id)).where(
                and_(
                    User.funnel_started_at >= cutoff_date,
                    User.user_intent == "curious"
                )
            )
        ) or 0

        # Прошли квалификацию (выбрали боль или цель дохода)
        qualified = await session.scalar(
            select(func.count(User.id)).where(
                and_(
                    User.funnel_started_at >= cutoff_date,
                    User.funnel_step >= 2
                )
            )
        ) or 0

        # Дошли до предложения продукта
        reached_offer = await session.scalar(
            select(func.count(User.id)).where(
                and_(
                    User.funnel_started_at >= cutoff_date,
                    User.funnel_step >= 4
                )
            )
        ) or 0

        # Оставили контакт
        left_contact = await session.scalar(
            select(func.count(User.id)).where(
                and_(
                    User.funnel_started_at >= cutoff_date,
                    (User.phone.isnot(None)) | (User.email.isnot(None))
                )
            )
        ) or 0

        # Горячие лиды
        hot_leads = await session.scalar(
            select(func.count(User.id)).where(
                and_(
                    User.funnel_started_at >= cutoff_date,
                    User.lead_status == "hot"
                )
            )
        ) or 0

        # По болям (для клиентов)
        pain_stats = {}
        pain_types = ["weight", "energy", "immunity", "beauty", "kids", "sport"]
        for pain in pain_types:
            count = await session.scalar(
                select(func.count(User.id)).where(
                    and_(
                        User.funnel_started_at >= cutoff_date,
                        User.pain_point == pain
                    )
                )
            ) or 0
            pain_stats[pain] = count

        # По целям дохода (для бизнеса)
        income_stats = {}
        income_types = ["10_30k", "50_100k", "200k_plus", "unsure"]
        for income in income_types:
            count = await session.scalar(
                select(func.count(User.id)).where(
                    and_(
                        User.funnel_started_at >= cutoff_date,
                        User.income_goal == income
                    )
                )
            ) or 0
            income_stats[income] = count

    # Расчёт конверсий
    def safe_percent(part, total):
        return round(part / total * 100) if total > 0 else 0

    return {
        "period_days": period_days,
        "total_leads": total_leads,
        "by_intent": {
            "client": client_leads,
            "business": business_leads,
            "curious": curious_leads,
            "client_percent": safe_percent(client_leads, total_leads),
            "business_percent": safe_percent(business_leads, total_leads),
            "curious_percent": safe_percent(curious_leads, total_leads),
        },
        "funnel": {
            "qualified": qualified,
            "qualified_percent": safe_percent(qualified, total_leads),
            "reached_offer": reached_offer,
            "reached_offer_percent": safe_percent(reached_offer, total_leads),
            "left_contact": left_contact,
            "left_contact_percent": safe_percent(left_contact, total_leads),
            "hot_leads": hot_leads,
        },
        "pain_stats": pain_stats,
        "income_stats": income_stats,
    }


def format_funnel_stats(stats: Dict[str, Any]) -> str:
    """
    Форматирует статистику воронки для отправки в Telegram

    Args:
        stats: Словарь со статистикой

    Returns:
        Отформатированное сообщение
    """
    pain_names = {
        "weight": "Похудение",
        "energy": "Энергия",
        "immunity": "Иммунитет",
        "beauty": "Красота",
        "kids": "Дети",
        "sport": "Спорт",
    }

    income_names = {
        "10_30k": "10-30к",
        "50_100k": "50-100к",
        "200k_plus": "200к+",
        "unsure": "Не уверен",
    }

    # Топ боли
    pain_sorted = sorted(
        stats["pain_stats"].items(),
        key=lambda x: x[1],
        reverse=True
    )[:3]
    pain_text = "\n".join([
        f"  • {pain_names.get(p, p)}: {c}"
        for p, c in pain_sorted if c > 0
    ]) or "  Нет данных"

    # Топ целей дохода
    income_sorted = sorted(
        stats["income_stats"].items(),
        key=lambda x: x[1],
        reverse=True
    )[:3]
    income_text = "\n".join([
        f"  • {income_names.get(i, i)}: {c}"
        for i, c in income_sorted if c > 0
    ]) or "  Нет данных"

    return f"""📊 <b>СТАТИСТИКА ВОРОНКИ</b>
<i>За последние {stats['period_days']} дней</i>

<b>Новых лидов:</b> {stats['total_leads']}
├── Клиент (здоровье): {stats['by_intent']['client']} ({stats['by_intent']['client_percent']}%)
├── Бизнес: {stats['by_intent']['business']} ({stats['by_intent']['business_percent']}%)
└── Любопытные: {stats['by_intent']['curious']} ({stats['by_intent']['curious_percent']}%)

<b>Конверсия воронки:</b>
├── Прошли квалификацию: {stats['funnel']['qualified']} ({stats['funnel']['qualified_percent']}%)
├── Дошли до предложения: {stats['funnel']['reached_offer']} ({stats['funnel']['reached_offer_percent']}%)
├── Оставили контакт: {stats['funnel']['left_contact']} ({stats['funnel']['left_contact_percent']}%)
└── 🔥 Горячих лидов: {stats['funnel']['hot_leads']}

<b>Топ боли (клиенты):</b>
{pain_text}

<b>Топ целей дохода (бизнес):</b>
{income_text}"""


def calculate_lead_score(user: User) -> int:
    """
    Рассчитывает скоринг лида

    Шкала 0-100:
    - 0-20: Холодный
    - 21-50: Тёплый
    - 51-80: Горячий
    - 81-100: Очень горячий

    Args:
        user: Пользователь

    Returns:
        Скор от 0 до 100
    """
    score = 0

    # Базовые очки за интент
    if user.user_intent == "business":
        score += 20  # Бизнес-лиды ценнее
    elif user.user_intent == "client":
        score += 10

    # За прохождение воронки
    score += min(user.funnel_step * 5, 25)  # Макс 25 очков

    # За оставленный контакт
    if user.phone:
        score += 20
    if user.email:
        score += 10

    # За статус
    if user.lead_status == "hot":
        score += 15
    elif user.lead_status == "qualified":
        score += 5

    # За высокие цели дохода (бизнес)
    if user.income_goal == "200k_plus":
        score += 10
    elif user.income_goal == "50_100k":
        score += 5

    # Штраф за неактивность
    if user.last_activity:
        days_inactive = (datetime.utcnow() - user.last_activity).days
        score -= min(days_inactive * 2, 20)  # Макс штраф 20

    return max(min(score, 100), 0)  # Ограничиваем 0-100
