"""
PerformanceAnalyzer — Contextual Bandit (LinUCB) + Pre-Publish Scoring.

Вдохновлено:
- Wayfair WayLift: contextual bandits для маркетинга
- EngageSense 2.0: гибридный скоринг (rules + statistics)
- arxiv 2411.13187: R = sqrt(quality * engagement)

Контекст = [hour, day_of_week, days_since_type, growth_rate].
Fallback: Thompson Sampling → random (при < 20 / < 5 постов).
"""
import math
import random
import re
from datetime import datetime, timedelta
from typing import Optional

import numpy as np
from loguru import logger
from sqlalchemy import select, func, and_

from shared.database.base import AsyncSessionLocal
from content_manager_bot.database.models import Post
from content_manager_bot.ai.style_dna import check_anti_ai_words


class ContentBandit:
    """Contextual Bandit (LinUCB) для выбора типа поста с учётом контекста."""

    def __init__(self, arms: list[str], d: int = 4):
        self.arms = arms
        self.d = d
        # LinUCB: A = I_d, b = 0_d для каждого arm
        self.A = {arm: np.eye(d) for arm in arms}
        self.b = {arm: np.zeros(d) for arm in arms}
        self._total_updates = 0

    def select(self, context: np.ndarray, alpha: float = 0.5) -> str:
        """Выбирает arm с учётом контекста (LinUCB)."""
        best_arm, best_ucb = None, -float('inf')
        for arm in self.arms:
            A_inv = np.linalg.inv(self.A[arm])
            theta = A_inv @ self.b[arm]
            ucb = float(theta @ context + alpha * np.sqrt(context @ A_inv @ context))
            if ucb > best_ucb:
                best_ucb = ucb
                best_arm = arm
        return best_arm

    def update(self, arm: str, context: np.ndarray, reward: float):
        """Обновляет модель после получения reward."""
        if arm not in self.A:
            return
        self.A[arm] += np.outer(context, context)
        self.b[arm] += reward * context
        self._total_updates += 1

    @property
    def total_updates(self) -> int:
        return self._total_updates


class PostScorer:
    """Оценка поста перед публикацией (0-100).

    Гибридный: rule-based (0-50) + statistical (0-50).
    """

    def __init__(self):
        self._historical_stats: Optional[dict] = None

    async def score(self, content: str, post_type: str, segment: str, hour: int) -> int:
        """Вычисляет score поста (0-100)."""
        rule = self._rule_score(content, post_type)
        stat = await self._statistical_score(post_type, segment, hour)
        total = max(0, min(100, rule + stat))
        logger.info(f"[DIRECTOR] PostScorer: rule={rule}, stat={stat}, total={total}")
        return total

    def _rule_score(self, content: str, post_type: str) -> int:
        """Rule-based scoring (0-50)."""
        score = 25  # базовый

        # Оптимальная длина (200-600 символов)
        length = len(content)
        if 200 <= length <= 600:
            score += 5
        elif length < 100 or length > 1000:
            score -= 5

        # Вопрос в конце
        last_100 = content[-100:] if len(content) > 100 else content
        if '?' in last_100:
            score += 5

        # Отсутствие AI-слов
        ai_words = check_anti_ai_words(content)
        if not ai_words:
            score += 5
        else:
            score -= len(ai_words) * 2

        # Наличие эмоции (мат, восклицание, многоточие)
        emotional_markers = ['!', '...', '—', 'бля', 'хуй', 'ебаш', 'пиздец', 'заебись']
        has_emotion = any(m in content.lower() for m in emotional_markers)
        if has_emotion:
            score += 5

        # Короткие абзацы (признак живого стиля)
        paragraphs = [p for p in content.split('\n') if p.strip()]
        if paragraphs:
            avg_para_len = sum(len(p) for p in paragraphs) / len(paragraphs)
            if avg_para_len < 150:
                score += 3

        # Разный ритм предложений
        sentences = re.split(r'[.!?]+', content)
        sentences = [s.strip() for s in sentences if s.strip()]
        if len(sentences) >= 3:
            lengths = [len(s) for s in sentences]
            variance = np.var(lengths)
            if variance > 200:  # большой разброс = хороший ритм
                score += 2

        return max(0, min(50, score))

    async def _statistical_score(self, post_type: str, segment: str, hour: int) -> int:
        """Statistical scoring (0-50) на основе исторических данных."""
        try:
            async with AsyncSessionLocal() as session:
                # Получаем средний engagement для этого типа + часа
                cutoff = datetime.utcnow() - timedelta(days=30)

                result = await session.execute(
                    select(func.avg(Post.engagement_rate)).where(
                        and_(
                            Post.status == "published",
                            Post.published_at >= cutoff,
                            Post.post_type == post_type,
                            Post.engagement_rate.isnot(None),
                        )
                    )
                )
                avg_engagement = result.scalar()

                if avg_engagement is None:
                    return 25  # нейтральный

                # Нормализуем: engagement_rate обычно 0-10%
                # 5%+ = отлично (50), 2-5% = хорошо (35), <2% = средне (20)
                if avg_engagement >= 5.0:
                    return 50
                elif avg_engagement >= 2.0:
                    return int(20 + (avg_engagement - 2.0) * 10)
                else:
                    return int(avg_engagement * 10)

        except Exception as e:
            logger.warning(f"[DIRECTOR] Statistical scoring failed: {e}")
            return 25


