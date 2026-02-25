"""
Сервис для сбора постов из каналов-образцов через Telethon.
"""
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, AsyncGenerator

from telethon import TelegramClient
from telethon.tl.types import Channel, Message
from telethon.errors import ChannelPrivateError, UsernameNotOccupiedError

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from shared.config.settings import settings
from shared.database.base import AsyncSessionLocal
from shared.database.models import StyleChannel, StylePost
from shared.utils.logger import get_logger

logger = get_logger(__name__)


class ChannelFetcher:
    """
    Сервис для мониторинга и сбора постов из Telegram каналов.

    Использует Telethon для доступа к публичным каналам.
    """

    def __init__(self):
        self._client: Optional[TelegramClient] = None
        self._is_connected = False

    @property
    def is_configured(self) -> bool:
        """Проверяет настроены ли Telethon credentials."""
        return bool(settings.telethon_api_id and settings.telethon_api_hash)

    async def connect(self) -> bool:
        """
        Подключиться к Telegram через Telethon.

        Returns:
            True если подключение успешно
        """
        if not self.is_configured:
            logger.warning("Telethon не настроен: отсутствуют API_ID или API_HASH")
            return False

        if self._is_connected and self._client:
            return True

        try:
            self._client = TelegramClient(
                settings.telethon_session_name,
                settings.telethon_api_id,
                settings.telethon_api_hash
            )
            await self._client.start()
            self._is_connected = True
            logger.info("Telethon клиент подключён")
            return True
        except Exception as e:
            logger.error(f"Ошибка подключения Telethon: {e}")
            return False

    async def disconnect(self):
        """Отключиться от Telegram."""
        if self._client:
            await self._client.disconnect()
            self._is_connected = False
            logger.info("Telethon клиент отключён")

    async def resolve_channel(self, username_or_id: str) -> Optional[dict]:
        """
        Получить информацию о канале по username или ID.

        Args:
            username_or_id: @username или числовой ID канала

        Returns:
            dict с информацией о канале или None
        """
        if not await self.connect():
            return None

        try:
            entity = await self._client.get_entity(username_or_id)
            if isinstance(entity, Channel):
                return {
                    "channel_id": entity.id,
                    "username": entity.username,
                    "title": entity.title,
                    "participants_count": getattr(entity, 'participants_count', None)
                }
            else:
                logger.warning(f"Entity не является каналом: {type(entity)}")
                return None
        except UsernameNotOccupiedError:
            logger.error(f"Канал не найден: {username_or_id}")
            return None
        except ChannelPrivateError:
            logger.error(f"Канал приватный: {username_or_id}")
            return None
        except Exception as e:
            logger.error(f"Ошибка при получении канала {username_or_id}: {e}")
            return None

    async def fetch_posts(
        self,
        channel_id: int,
        limit: int = 50,
        min_date: Optional[datetime] = None
    ) -> List[dict]:
        """
        Получить последние посты из канала.

        Args:
            channel_id: ID канала в Telegram
            limit: Максимальное количество постов
            min_date: Минимальная дата поста (не загружать старее)

        Returns:
            Список постов с текстом и метаданными
        """
        if not await self.connect():
            return []

        posts = []
        try:
            async for message in self._client.iter_messages(
                channel_id,
                limit=limit,
                offset_date=None,
                reverse=False
            ):
                if not isinstance(message, Message):
                    continue

                # Пропускаем посты старше min_date
                if min_date and message.date.replace(tzinfo=None) < min_date.replace(tzinfo=None):
                    break

                # Пропускаем посты без текста
                if not message.text:
                    continue

                # Определяем тип медиа
                media_type = None
                has_media = False
                if message.media:
                    has_media = True
                    media_type = type(message.media).__name__.replace("MessageMedia", "").lower()

                posts.append({
                    "message_id": message.id,
                    "text": message.text,
                    "post_date": message.date,
                    "has_media": has_media,
                    "media_type": media_type,
                    "views_count": message.views,
                    "forwards_count": message.forwards,
                    "reactions_count": sum(
                        r.count for r in (message.reactions.results if message.reactions else [])
                    ) if message.reactions else None
                })

            logger.info(f"Получено {len(posts)} постов из канала {channel_id}")
            return posts

        except ChannelPrivateError:
            logger.error(f"Канал {channel_id} приватный")
            return []
        except Exception as e:
            logger.error(f"Ошибка при получении постов из канала {channel_id}: {e}")
            return []


