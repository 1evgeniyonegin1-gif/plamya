"""
Менеджер серийного контента (cliffhangers и продолжения).

Управляет созданием и продолжением серий постов:
- Начало серии (series_intro) с интригой
- Продолжение (series_continue) с новым cliffhanger
- Финал (series_finale) с payoff

Добавлено 03.02.2026 по плану улучшения контента.
"""
from typing import Optional, Tuple, List
from datetime import datetime
from loguru import logger

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.base import AsyncSessionLocal
from content_manager_bot.database.models import ContentSeries, Post


# Темы для серий (из prompts.py SERIES_TOPICS)
SERIES_TOPICS = [
    {
        "title": "Как я потерял всё и начал заново",
        "topic": "История провала и возрождения в бизнесе",
        "character": "Данил",
        "parts": 3
    },
    {
        "title": "3 ошибки которые стоили мне года",
        "topic": "Ошибки новичка в сетевом бизнесе",
        "character": "Артём",  # Скептик
        "parts": 3
    },
    {
        "title": "Почему я ушла с работы в 45 лет",
        "topic": "История женщины которая рискнула",
        "character": "Валентина Петровна",
        "parts": 3
    },
    {
        "title": "Моя первая продажа — это был кошмар",
        "topic": "Первый опыт продаж и уроки",
        "character": "Маша",  # Новичок
        "parts": 3
    },
    {
        "title": "Что случилось когда я показал чек жене",
        "topic": "Семья и сетевой бизнес",
        "character": "Олег",  # Бизнесмен
        "parts": 3
    },
    {
        "title": "Клиент который изменил моё отношение к делу",
        "topic": "История одного клиента",
        "character": None,
        "parts": 3
    },
    {
        "title": "Месяц без результатов — и вот что произошло",
        "topic": "Преодоление плато в бизнесе",
        "character": "Данил",
        "parts": 3
    },
    {
        "title": "Секрет который мне рассказал топ-партнёр",
        "topic": "Инсайт от успешного партнёра",
        "character": None,
        "parts": 3
    },
]


