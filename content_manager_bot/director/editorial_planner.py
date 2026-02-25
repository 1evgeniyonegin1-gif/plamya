"""
EditorialPlanner — AI недельный контент-план.

Вдохновлено: Narrato AI Content Genie, Relevance AI (constrained autonomy).

1 вызов Deepseek/неделю → JSON план 10 слотов.
Использует ChannelMemory + PerformanceAnalyzer + SelfReview.
"""
import json
from datetime import datetime, timedelta
from typing import Optional

from loguru import logger
from sqlalchemy import select, and_

from shared.database.base import AsyncSessionLocal
from shared.ai_clients.deepseek_client import DeepseekClient
from shared.config.settings import settings
from content_manager_bot.database.director_models import ContentPlan
from content_manager_bot.director.channel_memory import get_channel_memory
from content_manager_bot.director.performance_analyzer import get_performance_analyzer


class EditorialPlanner:
    """AI-продюсер: генерирует недельный контент-план."""

    def __init__(self):
        self._ai_client: Optional[DeepseekClient] = None

    def _get_ai(self) -> DeepseekClient:
        if self._ai_client is None:
            self._ai_client = DeepseekClient()
        return self._ai_client

    async def generate_weekly_plan(self, segment: str) -> Optional[dict]:
        """Генерирует недельный план (10 слотов).

        Returns:
            dict с plan_data или None при ошибке.
        """
        try:
            # Собираем контекст
            memory = get_channel_memory()
            analyzer = get_performance_analyzer()

            channel_context = await memory.get_context_for_prompt(segment)
            insights = await analyzer.get_insights(segment)

            # Self-review рекомендации
            recommendations = await self._get_last_review_recommendations(segment)

            # Промпт
            prompt = f"""Ты продюсер Telegram-канала, сегмент: {segment}.

{channel_context}

АНАЛИТИКА:
{insights}

{f'РЕКОМЕНДАЦИИ ОТ SELF-REVIEW: {recommendations}' if recommendations else ''}

Спланируй 10 постов на неделю. Для каждого:
- day (1-7)
- post_type (observation/question/thought/journey/honesty/absurd/self_irony)
- topic_hint (направление мысли, 1 предложение)
- narrative_role (standalone / thread_start / thread_continue / thread_payoff)
- energy (low/medium/high — чередуй!)

Правила:
- Не больше 2 постов одного типа подряд
- 40% standalone, 30% thread_start/continue, 30% payoff/question
- Чередуй энергию: high → low → medium → high
- Используй topic gaps если есть

Ответь ТОЛЬКО JSON массивом. Без markdown, без пояснений."""

            ai = self._get_ai()
            response = await ai.generate_response(
                system_prompt="Ты AI-продюсер контента. Отвечаешь только JSON.",
                user_message=prompt,
                temperature=0.8,
                max_tokens=1000,
            )

            # Парсим JSON
            plan_data = self._parse_plan(response)
            if not plan_data:
                logger.error(f"[DIRECTOR] Failed to parse plan for {segment}")
                return None

            # Сохраняем
            week_start = self._get_week_start()

            async with AsyncSessionLocal() as session:
                # Деактивируем старые планы
                old_plans = await session.execute(
                    select(ContentPlan).where(
                        and_(
                            ContentPlan.segment == segment,
                            ContentPlan.status == "active",
                        )
                    )
                )
                for old in old_plans.scalars().all():
                    old.status = "archived"

                # Создаём новый
                plan = ContentPlan(
                    segment=segment,
                    week_start=week_start,
                    plan_data=plan_data,
                    slots_used=0,
                    slots_total=len(plan_data),
                    ai_model="deepseek",
                )
                session.add(plan)
                await session.commit()
                await session.refresh(plan)

                logger.info(f"[DIRECTOR] Weekly plan created for {segment}: {len(plan_data)} slots")
                return {
                    "plan_id": plan.id,
                    "segment": segment,
                    "week_start": str(week_start),
                    "slots": plan_data,
                    "total": len(plan_data),
                }

        except Exception as e:
            logger.error(f"[DIRECTOR] generate_weekly_plan error: {e}")
            return None

    async def get_next_planned_post(self, segment: str) -> Optional[dict]:
        """Достаёт следующий слот из активного плана.

        Returns:
            dict: {post_type, topic_hint, narrative_role, energy} или None.
        """
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(ContentPlan).where(
                        and_(
                            ContentPlan.segment == segment,
                            ContentPlan.status == "active",
                        )
                    ).order_by(ContentPlan.created_at.desc()).limit(1)
                )
                plan = result.scalar_one_or_none()

                if not plan:
                    # Автоматически генерируем план
                    logger.info(f"[DIRECTOR] No active plan for {segment}, generating...")
                    plan_data = await self.generate_weekly_plan(segment)
                    if not plan_data:
                        return None

                    # Перезагружаем план
                    result = await session.execute(
                        select(ContentPlan).where(
                            and_(
                                ContentPlan.segment == segment,
                                ContentPlan.status == "active",
                            )
                        ).order_by(ContentPlan.created_at.desc()).limit(1)
                    )
                    plan = result.scalar_one_or_none()
                    if not plan:
                        return None

                slots = plan.plan_data
                if not slots or not isinstance(slots, list):
                    return None

                # Находим следующий незаполненный слот
                used = plan.slots_used or 0
                if used >= len(slots):
                    # План закончился — генерируем новый
                    plan.status = "completed"
                    await session.commit()
                    logger.info(f"[DIRECTOR] Plan {plan.id} completed, generating new...")
                    await self.generate_weekly_plan(segment)
                    return await self.get_next_planned_post(segment)

                slot = slots[used]

                # Помечаем как in_progress
                plan.slots_used = used + 1
                plan.updated_at = datetime.utcnow()
                await session.commit()

                logger.info(f"[DIRECTOR] Next slot for {segment}: {slot.get('post_type')} (slot {used + 1}/{len(slots)})")
                return slot

        except Exception as e:
            logger.error(f"[DIRECTOR] get_next_planned_post error: {e}")
            return None

    async def get_active_plan(self, segment: str) -> Optional[dict]:
        """Возвращает активный план для отображения."""
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(ContentPlan).where(
                        and_(
                            ContentPlan.segment == segment,
                            ContentPlan.status == "active",
                        )
                    ).order_by(ContentPlan.created_at.desc()).limit(1)
                )
                plan = result.scalar_one_or_none()

                if not plan:
                    return None

                return {
                    "plan_id": plan.id,
                    "segment": segment,
                    "week_start": str(plan.week_start),
                    "slots": plan.plan_data,
                    "used": plan.slots_used,
                    "total": plan.slots_total,
                    "status": plan.status,
                }

        except Exception as e:
            logger.error(f"[DIRECTOR] get_active_plan error: {e}")
            return None

    def _parse_plan(self, response: str) -> Optional[list]:
        """Парсит JSON из ответа AI."""
        try:
            # Убираем markdown code blocks
            text = response.strip()
            if text.startswith("```"):
                lines = text.split("\n")
                text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

            # Ищем JSON массив
            start = text.find('[')
            end = text.rfind(']')
            if start == -1 or end == -1:
                return None

            json_str = text[start:end + 1]
            data = json.loads(json_str)

            if not isinstance(data, list):
                return None

            # Валидация слотов
            valid = []
            valid_types = {"observation", "question", "thought", "journey", "honesty", "absurd", "self_irony"}
            for slot in data:
                if isinstance(slot, dict) and slot.get("post_type") in valid_types:
                    valid.append({
                        "day": slot.get("day", 1),
                        "post_type": slot["post_type"],
                        "topic_hint": slot.get("topic_hint", ""),
                        "narrative_role": slot.get("narrative_role", "standalone"),
                        "energy": slot.get("energy", "medium"),
                    })

            return valid if valid else None

        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"[DIRECTOR] Plan parse error: {e}")
            return None

    async def _get_last_review_recommendations(self, segment: str) -> str:
        """Получает рекомендации из последнего self-review."""
        try:
            from content_manager_bot.database.director_models import ContentSelfReview

            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(ContentSelfReview).where(
                        ContentSelfReview.segment == segment,
                    ).order_by(ContentSelfReview.created_at.desc()).limit(1)
                )
                review = result.scalar_one_or_none()

                if not review or not review.review_data:
                    return ""

                recs = review.review_data.get("recommendations", [])
                if recs:
                    return "; ".join(recs[:5])
                return ""

        except Exception as e:
            logger.warning(f"[DIRECTOR] _get_last_review error: {e}")
            return ""

    @staticmethod
    def _get_week_start() -> datetime:
        """Возвращает понедельник текущей недели."""
        today = datetime.utcnow().date()
        return today - timedelta(days=today.weekday())


# Singleton
_planner: Optional[EditorialPlanner] = None


def get_editorial_planner() -> EditorialPlanner:
    global _planner
    if _planner is None:
        _planner = EditorialPlanner()
    return _planner