class StyleChannelService:
    """
    Сервис для управления каналами-образцами и их постами.
    """

    def __init__(self):
        self.fetcher = ChannelFetcher()

    async def add_channel(
        self,
        username_or_id: str,
        description: str = None,
        style_category: str = None,
        priority: int = 1
    ) -> Optional[StyleChannel]:
        """
        Добавить канал для мониторинга.

        Args:
            username_or_id: @username или ID канала
            description: Описание канала
            style_category: Категория стиля
            priority: Приоритет (1-10)

        Returns:
            Созданный StyleChannel или None при ошибке
        """
        # Получаем информацию о канале
        channel_info = await self.fetcher.resolve_channel(username_or_id)
        if not channel_info:
            return None

        async with AsyncSessionLocal() as session:
            # Проверяем не добавлен ли уже
            existing = await session.execute(
                select(StyleChannel).where(StyleChannel.channel_id == channel_info["channel_id"])
            )
            if existing.scalar_one_or_none():
                logger.warning(f"Канал уже добавлен: {channel_info['title']}")
                return None

            # Создаём запись
            channel = StyleChannel(
                channel_id=channel_info["channel_id"],
                username=channel_info["username"],
                title=channel_info["title"],
                description=description,
                style_category=style_category,
                priority=priority
            )
            session.add(channel)
            await session.commit()
            await session.refresh(channel)

            logger.info(f"Добавлен канал для мониторинга: {channel.title}")
            return channel

    async def remove_channel(self, channel_id: int) -> bool:
        """Удалить канал из мониторинга."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(StyleChannel).where(StyleChannel.channel_id == channel_id)
            )
            channel = result.scalar_one_or_none()
            if channel:
                await session.delete(channel)
                await session.commit()
                logger.info(f"Канал удалён: {channel.title}")
                return True
            return False

    async def get_active_channels(self) -> List[StyleChannel]:
        """Получить список активных каналов."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(StyleChannel)
                .where(StyleChannel.is_active == True)
                .order_by(StyleChannel.priority.desc())
            )
            return list(result.scalars().all())

    async def fetch_and_save_posts(
        self,
        channel: StyleChannel,
        limit: int = 50,
        days_back: int = 30
    ) -> int:
        """
        Загрузить и сохранить посты из канала.

        Args:
            channel: Канал для загрузки
            limit: Максимум постов
            days_back: За сколько дней загружать

        Returns:
            Количество новых постов
        """
        min_date = datetime.now() - timedelta(days=days_back)

        # Получаем посты из Telegram
        posts = await self.fetcher.fetch_posts(
            channel.channel_id,
            limit=limit,
            min_date=min_date
        )

        if not posts:
            return 0

        new_posts = 0
        async with AsyncSessionLocal() as session:
            for post_data in posts:
                # Проверяем не сохранён ли уже
                existing = await session.execute(
                    select(StylePost).where(
                        StylePost.channel_id == channel.id,
                        StylePost.message_id == post_data["message_id"]
                    )
                )
                if existing.scalar_one_or_none():
                    continue

                # Создаём запись
                post = StylePost(
                    channel_id=channel.id,
                    message_id=post_data["message_id"],
                    text=post_data["text"],
                    post_date=post_data["post_date"],
                    has_media=post_data["has_media"],
                    media_type=post_data["media_type"],
                    views_count=post_data["views_count"],
                    forwards_count=post_data["forwards_count"],
                    reactions_count=post_data["reactions_count"]
                )
                session.add(post)
                new_posts += 1

            # Обновляем статистику канала
            channel_record = await session.get(StyleChannel, channel.id)
            if channel_record:
                channel_record.last_fetched_at = datetime.now()
                channel_record.posts_count = await self._count_posts(session, channel.id)
                if posts:
                    channel_record.last_post_date = max(p["post_date"] for p in posts)

            await session.commit()

        logger.info(f"Сохранено {new_posts} новых постов из канала {channel.title}")
        return new_posts

    async def _count_posts(self, session: AsyncSession, channel_id: int) -> int:
        """Подсчитать количество постов канала."""
        result = await session.execute(
            select(func.count(StylePost.id)).where(StylePost.channel_id == channel_id)
        )
        return result.scalar() or 0

    async def fetch_all_channels(self, limit_per_channel: int = 30) -> dict:
        """
        Загрузить посты из всех активных каналов.

        Returns:
            Статистика загрузки
        """
        channels = await self.get_active_channels()
        stats = {
            "channels_processed": 0,
            "total_new_posts": 0,
            "errors": []
        }

        for channel in channels:
            try:
                new_posts = await self.fetch_and_save_posts(channel, limit=limit_per_channel)
                stats["channels_processed"] += 1
                stats["total_new_posts"] += new_posts
            except Exception as e:
                logger.error(f"Ошибка при загрузке канала {channel.title}: {e}")
                stats["errors"].append(f"{channel.title}: {str(e)}")

        return stats

    async def get_style_samples(
        self,
        style_category: str = None,
        limit: int = 10,
        min_quality: int = None
    ) -> List[StylePost]:
        """
        Получить образцы постов для генерации контента.

        Args:
            style_category: Фильтр по категории
            limit: Максимум постов
            min_quality: Минимальная оценка качества

        Returns:
            Список постов-образцов
        """
        async with AsyncSessionLocal() as session:
            query = (
                select(StylePost)
                .join(StyleChannel)
                .where(StyleChannel.is_active == True)
            )

            if style_category:
                query = query.where(StyleChannel.style_category == style_category)

            if min_quality is not None:
                query = query.where(StylePost.quality_score >= min_quality)

            # Сортируем по качеству и дате
            query = query.order_by(
                StylePost.quality_score.desc().nullslast(),
                StylePost.post_date.desc()
            ).limit(limit)

            result = await session.execute(query)
            return list(result.scalars().all())

    async def disconnect(self):
        """Отключить Telethon клиент."""
        await self.fetcher.disconnect()


# Глобальный экземпляр сервиса
_style_service: Optional[StyleChannelService] = None


def get_style_service() -> StyleChannelService:
    """Получить глобальный экземпляр StyleChannelService."""
    global _style_service
    if _style_service is None:
        _style_service = StyleChannelService()
    return _style_service
