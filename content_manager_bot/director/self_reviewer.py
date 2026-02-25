"""
SelfReviewer — AI самоанализ каждые 10 постов.

Deepseek анализирует 10 последних постов + метрики + channel state
→ strengths, weaknesses, recommendations, topic_suggestions, avoid.
"""
import json
from datetime import datetime
from typing import Optional

from loguru import logger
from sqlalchemy import select, func, and_

from shared.database.base import AsyncSessionLocal
from shared.ai_clients.deepseek_client import DeepseekClient
from content_manager_bot.database.models import Post
from content_manager_bot.database.director_models import ContentSelfReview
from content_manager_bot.director.channel_memory import get_channel_memory


class SelfReviewer:
    """AI самоанализ контента — каждые 10 постов."""

    def __init__(self):
        self._ai_client: Optional[DeepseekClient] = None

    def _get_ai(self) -> DeepseekClient:
        if self._ai_client is None:
            self._ai_client = DeepseekClient()
        return self._ai_client

    async def should_run(self, segment: str) -> bool:
        """Проверяет нужно ли запустить review (каждые 10 постов)."""
        try:
            async with AsyncSessionLocal() as session:
                # Последний review
                last_review = await session.execute(
                    select(ContentSelfReview).where(
                        ContentSelfReview.segment == segment,
                    ).order_by(ContentSelfReview.created_at.desc()).limit(1)
                )
                review = last_review.scalar_one_or_none()
                last_reviewed = review.posts_reviewed if review else 0

                # Текущее число постов
                total = await session.execute(
                    select(func.count(Post.id)).where(
                        and_(
                            Post.status == "published",
                            Post.segment == segment,
                        )
                    )
                )
                current_total = total.scalar() or 0

                return (current_total - last_reviewed) >= 10

        except Exception as e:
            logger.warning(f"[DIRECTOR] should_run error: {e}")
            return False

    async def run_review(self, segment: str) -> Optional[dict]:
        """Запускает AI самоанализ.

        Returns:
            dict: {strengths, weaknesses, recommendations, topic_suggestions, avoid}
        """
        try:
            # Загружаем данные
            posts_data = await self._load_posts_with_metrics(segment, limit=10)
            if not posts_data:
                logger.info(f"[DIRECTOR] No posts for review in {segment}")
                return None

            memory = get_channel_memory()
            channel_context = await memory.get_context_for_prompt(segment)

            # Промпт
            posts_block = "\n\n".join([
                f"#{p['id']} ({p['type']}): {p['preview']}\n"
                f"  Views: {p['views']}, Reactions: {p['reactions']}, Engagement: {p['engagement']:.1f}%"
                for p in posts_data
            ])

            prompt = f"""Ты критик Telegram-канала (сегмент: {segment}). Вот 10 последних постов с метриками:

{posts_block}

Channel state:
{channel_context}

Ответь СТРОГО JSON (без markdown, без пояснений):
{{
  "strengths": ["что хорошо (2-3 пункта)"],
  "weaknesses": ["что плохо (2-3 пункта)"],
  "recommendations": ["конкретные советы (3-5 пунктов)"],
  "topic_suggestions": ["3 темы которые стоит раскрыть"],
  "avoid": ["чего избегать (1-2 пункта)"]
}}"""

            ai = self._get_ai()
            response = await ai.generate_response(
                system_prompt="Ты AI-критик контента. Отвечаешь только JSON.",
                user_message=prompt,
                temperature=0.7,
                max_tokens=800,
            )

            # Парсим
            review_data = self._parse_review(response)
            if not review_data:
                logger.error(f"[DIRECTOR] Failed to parse review for {segment}")
                return None

            # Сохраняем
            async with AsyncSessionLocal() as session:
                total = await session.execute(
                    select(func.count(Post.id)).where(
                        and_(
                            Post.status == "published",
                            Post.segment == segment,
                        )
                    )
                )
                current_total = total.scalar() or 0

                review = ContentSelfReview(
                    segment=segment,
                    posts_reviewed=current_total,
                    review_data=review_data,
                    applied=False,
                )
                session.add(review)
                await session.commit()

            logger.info(f"[DIRECTOR] Self-review completed for {segment}: {len(review_data.get('recommendations', []))} recommendations")
            return review_data

        except Exception as e:
            logger.error(f"[DIRECTOR] run_review error: {e}")
            return None

    async def get_last_review(self, segment: str) -> Optional[dict]:
        """Возвращает последний review для отображения."""
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(ContentSelfReview).where(
                        ContentSelfReview.segment == segment,
                    ).order_by(ContentSelfReview.created_at.desc()).limit(1)
                )
                review = result.scalar_one_or_none()

                if not review:
                    return None

                return {
                    "segment": segment,
                    "posts_reviewed": review.posts_reviewed,
                    "review": review.review_data,
                    "created_at": review.created_at.isoformat() if review.created_at else None,
                    "applied": review.applied,
                }

        except Exception as e:
            logger.error(f"[DIRECTOR] get_last_review error: {e}")
            return None

    async def _load_posts_with_metrics(self, segment: str, limit: int = 10) -> list[dict]:
        """Загружает посты с метриками."""
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(Post).where(
                        and_(
                            Post.status == "published",
                            Post.segment == segment,
                        )
                    ).order_by(Post.published_at.desc()).limit(limit)
                )
                posts = result.scalars().all()

                return [
                    {
                        "id": p.id,
                        "type": p.post_type,
                        "preview": p.content[:120].replace("\n", " "),
                        "views": p.views_count or 0,
                        "reactions": p.reactions_count or 0,
                        "engagement": p.engagement_rate or 0.0,
                    }
                    for p in posts
                ]

        except Exception as e:
            logger.warning(f"[DIRECTOR] _load_posts_with_metrics error: {e}")
            return []

    def _parse_review(self, response: str) -> Optional[dict]:
        """Парсит JSON из ответа AI."""
        try:
            text = response.strip()
            if text.startswith("```"):
                lines = text.split("\n")
                text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

            start = text.find('{')
            end = text.rfind('}')
            if start == -1 or end == -1:
                return None

            data = json.loads(text[start:end + 1])

            # Валидация
            required = {"strengths", "weaknesses", "recommendations"}
            if not required.issubset(data.keys()):
                return None

            return data

        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"[DIRECTOR] Review parse error: {e}")
            return None


# Singleton
_reviewer: Optional[SelfReviewer] = None


def get_self_reviewer() -> SelfReviewer:
    global _reviewer
    if _reviewer is None:
        _reviewer = SelfReviewer()
    return _reviewer