class PerformanceAnalyzer:
    """Анализатор производительности контента.

    Объединяет:
    - ContentBandit (LinUCB) для выбора типа поста
    - PostScorer для оценки перед публикацией
    - Reward = sqrt(quality * engagement)
    """

    # Типы постов для bandit
    POST_TYPES = ["observation", "question", "thought", "journey", "honesty", "absurd", "self_irony"]

    def __init__(self):
        self.bandit = ContentBandit(arms=self.POST_TYPES, d=4)
        self.scorer = PostScorer()
        self._initialized = False

    async def initialize(self):
        """Загружает историю из БД для инициализации bandit."""
        if self._initialized:
            return

        try:
            async with AsyncSessionLocal() as session:
                # Считаем общее число опубликованных постов
                result = await session.execute(
                    select(func.count(Post.id)).where(Post.status == "published")
                )
                total = result.scalar() or 0

                if total >= 20:
                    # Загружаем rewards для инициализации
                    posts = await session.execute(
                        select(
                            Post.post_type,
                            Post.published_at,
                            Post.engagement_rate,
                        ).where(
                            and_(
                                Post.status == "published",
                                Post.engagement_rate.isnot(None),
                                Post.published_at.isnot(None),
                            )
                        ).order_by(Post.published_at.desc()).limit(100)
                    )

                    for post_type, published_at, engagement_rate in posts.all():
                        if post_type not in self.POST_TYPES:
                            continue
                        context = self._build_context(
                            hour=published_at.hour if published_at else 12,
                            day_of_week=published_at.weekday() if published_at else 0,
                            days_since_type=1.0,
                            growth_rate=0.5,
                        )
                        # Reward из engagement
                        quality = 0.5  # default quality
                        engagement = min((engagement_rate or 0) / 10.0, 1.0)
                        reward = math.sqrt(quality * engagement)
                        self.bandit.update(post_type, context, reward)

                    logger.info(f"[DIRECTOR] Bandit initialized with {total} posts, {self.bandit.total_updates} updates")

            self._initialized = True

        except Exception as e:
            logger.warning(f"[DIRECTOR] Bandit initialization failed: {e}")
            self._initialized = True  # don't retry

    async def select_post_type(self, segment: Optional[str] = None) -> str:
        """Выбирает оптимальный тип поста с учётом контекста.

        Fallback chain: LinUCB → Thompson Sampling → random.
        """
        await self.initialize()

        now = datetime.utcnow()
        msk_hour = (now.hour + 3) % 24

        # Контекст
        days_since = await self._days_since_last_type(segment)
        context = self._build_context(
            hour=msk_hour,
            day_of_week=now.weekday(),
            days_since_type=1.0,  # будет обновлено для каждого arm
            growth_rate=0.5,
        )

        # Fallback: если мало данных — random
        if self.bandit.total_updates < 5:
            choice = random.choice(self.POST_TYPES)
            logger.info(f"[DIRECTOR] Random choice (cold start): {choice}")
            return choice

        # Fallback: Thompson Sampling для < 20 обновлений
        if self.bandit.total_updates < 20:
            choice = self._thompson_sampling(days_since)
            logger.info(f"[DIRECTOR] Thompson Sampling choice: {choice}")
            return choice

        # LinUCB выбор
        choice = self.bandit.select(context, alpha=0.5)
        logger.info(f"[DIRECTOR] LinUCB choice: {choice} (context: h={msk_hour}, d={now.weekday()})")
        return choice

    async def record_performance(self, post_type: str, quality_score: int, engagement_rate: float):
        """Записывает результат для обучения bandit."""
        await self.initialize()

        now = datetime.utcnow()
        context = self._build_context(
            hour=(now.hour + 3) % 24,
            day_of_week=now.weekday(),
            days_since_type=1.0,
            growth_rate=0.5,
        )

        # Reward = sqrt(quality * engagement)
        quality = quality_score / 100.0
        engagement = min(engagement_rate / 10.0, 1.0)
        reward = math.sqrt(max(0, quality * engagement))

        self.bandit.update(post_type, context, reward)
        logger.info(f"[DIRECTOR] Recorded: type={post_type}, quality={quality_score}, engagement={engagement_rate:.2f}%, reward={reward:.3f}")

    async def get_insights(self, segment: Optional[str] = None) -> str:
        """Возвращает текстовые insights для админа."""
        await self.initialize()

        try:
            async with AsyncSessionLocal() as session:
                # Средний engagement по типам за 30 дней
                cutoff = datetime.utcnow() - timedelta(days=30)
                result = await session.execute(
                    select(
                        Post.post_type,
                        func.avg(Post.engagement_rate),
                        func.count(Post.id),
                        func.avg(Post.views_count),
                    ).where(
                        and_(
                            Post.status == "published",
                            Post.published_at >= cutoff,
                            Post.engagement_rate.isnot(None),
                        )
                    ).group_by(Post.post_type)
                )

                rows = result.all()
                if not rows:
                    return "Недостаточно данных для аналитики (нужно хотя бы несколько опубликованных постов)."

                # Форматируем
                lines = ["📊 <b>Performance Insights (30 дней)</b>\n"]

                # Сортируем по engagement
                sorted_rows = sorted(rows, key=lambda r: r[1] or 0, reverse=True)

                for post_type, avg_eng, count, avg_views in sorted_rows:
                    avg_eng = avg_eng or 0
                    avg_views = avg_views or 0
                    bar = "█" * min(int(avg_eng * 2), 20) + "░" * max(0, 20 - min(int(avg_eng * 2), 20))
                    lines.append(
                        f"  {post_type}: {avg_eng:.1f}% [{bar}] ({count} постов, ~{int(avg_views)} просмотров)"
                    )

                # Лучший час
                hour_result = await session.execute(
                    select(
                        func.extract('hour', Post.published_at).label('hour'),
                        func.avg(Post.engagement_rate),
                    ).where(
                        and_(
                            Post.status == "published",
                            Post.published_at >= cutoff,
                            Post.engagement_rate.isnot(None),
                        )
                    ).group_by('hour').order_by(func.avg(Post.engagement_rate).desc()).limit(3)
                )
                best_hours = hour_result.all()
                if best_hours:
                    hours_str = ", ".join(f"{int(h + 3) % 24}:00 MSK ({e:.1f}%)" for h, e in best_hours)
                    lines.append(f"\n🕐 Лучшие часы: {hours_str}")

                # Рекомендация bandit
                recommended = await self.select_post_type(segment)
                lines.append(f"\n🎯 Рекомендуемый тип: <b>{recommended}</b>")

                return "\n".join(lines)

        except Exception as e:
            logger.error(f"[DIRECTOR] get_insights error: {e}")
            return f"Ошибка получения insights: {e}"

    def _build_context(self, hour: int, day_of_week: int, days_since_type: float, growth_rate: float) -> np.ndarray:
        """Строит вектор контекста для LinUCB."""
        return np.array([
            hour / 24.0,
            day_of_week / 7.0,
            min(days_since_type / 7.0, 1.0),
            min(max(growth_rate, 0.0), 1.0),
        ])

    async def _days_since_last_type(self, segment: Optional[str] = None) -> dict:
        """Возвращает дней с последнего поста каждого типа."""
        result = {}
        try:
            async with AsyncSessionLocal() as session:
                for pt in self.POST_TYPES:
                    query = select(func.max(Post.published_at)).where(
                        and_(Post.post_type == pt, Post.status == "published")
                    )
                    if segment:
                        query = query.where(Post.segment == segment)

                    res = await session.execute(query)
                    last_date = res.scalar()
                    if last_date:
                        result[pt] = (datetime.utcnow() - last_date).days
                    else:
                        result[pt] = 30  # never posted

        except Exception as e:
            logger.warning(f"[DIRECTOR] _days_since_last_type error: {e}")

        return result

    def _thompson_sampling(self, days_since: dict) -> str:
        """Thompson Sampling fallback — учитывает давность типа."""
        best_arm, best_sample = None, -1.0
        for arm in self.POST_TYPES:
            days = days_since.get(arm, 7)
            # Чем больше дней — тем выше alpha (больше шанс выбора)
            alpha = 1 + min(days, 14)
            beta = 2
            sample = random.betavariate(alpha, beta)
            if sample > best_sample:
                best_sample = sample
                best_arm = arm
        return best_arm or random.choice(self.POST_TYPES)


# Singleton
_analyzer: Optional[PerformanceAnalyzer] = None


def get_performance_analyzer() -> PerformanceAnalyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = PerformanceAnalyzer()
    return _analyzer