class SeriesManager:
    """
    Управляет сериями постов с продолжением.

    Функции:
    - Создание новой серии
    - Получение активной серии для продолжения
    - Генерация следующей части серии
    - Отслеживание состояния серий
    """

    def __init__(self):
        self._active_series_cache: Optional[ContentSeries] = None

    async def get_active_series(self) -> Optional[ContentSeries]:
        """
        Получает активную незавершённую серию.

        Returns:
            ContentSeries или None если нет активных серий
        """
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(ContentSeries)
                    .where(ContentSeries.status == "active")
                    .order_by(ContentSeries.created_at.desc())
                    .limit(1)
                )
                series = result.scalar_one_or_none()

                if series:
                    logger.info(f"[SERIES] Найдена активная серия: {series.title} (часть {series.current_part}/{series.total_parts})")
                    self._active_series_cache = series
                    return series

                return None

        except Exception as e:
            logger.error(f"[SERIES] Ошибка получения активной серии: {e}")
            return None

    async def create_series(
        self,
        title: Optional[str] = None,
        topic: Optional[str] = None,
        character: Optional[str] = None,
        total_parts: int = 3
    ) -> ContentSeries:
        """
        Создаёт новую серию постов.

        Args:
            title: Название серии (если None — выбирается случайно)
            topic: Тема серии
            character: Персонаж серии (recurring character)
            total_parts: Количество частей

        Returns:
            Созданная серия
        """
        import random

        # Если параметры не заданы — выбираем случайную тему
        if not title or not topic:
            template = random.choice(SERIES_TOPICS)
            title = title or template["title"]
            topic = topic or template["topic"]
            character = character or template.get("character")
            total_parts = template.get("parts", 3)

        try:
            async with AsyncSessionLocal() as session:
                series = ContentSeries(
                    title=title,
                    topic=topic,
                    character=character,
                    total_parts=total_parts,
                    current_part=0,
                    status="draft",
                    post_ids=[]
                )
                session.add(series)
                await session.commit()
                await session.refresh(series)

                logger.info(f"[SERIES] Создана серия: {series.title} ({series.total_parts} частей)")
                return series

        except Exception as e:
            logger.error(f"[SERIES] Ошибка создания серии: {e}")
            raise

    async def start_series(self, series_id: int) -> ContentSeries:
        """
        Начинает серию (меняет статус на active).

        Args:
            series_id: ID серии

        Returns:
            Обновлённая серия
        """
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(ContentSeries).where(ContentSeries.id == series_id)
                )
                series = result.scalar_one_or_none()

                if not series:
                    raise ValueError(f"Серия {series_id} не найдена")

                series.status = "active"
                series.started_at = datetime.utcnow()
                await session.commit()
                await session.refresh(series)

                logger.info(f"[SERIES] Серия запущена: {series.title}")
                return series

        except Exception as e:
            logger.error(f"[SERIES] Ошибка запуска серии: {e}")
            raise

    async def advance_series(
        self,
        series_id: int,
        post_id: int,
        cliffhanger: Optional[str] = None,
        context_update: Optional[str] = None
    ) -> Tuple[ContentSeries, str]:
        """
        Продвигает серию вперёд после публикации поста.

        Args:
            series_id: ID серии
            post_id: ID опубликованного поста
            cliffhanger: Cliffhanger из поста (для следующей части)
            context_update: Обновление контекста (что произошло в этой части)

        Returns:
            Tuple[ContentSeries, str]: (обновлённая серия, тип следующего поста или "completed")
        """
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(ContentSeries).where(ContentSeries.id == series_id)
                )
                series = result.scalar_one_or_none()

                if not series:
                    raise ValueError(f"Серия {series_id} не найдена")

                # Обновляем данные серии
                series.current_part += 1

                # Добавляем post_id в список
                post_ids = series.post_ids or []
                post_ids.append(post_id)
                series.post_ids = post_ids

                # Обновляем контекст
                if context_update:
                    current_context = series.context_summary or ""
                    series.context_summary = f"{current_context}\n\nЧасть {series.current_part}: {context_update}".strip()

                # Сохраняем cliffhanger для следующей части
                if cliffhanger:
                    series.last_cliffhanger = cliffhanger

                # Проверяем завершение
                if series.is_complete():
                    series.status = "completed"
                    series.completed_at = datetime.utcnow()
                    next_type = "completed"
                    logger.info(f"[SERIES] Серия завершена: {series.title}")
                else:
                    next_type = series.next_post_type()
                    logger.info(f"[SERIES] Серия продвинута: {series.title} → часть {series.current_part}/{series.total_parts}")

                await session.commit()
                await session.refresh(series)

                return series, next_type

        except Exception as e:
            logger.error(f"[SERIES] Ошибка продвижения серии: {e}")
            raise

    async def get_series_context(self, series_id: int) -> dict:
        """
        Получает контекст серии для генерации следующего поста.

        Args:
            series_id: ID серии

        Returns:
            dict с контекстом для промпта
        """
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(ContentSeries).where(ContentSeries.id == series_id)
                )
                series = result.scalar_one_or_none()

                if not series:
                    return {}

                return {
                    "series_id": series.id,
                    "title": series.title,
                    "topic": series.topic,
                    "character": series.character,
                    "current_part": series.current_part + 1,  # Следующая часть
                    "total_parts": series.total_parts,
                    "is_intro": series.current_part == 0,
                    "is_finale": series.current_part == series.total_parts - 1,
                    "previous_context": series.context_summary,
                    "last_cliffhanger": series.last_cliffhanger,
                    "post_type": series.next_post_type()
                }

        except Exception as e:
            logger.error(f"[SERIES] Ошибка получения контекста: {e}")
            return {}

    async def cancel_series(self, series_id: int) -> bool:
        """
        Отменяет серию.

        Args:
            series_id: ID серии

        Returns:
            True если успешно
        """
        try:
            async with AsyncSessionLocal() as session:
                await session.execute(
                    update(ContentSeries)
                    .where(ContentSeries.id == series_id)
                    .values(status="cancelled")
                )
                await session.commit()

                logger.info(f"[SERIES] Серия {series_id} отменена")
                return True

        except Exception as e:
            logger.error(f"[SERIES] Ошибка отмены серии: {e}")
            return False

    async def get_all_series(self, status: Optional[str] = None, limit: int = 10) -> List[ContentSeries]:
        """
        Получает список серий.

        Args:
            status: Фильтр по статусу (draft, active, completed, cancelled)
            limit: Максимум записей

        Returns:
            Список серий
        """
        try:
            async with AsyncSessionLocal() as session:
                query = select(ContentSeries).order_by(ContentSeries.created_at.desc()).limit(limit)

                if status:
                    query = query.where(ContentSeries.status == status)

                result = await session.execute(query)
                return list(result.scalars().all())

        except Exception as e:
            logger.error(f"[SERIES] Ошибка получения списка серий: {e}")
            return []

    def build_series_prompt_addition(self, context: dict) -> str:
        """
        Создаёт дополнение к промпту для генерации поста серии.

        Args:
            context: Контекст серии из get_series_context()

        Returns:
            str: Дополнение к промпту
        """
        if not context:
            return ""

        parts = []

        parts.append(f"""
═══════════════════════════════════════════
📖 ЭТО ЧАСТЬ СЕРИИ ПОСТОВ
═══════════════════════════════════════════

СЕРИЯ: "{context.get('title', 'Без названия')}"
ТЕМА: {context.get('topic', '')}
ЧАСТЬ: {context.get('current_part', 1)} из {context.get('total_parts', 3)}
""")

        # Персонаж
        if context.get('character'):
            parts.append(f"ПЕРСОНАЖ: {context['character']} (recurring character — упоминай его по имени!)")

        # Контекст предыдущих частей
        if context.get('previous_context'):
            parts.append(f"""
ЧТО БЫЛО РАНЬШЕ:
{context['previous_context']}
""")

        # Cliffhanger для продолжения
        if context.get('last_cliffhanger') and not context.get('is_intro'):
            parts.append(f"""
ПРЕДЫДУЩИЙ CLIFFHANGER (раскрой его!):
"{context['last_cliffhanger']}"
""")

        # Инструкции по типу части
        if context.get('is_intro'):
            parts.append("""
ТИП: НАЧАЛО СЕРИИ
• Создай интригу и задай вопрос
• Заверши CLIFFHANGER — "продолжение завтра"
• НЕ раскрывай всё сразу!
""")
        elif context.get('is_finale'):
            parts.append("""
ТИП: ФИНАЛ СЕРИИ
• Раскрой все загадки
• Подведи итог истории
• Дай конкретный урок/вывод
• CTA уместен
""")
        else:
            parts.append("""
ТИП: ПРОДОЛЖЕНИЕ
• Раскрой предыдущий cliffhanger
• Развей историю дальше
• Создай НОВЫЙ cliffhanger в конце
""")

        parts.append("═══════════════════════════════════════════")

        return "\n".join(parts)


# Синглтон для удобства
_series_manager: Optional[SeriesManager] = None


def get_series_manager() -> SeriesManager:
    """Получает синглтон SeriesManager"""
    global _series_manager
    if _series_manager is None:
        _series_manager = SeriesManager()
    return _series_manager
