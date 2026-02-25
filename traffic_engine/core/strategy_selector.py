"""
Strategy Selector — Thompson Sampling для выбора стратегии комментирования.

MAB (Multi-Armed Bandit) подход:
- Каждая стратегия (smart/supportive/funny/expert) = "рука"
- Reward = получил ответ (reply) или реакцию
- Thompson Sampling автоматически сдвигается к работающим стратегиям
- Начинает с равных шансов, учится на результатах

Таблица: traffic_strategy_effectiveness (см. миграцию 013)
"""

import random
from typing import Dict, Optional

from loguru import logger
from sqlalchemy import select

from traffic_engine.database import get_session
from traffic_engine.database.models import StrategyEffectiveness


class StrategySelector:
    """
    Thompson Sampling для выбора стратегии комментирования.

    Для каждого (segment, channel, strategy) хранит:
    - attempts: сколько раз пробовали
    - successes: сколько раз сработало (reply=1.0, reaction=0.5)
    - score: successes/attempts

    При выборе стратегии:
    1. Для каждой стратегии сэмплируем из Beta(successes+1, attempts-successes+1)
    2. Выбираем стратегию с максимальным сэмплом
    3. Это автоматически балансирует exploration vs exploitation
    """

    STRATEGIES = ["smart", "supportive", "funny", "expert"]

    def __init__(self):
        self._cache: Dict[str, Dict[str, tuple]] = {}  # key -> {strategy: (successes, attempts)}

    async def select_strategy(
        self,
        segment: Optional[str] = None,
        channel_username: Optional[str] = None,
    ) -> str:
        """
        Выбрать стратегию через Thompson Sampling.

        Args:
            segment: Сегмент аккаунта
            channel_username: Username канала

        Returns:
            Название стратегии (smart/supportive/funny/expert)
        """
        cache_key = f"{segment or 'any'}_{channel_username or 'any'}"

        # Загружаем данные из БД (или кэша)
        if cache_key not in self._cache:
            await self._load_stats(segment, channel_username)

        stats = self._cache.get(cache_key, {})

        # Thompson Sampling
        best_strategy = "smart"
        best_sample = -1

        for strategy in self.STRATEGIES:
            successes, attempts = stats.get(strategy, (0, 0))

            # Beta distribution sampling
            # Alpha = successes + 1, Beta = (attempts - successes) + 1
            alpha = successes + 1
            beta_param = max(1, attempts - successes + 1)

            sample = random.betavariate(alpha, beta_param)

            if sample > best_sample:
                best_sample = sample
                best_strategy = strategy

        logger.debug(
            f"Thompson Sampling [{cache_key}]: selected '{best_strategy}' "
            f"(sample={best_sample:.3f})"
        )
        return best_strategy

    async def record_result(
        self,
        strategy: str,
        got_reply: bool = False,
        got_reaction: bool = False,
        segment: Optional[str] = None,
        channel_username: Optional[str] = None,
        post_topic: Optional[str] = None,
    ) -> None:
        """
        Записать результат использования стратегии.

        Args:
            strategy: Использованная стратегия
            got_reply: Получили ответ на коммент
            got_reaction: Получили реакцию на коммент
            segment: Сегмент
            channel_username: Канал
            post_topic: Тема поста
        """
        # Вычисляем reward
        reward = 0.0
        if got_reply:
            reward += 1.0
        if got_reaction:
            reward += 0.5

        try:
            async with get_session() as session:
                # Ищем существующую запись
                result = await session.execute(
                    select(StrategyEffectiveness).where(
                        StrategyEffectiveness.segment == (segment or "any"),
                        StrategyEffectiveness.channel_username == channel_username,
                        StrategyEffectiveness.comment_strategy == strategy,
                    ).limit(1)
                )
                record = result.scalar_one_or_none()

                if record:
                    record.attempts += 1
                    record.successes += reward
                    record.score = record.successes / record.attempts if record.attempts > 0 else 0.5
                    from datetime import datetime, timezone
                    record.last_updated = datetime.now(timezone.utc)
                else:
                    record = StrategyEffectiveness(
                        segment=segment or "any",
                        channel_username=channel_username,
                        comment_strategy=strategy,
                        post_topic=post_topic,
                        attempts=1,
                        successes=reward,
                        score=reward,
                    )
                    session.add(record)

                await session.commit()

            # Инвалидируем кэш
            cache_key = f"{segment or 'any'}_{channel_username or 'any'}"
            self._cache.pop(cache_key, None)

        except Exception as e:
            logger.error(f"Failed to record strategy result: {e}")

    async def _load_stats(
        self,
        segment: Optional[str] = None,
        channel_username: Optional[str] = None,
    ) -> None:
        """Загрузить статистику из БД в кэш."""
        cache_key = f"{segment or 'any'}_{channel_username or 'any'}"

        try:
            async with get_session() as session:
                query = select(StrategyEffectiveness).where(
                    StrategyEffectiveness.segment == (segment or "any"),
                )
                if channel_username:
                    query = query.where(
                        StrategyEffectiveness.channel_username == channel_username
                    )

                result = await session.execute(query)
                records = result.scalars().all()

                stats = {}
                for record in records:
                    stats[record.comment_strategy] = (record.successes, record.attempts)

                self._cache[cache_key] = stats

        except Exception as e:
            logger.error(f"Failed to load strategy stats: {e}")
            self._cache[cache_key] = {}

    async def get_report(self, segment: Optional[str] = None) -> str:
        """
        Получить отчёт по эффективности стратегий.

        Returns:
            Форматированный текст отчёта
        """
        try:
            async with get_session() as session:
                query = select(StrategyEffectiveness).order_by(
                    StrategyEffectiveness.segment,
                    StrategyEffectiveness.score.desc(),
                )
                if segment:
                    query = query.where(StrategyEffectiveness.segment == segment)

                result = await session.execute(query)
                records = result.scalars().all()

            if not records:
                return "Нет данных по стратегиям (нужно больше комментов)"

            report = "🎯 <b>Эффективность стратегий</b>\n\n"
            current_segment = None

            for r in records:
                if r.segment != current_segment:
                    current_segment = r.segment
                    report += f"<b>[{current_segment}]</b>\n"

                score_bar = "█" * int(r.score * 10) + "░" * (10 - int(r.score * 10))
                report += (
                    f"  {r.comment_strategy}: {score_bar} "
                    f"{r.score:.0%} ({r.attempts} попыток)\n"
                )

            return report

        except Exception as e:
            logger.error(f"Failed to get strategy report: {e}")
            return f"Ошибка: {e}"
