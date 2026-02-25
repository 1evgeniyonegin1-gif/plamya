"""
Admin команды для управления мониторингом каналов-образцов
"""
from datetime import datetime, timedelta
from typing import Optional, List
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command, CommandObject
from loguru import logger
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from shared.config.settings import settings
from shared.database.base import AsyncSessionLocal
from shared.database.models import StyleChannel, StylePost
from shared.style_monitor import get_style_service

router = Router(name="channel_admin")


def is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь администратором"""
    return user_id in settings.admin_ids_list


# ============== КОМАНДА: /add_channel ==============

@router.message(Command("add_channel"))
async def cmd_add_channel(message: Message):
    """
    Добавить канал для мониторинга стиля.
    Формат: /add_channel @username [категория] [приоритет]
    Пример: /add_channel @motivational_channel motivation 8
    """
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет доступа к этой команде.")
        return

    args = message.text.split(maxsplit=3)

    if len(args) < 2:
        await message.answer(
            "📺 <b>Добавление канала-образца</b>\n\n"
            "<b>Формат:</b> /add_channel @username [категория] [приоритет]\n\n"
            "<b>Категории стиля:</b>\n"
            "• <code>motivation</code> — мотивационный контент\n"
            "• <code>product</code> — посты о продуктах\n"
            "• <code>lifestyle</code> — лайфстайл контент\n"
            "• <code>business</code> — бизнес-контент\n"
            "• <code>general</code> — общий стиль\n\n"
            "<b>Приоритет:</b> 1-10 (по умолчанию 5)\n\n"
            "<b>Пример:</b>\n"
            "<code>/add_channel @channel_name motivation 8</code>"
        )
        return

    username = args[1]
    category = args[2].lower() if len(args) > 2 else "general"

    try:
        priority = int(args[3]) if len(args) > 3 else 5
        priority = max(1, min(10, priority))  # Ограничиваем 1-10
    except ValueError:
        priority = 5

    status_msg = await message.answer(f"⏳ Добавляю канал {username}...")

    try:
        style_service = get_style_service()
        channel = await style_service.add_channel(
            username_or_id=username,
            style_category=category
        )

        if channel:
            # Обновляем приоритет
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(StyleChannel).where(StyleChannel.id == channel.id)
                )
                db_channel = result.scalar_one()
                db_channel.priority = priority
                await session.commit()

            emoji_cat = {
                "motivation": "💪",
                "product": "🛍️",
                "lifestyle": "🎨",
                "business": "💼",
                "general": "📺"
            }
            cat_emoji = emoji_cat.get(category, "📺")

            await status_msg.edit_text(
                f"✅ <b>Канал добавлен!</b>\n\n"
                f"📺 {channel.title}\n"
                f"🔗 {username}\n"
                f"{cat_emoji} Категория: <b>{category}</b>\n"
                f"⭐ Приоритет: {'⭐' * priority}\n\n"
                f"Используйте /list_channels чтобы увидеть все каналы.\n"
                f"Используйте /fetch_now для загрузки постов."
            )
        else:
            await status_msg.edit_text(
                f"❌ Не удалось добавить канал {username}\n\n"
                "<b>Возможные причины:</b>\n"
                "• Канал не существует\n"
                "• Канал приватный\n"
                "• Канал уже добавлен\n"
                "• Не настроены Telethon credentials\n\n"
                "Проверьте TELETHON_API_ID и TELETHON_API_HASH в .env"
            )

    except Exception as e:
        logger.error(f"Error adding channel: {e}")
        await status_msg.edit_text(
            f"❌ Ошибка при добавлении канала:\n\n"
            f"<code>{str(e)[:200]}</code>"
        )


# ============== КОМАНДА: /list_channels ==============

@router.message(Command("list_channels"))
async def cmd_list_channels(message: Message):
    """Показать список всех каналов с метриками"""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет доступа к этой команде.")
        return

    try:
        async with AsyncSessionLocal() as session:
            # Получаем все каналы
            result = await session.execute(
                select(StyleChannel)
                .where(StyleChannel.is_active == True)
                .order_by(StyleChannel.priority.desc(), StyleChannel.title)
            )
            channels = result.scalars().all()

        if not channels:
            await message.answer(
                "📭 <b>Нет активных каналов</b>\n\n"
                "Добавьте каналы командой:\n"
                "<code>/add_channel @username [категория] [приоритет]</code>"
            )
            return

        # Формируем список
        text = "📺 <b>КАНАЛЫ ДЛЯ МОНИТОРИНГА</b>\n\n"

        emoji_status = {
            "motivation": "💪",
            "product": "🛍️",
            "lifestyle": "🎨",
            "business": "💼",
            "general": "📺"
        }

        for channel in channels:
            # Статус кнопка
            status_emoji = "🟢" if channel.is_active else "🔴"
            cat_emoji = emoji_status.get(channel.style_category, "📺")

            text += f"{status_emoji} <b>{channel.title}</b>\n"

            # Username/ID
            if channel.username:
                text += f"   🔗 @{channel.username} (ID: {channel.channel_id})\n"
            else:
                text += f"   🔗 ID: {channel.channel_id}\n"

            # Категория и приоритет
            text += f"   {cat_emoji} Категория: {channel.style_category or 'general'}\n"
            text += f"   ⭐ Приоритет: {'⭐' * channel.priority}\n"

            # Статистика
            text += f"   📊 Постов: {channel.posts_count}\n"

            # Последняя загрузка
            if channel.last_fetched_at:
                last_fetch = channel.last_fetched_at.strftime('%d.%m %H:%M')
                text += f"   ⏱ Обновлено: {last_fetch}\n"
            else:
                text += f"   ⏱ Не обновлялся\n"

            text += "\n"

        text += f"<i>Всего каналов: {len(channels)}</i>"

        await message.answer(text)

    except Exception as e:
        logger.error(f"Error listing channels: {e}")
        await message.answer(
            f"❌ Ошибка при получении списка каналов:\n\n"
            f"<code>{str(e)[:200]}</code>"
        )


# ============== КОМАНДА: /toggle_channel ==============

@router.message(Command("toggle_channel"))
async def cmd_toggle_channel(message: Message):
    """
    Включить/выключить канал.
    Формат: /toggle_channel <id>
    """
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет доступа к этой команде.")
        return

    args = message.text.split(maxsplit=1)

    if len(args) < 2:
        await message.answer(
            "Формат: /toggle_channel <channel_id>\n\n"
            "Используйте /list_channels чтобы увидеть ID каналов."
        )
        return

    try:
        channel_id = int(args[1])

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(StyleChannel).where(StyleChannel.id == channel_id)
            )
            channel = result.scalar_one_or_none()

            if not channel:
                await message.answer(f"❌ Канал с ID {channel_id} не найден")
                return

            # Переключаем активность
            channel.is_active = not channel.is_active
            await session.commit()

            status = "✅ включен" if channel.is_active else "⛔ выключен"
            await message.answer(
                f"{status}\n\n"
                f"📺 <b>{channel.title}</b>"
            )

    except ValueError:
        await message.answer("❌ Неверный формат ID канала (должно быть число)")
    except Exception as e:
        logger.error(f"Error toggling channel: {e}")
        await message.answer(
            f"❌ Ошибка при изменении канала:\n\n"
            f"<code>{str(e)[:200]}</code>"
        )


# ============== КОМАНДА: /fetch_now ==============

@router.message(Command("fetch_now"))
async def cmd_fetch_now(message: Message):
    """
    Принудительная загрузка постов из канала.
    Формат: /fetch_now [channel_id] - загрузить один канал или все
    """
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет доступа к этой команде.")
        return

    args = message.text.split(maxsplit=1)
    channel_id = None

    if len(args) > 1:
        try:
            channel_id = int(args[1])
        except ValueError:
            await message.answer("❌ Неверный формат ID канала (должно быть число)")
            return

    status_msg = await message.answer(
        f"⏳ Загружаю посты{'из канала ' + str(channel_id) if channel_id else 'из всех каналов'}..."
    )

    try:
        style_service = get_style_service()

        if channel_id:
            # Загружаем из одного канала
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(StyleChannel).where(StyleChannel.id == channel_id)
                )
                channel = result.scalar_one_or_none()

                if not channel:
                    await status_msg.edit_text(f"❌ Канал с ID {channel_id} не найден")
                    return

            stats = await style_service.fetch_channel(channel_id, limit=50)

            await status_msg.edit_text(
                f"✅ <b>Загрузка завершена!</b>\n\n"
                f"📺 {channel.title}\n"
                f"📝 Новых постов: {stats['new_posts']}\n"
                f"📊 Всего в БД: {stats['total_posts']}\n\n"
                f"Используйте /channel_stats {channel_id} для детальной информации"
            )
        else:
            # Загружаем из всех каналов
            stats = await style_service.fetch_all_channels(limit_per_channel=50)

            await status_msg.edit_text(
                f"✅ <b>Загрузка завершена!</b>\n\n"
                f"📺 Обработано каналов: {stats['channels_processed']}\n"
                f"📝 Новых постов: {stats['total_new_posts']}\n"
                f"📊 Всего в БД: {stats.get('total_posts', 'N/A')}\n\n"
                f"{'⚠️ Есть ошибки при загрузке' if stats.get('errors') else '✅ Без ошибок'}"
            )

    except Exception as e:
        logger.error(f"Error fetching posts: {e}")
        await status_msg.edit_text(
            f"❌ Ошибка при загрузке постов:\n\n"
            f"<code>{str(e)[:200]}</code>"
        )


# ============== КОМАНДА: /channel_stats ==============

@router.message(Command("channel_stats"))
async def cmd_channel_stats(message: Message):
    """
    Детальная статистика по каналу.
    Формат: /channel_stats <id>
    """
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет доступа к этой команде.")
        return

    args = message.text.split(maxsplit=1)

    if len(args) < 2:
        await message.answer(
            "Формат: /channel_stats <channel_id>\n\n"
            "Используйте /list_channels чтобы увидеть ID каналов."
        )
        return

    try:
        channel_id = int(args[1])

        async with AsyncSessionLocal() as session:
            # Получаем канал
            result = await session.execute(
                select(StyleChannel).where(StyleChannel.id == channel_id)
            )
            channel = result.scalar_one_or_none()

            if not channel:
                await message.answer(f"❌ Канал с ID {channel_id} не найден")
                return

            # Получаем статистику по постам
            posts_result = await session.execute(
                select(StylePost)
                .where(StylePost.channel_id == channel_id)
                .order_by(StylePost.post_date.desc())
                .limit(1)
            )
            latest_post = posts_result.scalar_one_or_none()

            # Статистика по датам
            posts_count_result = await session.execute(
                select(func.count(StylePost.id))
                .where(StylePost.channel_id == channel_id)
            )
            total_posts = posts_count_result.scalar() or 0

            # Статистика за последние 7 дней
            week_ago = datetime.utcnow() - timedelta(days=7)
            week_result = await session.execute(
                select(func.count(StylePost.id))
                .where(
                    StylePost.channel_id == channel_id,
                    StylePost.post_date >= week_ago
                )
            )
            posts_last_week = week_result.scalar() or 0

            # Статистика по наличию медиа
            media_result = await session.execute(
                select(func.count(StylePost.id))
                .where(
                    StylePost.channel_id == channel_id,
                    StylePost.has_media == True
                )
            )
            posts_with_media = media_result.scalar() or 0

            # Средние просмотры
            views_avg_result = await session.execute(
                select(func.avg(StylePost.views_count))
                .where(StylePost.channel_id == channel_id)
            )
            avg_views = views_avg_result.scalar() or 0

            emoji_cat = {
                "motivation": "💪",
                "product": "🛍️",
                "lifestyle": "🎨",
                "business": "💼",
                "general": "📺"
            }
            cat_emoji = emoji_cat.get(channel.style_category, "📺")

        # Формируем ответ
        text = f"📊 <b>СТАТИСТИКА КАНАЛА</b>\n\n"
        text += f"📺 <b>{channel.title}</b>\n"

        if channel.username:
            text += f"🔗 @{channel.username}\n"
        else:
            text += f"🔗 ID: {channel.channel_id}\n"

        text += f"{cat_emoji} Категория: {channel.style_category or 'general'}\n"
        text += f"⭐ Приоритет: {'⭐' * channel.priority}\n"
        text += f"{'🟢' if channel.is_active else '🔴'} Статус: {'активен' if channel.is_active else 'отключен'}\n\n"

        text += "<b>📈 МЕТРИКИ:</b>\n"
        text += f"• Всего постов: <b>{total_posts}</b>\n"
        text += f"• За последние 7 дней: <b>{posts_last_week}</b>\n"
        text += f"• С медиа: <b>{posts_with_media}</b> ({100*posts_with_media//total_posts if total_posts else 0}%)\n"
        text += f"• Средние просмотры: <b>{int(avg_views)}</b>\n\n"

        if channel.last_fetched_at:
            text += f"⏱ Последнее обновление: {channel.last_fetched_at.strftime('%d.%m.%Y %H:%M:%S')}\n"

        if latest_post:
            text += f"📅 Последний пост: {latest_post.post_date.strftime('%d.%m.%Y %H:%M')}\n"

        await message.answer(text)

    except ValueError:
        await message.answer("❌ Неверный формат ID канала (должно быть число)")
    except Exception as e:
        logger.error(f"Error getting channel stats: {e}")
        await message.answer(
            f"❌ Ошибка при получении статистики:\n\n"
            f"<code>{str(e)[:200]}</code>"
        )


# ============== ДОПОЛНИТЕЛЬНЫЕ УТИЛИТЫ ==============

@router.message(Command("remove_channel"))
async def cmd_remove_channel(message: Message):
    """
    Удалить канал из мониторинга.
    Формат: /remove_channel <id>
    """
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет доступа к этой команде.")
        return

    args = message.text.split(maxsplit=1)

    if len(args) < 2:
        await message.answer(
            "Формат: /remove_channel <channel_id>\n\n"
            "Используйте /list_channels чтобы увидеть ID каналов.\n\n"
            "⚠️ Внимание: это удалит канал и все его посты!"
        )
        return

    try:
        channel_id = int(args[1])

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(StyleChannel).where(StyleChannel.id == channel_id)
            )
            channel = result.scalar_one_or_none()

            if not channel:
                await message.answer(f"❌ Канал с ID {channel_id} не найден")
                return

            title = channel.title
            await session.delete(channel)
            await session.commit()

        await message.answer(
            f"✅ <b>Канал удалён!</b>\n\n"
            f"📺 {title}"
        )

    except ValueError:
        await message.answer("❌ Неверный формат ID канала (должно быть число)")
    except Exception as e:
        logger.error(f"Error removing channel: {e}")
        await message.answer(
            f"❌ Ошибка при удалении канала:\n\n"
            f"<code>{str(e)[:200]}</code>"
        )


__all__ = ["router"]
