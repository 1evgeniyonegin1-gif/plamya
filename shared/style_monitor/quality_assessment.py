"""
Модуль для оценки качества постов из Telegram каналов.

Оценка производится по нескольким метрикам:
- Views (просмотры)
- Engagement (вовлечённость: reactions + forwards)
- Length (длина текста)
- Readability (читаемость)
- Freshness (свежесть контента)
"""

import re
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.models import StylePost, StyleChannel
from shared.database.base import AsyncSessionLocal

logger = logging.getLogger(__name__)


class QualityAssessmentEngine:
    """Движок для оценки качества постов из Telegram каналов"""

    # Веса для итоговой оценки
    WEIGHTS = {
        "views": 0.3,        # Просмотры (30%)
        "engagement": 0.25,  # Вовлечённость (25%)
        "length": 0.15,      # Длина текста (15%)
        "readability": 0.15, # Читаемость (15%)
        "freshness": 0.15    # Свежесть (15%)
    }

    MIN_VIEWS = 500     # Минимум просмотров для рассмотрения
    MIN_SCORE = 7.0     # Минимальная оценка для добавления в RAG

    # Оптимальные параметры для контента
    OPTIMAL_LENGTH_MIN = 300
    OPTIMAL_LENGTH_MAX = 800
    GOOD_LENGTH_MIN = 200
    GOOD_LENGTH_MAX = 1200

    def __init__(self):
        """Инициализация движка оценки качества"""
        self._channel_stats_cache: Dict[int, Dict] = {}

    async def assess_post(
        self,
        post: StylePost,
        channel: StyleChannel,
        session: Optional[AsyncSession] = None
    ) -> Dict:
        """
        Оценить качество поста (0-10).

        Args:
            post: Пост для оценки
            channel: Канал, из которого пост
            session: Опциональная сессия БД (для оптимизации)

        Returns:
            {
                "quality_score": float,
                "style_tags": dict,
                "reason": str
            }
        """
        scores = {}

        # 1. Оценка просмотров (нормализация по каналу)
        if post.views_count and post.views_count >= self.MIN_VIEWS:
            avg_views = await self._get_channel_avg_views(channel.id, session)
            if avg_views > 0:
                # Нормализация: средний пост = 5 баллов, выше среднего = до 10
                scores["views"] = min(10, (post.views_count / avg_views) * 5)
            else:
                scores["views"] = 5  # Нет статистики - средний балл
        else:
            scores["views"] = 0  # Недостаточно просмотров

        # 2. Вовлечённость (reactions + forwards / views)
        if post.views_count and post.views_count > 0:
            engagement = (post.reactions_count or 0) + (post.forwards_count or 0)
            engagement_rate = engagement / post.views_count

            # 2% engagement = 10 баллов (отличный показатель для Telegram)
            scores["engagement"] = min(10, engagement_rate * 50)
        else:
            scores["engagement"] = 0

        # 3. Длина текста
        text_len = len(post.text) if post.text else 0

        if self.OPTIMAL_LENGTH_MIN <= text_len <= self.OPTIMAL_LENGTH_MAX:
            scores["length"] = 10  # Оптимальная длина
        elif self.GOOD_LENGTH_MIN <= text_len < self.OPTIMAL_LENGTH_MIN:
            scores["length"] = 7  # Немного короче
        elif self.OPTIMAL_LENGTH_MAX < text_len <= self.GOOD_LENGTH_MAX:
            scores["length"] = 7  # Немного длиннее
        else:
            scores["length"] = 4  # Слишком короткий или длинный

        # 4. Читаемость
        readability = self._assess_readability(post.text or "")
        scores["readability"] = readability

        # 5. Свежесть
        if post.post_date:
            days_ago = (datetime.now() - post.post_date).days

            if days_ago <= 7:
                scores["freshness"] = 10  # Свежий контент
            elif days_ago <= 30:
                scores["freshness"] = 7   # Месячной давности
            elif days_ago <= 90:
                scores["freshness"] = 5   # До 3 месяцев
            else:
                scores["freshness"] = 3   # Старый контент
        else:
            scores["freshness"] = 5  # Дата неизвестна

        # Итоговая оценка
        final_score = sum(
            scores[key] * self.WEIGHTS[key]
            for key in scores
        )

        # Style tags
        style_tags = {
            "tone": self._detect_tone(post.text or ""),
            "length": "optimal" if self.OPTIMAL_LENGTH_MIN <= text_len <= self.OPTIMAL_LENGTH_MAX else "suboptimal",
            "emoji_count": self._count_emojis(post.text or ""),
            "has_cta": self._has_call_to_action(post.text or ""),
            "paragraph_count": (post.text or "").count("\n\n") + 1,
            "has_formatting": self._has_html_formatting(post.text or "")
        }

        return {
            "quality_score": round(final_score, 1),
            "style_tags": style_tags,
            "reason": self._explain_score(scores, final_score),
            "component_scores": scores  # Для отладки
        }

    async def _get_channel_avg_views(
        self,
        channel_id: int,
        session: Optional[AsyncSession] = None
    ) -> float:
        """Получить средние просмотры по каналу"""
        # Проверяем кэш
        if channel_id in self._channel_stats_cache:
            cache_entry = self._channel_stats_cache[channel_id]
            # Кэш на 1 час
            if (datetime.now() - cache_entry["cached_at"]).seconds < 3600:
                return cache_entry["avg_views"]

        # Запрашиваем из БД
        should_close = False
        if session is None:
            session = AsyncSessionLocal()
            should_close = True

        try:
            result = await session.execute(
                select(func.avg(StylePost.views_count))
                .where(
                    StylePost.channel_id == channel_id,
                    StylePost.views_count.isnot(None),
                    StylePost.views_count > 0
                )
            )
            avg_views = result.scalar() or 0

            # Кэшируем
            self._channel_stats_cache[channel_id] = {
                "avg_views": avg_views,
                "cached_at": datetime.now()
            }

            return avg_views

        finally:
            if should_close:
                await session.close()

    def _assess_readability(self, text: str) -> float:
        """
        Оценка читаемости (0-10).

        Факторы:
        - Короткие абзацы
        - Наличие emoji
        - HTML форматирование
        - Не слишком длинные предложения
        """
        score = 5.0  # Базовая оценка

        # 1. Короткие абзацы (+2)
        paragraphs = text.split("\n\n")
        if paragraphs:
            avg_para_len = sum(len(p) for p in paragraphs) / len(paragraphs)
            if avg_para_len < 200:
                score += 2
            elif avg_para_len < 300:
                score += 1

        # 2. Наличие emoji (+1)
        if self._count_emojis(text) > 0:
            score += 1

        # 3. HTML форматирование (+2)
        if self._has_html_formatting(text):
            score += 2

        # 4. Не слишком длинные предложения (проверка на точки)
        sentences = text.split(". ")
        if len(sentences) > 1:
            avg_sentence_len = sum(len(s) for s in sentences) / len(sentences)
            if avg_sentence_len < 100:  # Короткие предложения - хорошо
                score += 1

        return min(10, score)

    def _detect_tone(self, text: str) -> str:
        """
        Определить тон текста (heuristic).

        Returns: "motivational", "informational", "promotional", "conversational"
        """
        text_lower = text.lower()

        # Мотивационные маркеры
        motivational_words = [
            "успех", "достичь", "мечта", "цель", "вдохнов",
            "возможность", "результат", "изменить", "поверь"
        ]
        if any(word in text_lower for word in motivational_words):
            return "motivational"

        # Промо-маркеры
        promo_words = ["акция", "скидка", "специальное предложение", "только сегодня", "успей"]
        if any(word in text_lower for word in promo_words):
            return "promotional"

        # Информационные маркеры
        info_words = ["узнать", "информация", "важно", "обратите внимание", "факт"]
        if any(word in text_lower for word in info_words):
            return "informational"

        return "conversational"

    def _count_emojis(self, text: str) -> int:
        """Подсчитать количество emoji в тексте"""
        # Простая эвристика: символы Unicode в диапазонах emoji
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # Emoticons
            "\U0001F300-\U0001F5FF"  # Symbols & Pictographs
            "\U0001F680-\U0001F6FF"  # Transport & Map
            "\U0001F1E0-\U0001F1FF"  # Flags
            "\U00002702-\U000027B0"
            "\U000024C2-\U0001F251"
            "]+",
            flags=re.UNICODE
        )
        emojis = emoji_pattern.findall(text)
        return len(emojis)

    def _has_call_to_action(self, text: str) -> bool:
        """Проверить наличие призыва к действию"""
        cta_patterns = [
            r"переход(и|ите) по ссылке",
            r"узна(й|йте) больше",
            r"закаж(и|ите)",
            r"напиш(и|ите)",
            r"подпис(ывайся|ывайтесь)",
            r"жм(и|ите)",
            r"переход(и|ите)",
        ]

        text_lower = text.lower()
        return any(re.search(pattern, text_lower) for pattern in cta_patterns)

    def _has_html_formatting(self, text: str) -> bool:
        """Проверить наличие HTML форматирования"""
        html_tags = ["<b>", "<i>", "<u>", "<s>", "<code>", "<pre>", "<blockquote>", "<a href"]
        return any(tag in text for tag in html_tags)

    def _explain_score(self, scores: Dict[str, float], final_score: float) -> str:
        """Объяснить почему такая оценка"""
        reasons = []

        # Находим сильные и слабые стороны
        strong_points = [k for k, v in scores.items() if v >= 8]
        weak_points = [k for k, v in scores.items() if v < 5]

        if strong_points:
            strong_names = {
                "views": "high views",
                "engagement": "high engagement",
                "length": "optimal length",
                "readability": "good readability",
                "freshness": "fresh content"
            }
            reasons.append("Strong: " + ", ".join(strong_names.get(p, p) for p in strong_points))

        if weak_points:
            weak_names = {
                "views": "low views",
                "engagement": "low engagement",
                "length": "suboptimal length",
                "readability": "poor readability",
                "freshness": "old content"
            }
            reasons.append("Weak: " + ", ".join(weak_names.get(p, p) for p in weak_points))

        if not reasons:
            reasons.append("Average performance across all metrics")

        return "; ".join(reasons)

    async def assess_posts_batch(
        self,
        posts: list[StylePost],
        channels: Dict[int, StyleChannel]
    ) -> Dict[int, Dict]:
        """
        Оценить пакет постов (оптимизированная версия).

        Args:
            posts: Список постов
            channels: Словарь {channel_id: StyleChannel}

        Returns:
            {post_id: assessment_result}
        """
        results = {}

        async with AsyncSessionLocal() as session:
            for post in posts:
                channel = channels.get(post.channel_id)
                if not channel:
                    logger.warning(f"Channel {post.channel_id} not found for post {post.id}")
                    continue

                assessment = await self.assess_post(post, channel, session)
                results[post.id] = assessment

        return results
