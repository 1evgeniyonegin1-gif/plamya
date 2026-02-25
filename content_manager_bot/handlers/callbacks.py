"""
Обработчики callback-кнопок
"""
import asyncio
from datetime import datetime, timedelta
from typing import List
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from loguru import logger
from sqlalchemy import select, func

from shared.config.settings import settings
from shared.database.base import AsyncSessionLocal
from content_manager_bot.ai.content_generator import ContentGenerator
from content_manager_bot.database.models import Post, AdminAction, ContentSchedule
from content_manager_bot.database.funnel_models import ChannelTier
from content_manager_bot.utils.keyboards import Keyboards
from content_manager_bot.handlers.admin import is_admin, generate_and_show_post
from content_manager_bot.scheduler.content_scheduler import ContentScheduler
from content_manager_bot.routing.channel_router import ChannelRouter
from content_manager_bot.director import get_reflection_engine, get_channel_memory

router = Router()


def split_post_to_messages(text: str, max_length: int = 1000) -> List[str]:
    """
    Разбивает длинный пост на несколько сообщений.
    Разделяет по абзацам, не по символам.

    Args:
        text: Текст поста
        max_length: Максимальная длина одного сообщения

    Returns:
        List[str]: Список частей сообщения
    """
    if len(text) <= max_length:
        return [text]

    messages = []
    current = ""

    for paragraph in text.split('\n\n'):
        # Если параграф сам по себе слишком длинный — разбиваем по строкам
        if len(paragraph) > max_length:
            if current:
                messages.append(current.strip())
                current = ""
            # Разбиваем по строкам
            for line in paragraph.split('\n'):
                if len(current) + len(line) + 1 <= max_length:
                    current += ('\n' if current else '') + line
                else:
                    if current:
                        messages.append(current.strip())
                    current = line
        elif len(current) + len(paragraph) + 2 <= max_length:
            current += ('\n\n' if current else '') + paragraph
        else:
            if current:
                messages.append(current.strip())
            current = paragraph

    if current:
        messages.append(current.strip())

    return messages

# Инициализируем генератор контента
content_generator = ContentGenerator()


class EditPostStates(StatesGroup):
    """Состояния для редактирования поста"""
    waiting_for_edit = State()
    waiting_for_feedback = State()
    waiting_for_custom_time = State()
    waiting_for_manual_edit = State()  # Ручное редактирование текста


# === Генерация по типу ===

@router.callback_query(F.data.startswith("gen_type:"))
async def callback_generate_by_type(callback: CallbackQuery):
    """Обработка выбора типа поста для генерации"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    # Сразу отвечаем пользователю что началась генерация
    await callback.answer("⏳ Генерирую пост...", show_alert=False)

    post_type = callback.data.split(":")[1]

    await callback.message.edit_text(
        f"⏳ Генерирую пост типа: {post_type}...\n"
        f"<i>Это может занять 20-40 секунд</i>"
    )

    await generate_and_show_post(callback.message, post_type)


# === Публикация ===

@router.callback_query(F.data.startswith("publish:"))
async def callback_publish(callback: CallbackQuery, bot: Bot):
    """Публикация поста в канал"""
    import base64
    from aiogram.types import BufferedInputFile

    # === ЛОГИРОВАНИЕ ===
    logger.info(f"[CALLBACK] publish: user={callback.from_user.id}, data={callback.data}")

    if not is_admin(callback.from_user.id):
        logger.warning(f"[CALLBACK] publish: ACCESS DENIED for user={callback.from_user.id}")
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    # Сразу отвечаем что публикуем
    await callback.answer("📤 Публикую...", show_alert=False)

    post_id = int(callback.data.split(":")[1])

    async with AsyncSessionLocal() as session:
        # Получаем пост
        result = await session.execute(
            select(Post).where(Post.id == post_id)
        )
        post = result.scalar_one_or_none()

        if not post:
            await callback.answer("❌ Пост не найден", show_alert=True)
            return

        try:
            # Добавляем ссылку на куратора (только для основного канала, не для тематических)
            if post.segment:
                curator_footer = ""
            else:
                curator_footer = (
                    f"\n\n━━━━━━━━━━━━━━━\n"
                    f"❓ Есть вопросы? Спроси AI-Куратора → {settings.curator_bot_username}"
                )

            # === Маршрутизация: сначала проверяем тематические каналы по сегменту ===
            target_chat = None
            publish_target = None

            if post.segment and post.segment in settings.thematic_channels:
                target_chat = settings.thematic_channels[post.segment]
                publish_target = target_chat
                logger.info(f"[CALLBACK] Routing post #{post_id} to thematic channel: {target_chat} (segment={post.segment})")
            else:
                # === Маршрутизация по каналам воронки ===
                channel_router = ChannelRouter(session)
                target_channel = None

                # Если у поста указан target_channel_id — используем его
                if post.target_channel_id:
                    target_channel = await channel_router.get_channel_by_telegram_id(post.target_channel_id)
                    if not target_channel:
                        result_ch = await session.execute(
                            select(ChannelTier).where(ChannelTier.id == post.target_channel_id)
                        )
                        target_channel = result_ch.scalar_one_or_none()

                # Если канал не найден — получаем через роутер по типу поста
                if not target_channel:
                    target_channel = await channel_router.get_target_channel(
                        post_type=post.post_type,
                        segment="universal"
                    )

                # Определяем Telegram chat_id для публикации
                if target_channel:
                    target_chat = target_channel.channel_id
                    publish_target = target_channel.channel_username or f"ID:{target_channel.channel_id}"
                else:
                    # Fallback: используем legacy hardcoded канал
                    target_chat = settings.channel_username
                    publish_target = settings.channel_username

            # Разбиваем длинный пост на части
            post_parts = split_post_to_messages(post.content, max_length=900)

            # Добавляем footer к последней части
            if post_parts:
                post_parts[-1] = post_parts[-1] + curator_footer

            channel_message = None

            # Если есть изображение - публикуем первую часть с изображением
            if post.image_url:
                try:
                    # Конвертируем base64 в файл
                    image_bytes = base64.b64decode(post.image_url)
                    image_file = BufferedInputFile(image_bytes, filename=f"post_{post_id}.jpg")

                    # Первая часть с фото (caption до 1024 символов)
                    first_part = post_parts[0] if post_parts else ""
                    if len(first_part) > 1024:
                        first_part = first_part[:1020] + "..."

                    channel_message = await bot.send_photo(
                        chat_id=target_chat,
                        photo=image_file,
                        caption=first_part,
                        parse_mode="HTML"
                    )

                    # Остальные части отправляем как текст
                    for part in post_parts[1:]:
                        await bot.send_message(
                            chat_id=target_chat,
                            text=part,
                            parse_mode="HTML"
                        )

                except Exception as e:
                    logger.error(f"Error sending image for post #{post_id}: {e}")
                    # Фолбэк: публикуем без изображения
                    for i, part in enumerate(post_parts):
                        msg = await bot.send_message(
                            chat_id=target_chat,
                            text=part,
                            parse_mode="HTML"
                        )
                        if i == 0:
                            channel_message = msg
            else:
                # Публикуем без изображения — все части
                for i, part in enumerate(post_parts):
                    msg = await bot.send_message(
                        chat_id=target_chat,
                        text=part,
                        parse_mode="HTML"
                    )
                    if i == 0:
                        channel_message = msg

            # Обновляем статус поста
            post.status = "published"
            post.published_at = datetime.utcnow()
            post.approved_at = datetime.utcnow()
            post.admin_id = callback.from_user.id
            post.channel_message_id = channel_message.message_id

            # Логируем действие
            action = AdminAction(
                admin_id=callback.from_user.id,
                post_id=post_id,
                action="publish",
                details={"has_image": bool(post.image_url)}
            )
            session.add(action)

            await session.commit()

            # AI Director: обновляем ChannelMemory после публикации
            if post.segment:
                try:
                    memory = get_channel_memory()
                    await memory.update_after_publish(
                        segment=post.segment,
                        post_content=post.content,
                        post_type=post.post_type,
                        post_id=post.id,
                        engagement_rate=post.engagement_rate,
                    )
                except Exception as e:
                    logger.warning(f"[DIRECTOR] ChannelMemory update failed: {e}")

            # Обновляем сообщение админу
            image_info = "🖼 с изображением" if post.image_url else ""
            await callback.message.edit_text(
                f"✅ <b>Пост #{post_id} опубликован! {image_info}</b>\n\n"
                f"{post.content[:300]}...\n\n"
                f"<i>Опубликовано в: {publish_target}</i>"
            )

            logger.info(f"Post #{post_id} published to {publish_target} (with_image={bool(post.image_url)})")

        except Exception as e:
            logger.error(f"Error publishing post #{post_id}: {e}")
            await callback.answer(f"❌ Ошибка публикации: {str(e)}", show_alert=True)
            return

    # callback.answer уже был вызван в начале


# === Отметить как опубликованный (вручную) ===

@router.callback_query(F.data.startswith("mark_published:"))
async def callback_mark_published(callback: CallbackQuery):
    """Помечает пост как опубликованный без отправки ботом.
    Для случаев когда пользователь копирует текст и постит сам."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    await callback.answer("✅ Запомнил!", show_alert=False)

    post_id = int(callback.data.split(":")[1])

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Post).where(Post.id == post_id)
        )
        post = result.scalar_one_or_none()

        if not post:
            await callback.answer("❌ Пост не найден", show_alert=True)
            return

        post.status = "published"
        post.published_at = datetime.utcnow()
        post.approved_at = datetime.utcnow()
        post.admin_id = callback.from_user.id

        action = AdminAction(
            admin_id=callback.from_user.id,
            post_id=post_id,
            action="mark_published",
            details={"manual": True}
        )
        session.add(action)
        await session.commit()

        await callback.message.edit_text(
            f"✅ <b>Пост #{post_id} — запомнил как опубликованный</b>\n\n"
            f"{post.content[:300]}{'...' if len(post.content) > 300 else ''}\n\n"
            f"<i>Бот учтёт этот пост при генерации новых — не будет повторять тему.</i>"
        )

        logger.info(f"Post #{post_id} marked as published manually by admin {callback.from_user.id}")


# === Планирование ===

@router.callback_query(F.data.startswith("schedule:"))
async def callback_schedule(callback: CallbackQuery):
    """Показать меню планирования публикации"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    post_id = int(callback.data.split(":")[1])

    await callback.message.edit_reply_markup(
        reply_markup=Keyboards.schedule_time_selection(post_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("sched_time:"))
async def callback_schedule_time(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора времени публикации"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    parts = callback.data.split(":")
    time_option = parts[1]
    post_id = int(parts[2])

    # Вычисляем время публикации
    now = datetime.utcnow()
    scheduled_time = None

    if time_option == "1h":
        scheduled_time = now + timedelta(hours=1)
    elif time_option == "3h":
        scheduled_time = now + timedelta(hours=3)
    elif time_option == "tomorrow_9":
        tomorrow = now.date() + timedelta(days=1)
        scheduled_time = datetime.combine(tomorrow, datetime.min.time().replace(hour=6))  # 9:00 MSK = 6:00 UTC
    elif time_option == "tomorrow_18":
        tomorrow = now.date() + timedelta(days=1)
        scheduled_time = datetime.combine(tomorrow, datetime.min.time().replace(hour=15))  # 18:00 MSK = 15:00 UTC
    elif time_option == "custom":
        await callback.message.edit_text(
            "📅 Введите дату и время публикации в формате:\n"
            "<code>ДД.ММ.ГГГГ ЧЧ:ММ</code>\n\n"
            "Например: <code>25.01.2026 14:30</code>\n\n"
            "Или отправьте /cancel для отмены"
        )
        # Сохраняем post_id в состоянии FSM
        await state.set_state(EditPostStates.waiting_for_custom_time)
        await state.update_data(post_id=post_id)
        await callback.answer()
        return

    if scheduled_time:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Post).where(Post.id == post_id)
            )
            post = result.scalar_one_or_none()

            if post:
                post.status = "scheduled"
                post.scheduled_for = scheduled_time

                action = AdminAction(
                    admin_id=callback.from_user.id,
                    post_id=post_id,
                    action="schedule",
                    details={"scheduled_for": scheduled_time.isoformat()}
                )
                session.add(action)

                await session.commit()

                # Время в московском часовом поясе (+3)
                msk_time = scheduled_time + timedelta(hours=3)

                await callback.message.edit_text(
                    f"📅 <b>Пост #{post_id} запланирован!</b>\n\n"
                    f"Время публикации: {msk_time.strftime('%d.%m.%Y %H:%M')} (МСК)\n\n"
                    f"<i>Пост будет автоматически опубликован в указанное время.</i>"
                )

    await callback.answer()


# === Редактирование ===

@router.callback_query(F.data.startswith("edit:"))
async def callback_edit(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования поста"""
    logger.info(f"[CALLBACK] edit: user={callback.from_user.id}, data={callback.data}")

    if not is_admin(callback.from_user.id):
        logger.warning(f"[CALLBACK] edit: ACCESS DENIED for user={callback.from_user.id}")
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    await callback.answer()
    post_id = int(callback.data.split(":")[1])

    # Сохраняем ID поста в состояние
    await state.update_data(editing_post_id=post_id)
    await state.set_state(EditPostStates.waiting_for_edit)

    await callback.message.edit_text(
        f"📝 <b>Редактирование поста #{post_id}</b>\n\n"
        "Отправьте инструкции по редактированию.\n"
        "Например: «Сделай короче» или «Добавь больше эмодзи»\n\n"
        "<i>Или отправьте /cancel для отмены</i>"
    )


@router.callback_query(F.data.startswith("regenerate:"))
async def callback_regenerate(callback: CallbackQuery, state: FSMContext):
    """Перегенерация поста с обратной связью"""
    logger.info(f"[CALLBACK] regenerate: user={callback.from_user.id}, data={callback.data}")

    if not is_admin(callback.from_user.id):
        logger.warning(f"[CALLBACK] regenerate: ACCESS DENIED for user={callback.from_user.id}")
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    await callback.answer()
    post_id = int(callback.data.split(":")[1])

    await state.update_data(regenerating_post_id=post_id)
    await state.set_state(EditPostStates.waiting_for_feedback)

    await callback.message.edit_text(
        f"🔄 <b>Перегенерация поста #{post_id}</b>\n\n"
        "Напишите, что не понравилось или что нужно изменить.\n"
        "AI учтёт ваши пожелания при генерации нового варианта.\n\n"
        "<i>Или отправьте /cancel для отмены</i>"
    )


# === Ручное редактирование ===

@router.callback_query(F.data.startswith("manual_edit:"))
async def callback_manual_edit(callback: CallbackQuery, state: FSMContext):
    """Начало ручного редактирования поста"""
    logger.info(f"[CALLBACK] manual_edit: user={callback.from_user.id}, data={callback.data}")

    if not is_admin(callback.from_user.id):
        logger.warning(f"[CALLBACK] manual_edit: ACCESS DENIED for user={callback.from_user.id}")
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    post_id = int(callback.data.split(":")[1])

    # Получаем текущий текст поста для показа
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Post).where(Post.id == post_id)
        )
        post = result.scalar_one_or_none()

        if not post:
            await callback.answer("❌ Пост не найден", show_alert=True)
            return

        # Сохраняем ID поста в состояние
        await state.update_data(manual_edit_post_id=post_id)
        await state.set_state(EditPostStates.waiting_for_manual_edit)

        await callback.message.edit_text(
            f"✏️ <b>Ручное редактирование поста #{post_id}</b>\n\n"
            f"<b>Текущий текст:</b>\n"
            f"<code>{post.content[:500]}{'...' if len(post.content) > 500 else ''}</code>\n\n"
            "📝 <b>Отправьте новый текст поста целиком.</b>\n"
            "Ваш текст полностью заменит текущий.\n\n"
            "<i>Или отправьте /cancel для отмены</i>"
        )
    await callback.answer()


# === Отклонение ===

@router.callback_query(F.data.startswith("reject:"))
async def callback_reject(callback: CallbackQuery):
    """Отклонение поста"""
    logger.info(f"[CALLBACK] reject: user={callback.from_user.id}, data={callback.data}")

    if not is_admin(callback.from_user.id):
        logger.warning(f"[CALLBACK] reject: ACCESS DENIED for user={callback.from_user.id}")
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    post_id = int(callback.data.split(":")[1])

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Post).where(Post.id == post_id)
        )
        post = result.scalar_one_or_none()

        if post:
            post.status = "rejected"
            post.admin_id = callback.from_user.id

            action = AdminAction(
                admin_id=callback.from_user.id,
                post_id=post_id,
                action="reject"
            )
            session.add(action)

            await session.commit()

            # AI Director: логируем отклонение для ReflectionEngine
            segment = post.segment or "main"
            try:
                reflection = get_reflection_engine()
                await reflection.on_reject(
                    segment=segment,
                    content=post.content,
                    reason="Отклонён админом",
                    post_type=post.post_type or "unknown",
                )
            except Exception as e:
                logger.warning(f"[DIRECTOR] ReflectionEngine error: {e}")

    await callback.message.edit_text(
        f"❌ <b>Пост #{post_id} отклонён</b>\n\n"
        "Используйте /generate для создания нового поста."
    )
    await callback.answer("Пост отклонён")


# === Отмена ===

@router.callback_query(F.data.startswith("cancel:"))
async def callback_cancel(callback: CallbackQuery):
    """Отмена текущего действия"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    post_id = int(callback.data.split(":")[1])

    # Возвращаем клавиатуру модерации
    await callback.message.edit_reply_markup(
        reply_markup=Keyboards.post_moderation(post_id)
    )
    await callback.answer("Отменено")


@router.callback_query(F.data == "back_to_menu")
async def callback_back_to_menu_legacy(callback: CallbackQuery):
    """Возврат в главное меню (legacy, redirect to new)"""
    await callback_menu_main(callback)


# === Обработчики главного меню ===

async def get_pending_count() -> int:
    """Получить количество постов на модерации"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(func.count(Post.id)).where(Post.status == "pending")
        )
        return result.scalar() or 0


@router.callback_query(F.data == "menu:main")
async def callback_menu_main(callback: CallbackQuery):
    """Показать главное меню"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    pending_count = await get_pending_count()

    await callback.message.edit_text(
        "🎛 <b>ГЛАВНОЕ МЕНЮ</b>\n\n"
        "Выберите действие:",
        reply_markup=Keyboards.main_menu(pending_count)
    )
    await callback.answer()


@router.callback_query(F.data == "menu:generate")
async def callback_menu_generate(callback: CallbackQuery):
    """Генерирует пост случайного типа"""
    import random
    from content_manager_bot.handlers.admin import generate_and_show_post

    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    # Выбираем случайный тип
    valid_types = list(ContentGenerator.get_available_post_types().keys())
    post_type = random.choice(valid_types)

    await callback.answer("🎲 Генерирую случайный пост...", show_alert=False)

    await callback.message.edit_text(
        f"🎲 Генерирую пост типа: {post_type}...\n"
        f"<i>Это может занять 20-40 секунд</i>"
    )

    await generate_and_show_post(callback.message, post_type)


@router.callback_query(F.data == "menu:pending")
async def callback_menu_pending(callback: CallbackQuery):
    """Показать посты на модерации"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    # Сразу отвечаем
    await callback.answer("📋 Загружаю посты...", show_alert=False)

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Post)
            .where(Post.status == "pending")
            .order_by(Post.generated_at.desc())
            .limit(5)  # Уменьшено с 10 до 5 для быстрой загрузки
        )
        posts = result.scalars().all()

    if not posts:
        await callback.message.edit_text(
            "📭 <b>Нет постов на модерации</b>\n\n"
            "Используйте кнопку «Создать пост» для генерации нового поста.",
            reply_markup=Keyboards.back_to_menu()
        )
        return

    # Показываем список
    type_names = ContentGenerator.get_available_post_types()

    text = f"📋 <b>Посты на модерации ({len(posts)}):</b>\n\n"
    for post in posts:
        type_name = type_names.get(post.post_type, post.post_type)
        preview = post.content[:80] + "..." if len(post.content) > 80 else post.content
        text += f"📝 <b>#{post.id}</b> ({type_name})\n{preview}\n\n"

    await callback.message.edit_text(text, reply_markup=Keyboards.back_to_menu())

    # Показываем только первые 3 поста с кнопками (для скорости)
    for post in posts[:3]:
        type_name = type_names.get(post.post_type, post.post_type)
        preview = post.content[:200] + "..." if len(post.content) > 200 else post.content
        has_image = bool(post.image_url)

        await callback.message.answer(
            f"📝 <b>#{post.id}</b> ({type_name})\n\n"
            f"{preview}\n\n"
            f"<i>Создан: {post.generated_at.strftime('%d.%m.%Y %H:%M')}</i>",
            reply_markup=Keyboards.post_moderation(post.id, has_image)
        )

    # Если есть ещё посты — уведомляем
    if len(posts) > 3:
        await callback.message.answer(
            f"<i>... и ещё {len(posts) - 3} постов. Используйте /pending для полного списка.</i>"
        )


@router.callback_query(F.data == "menu:stats")
async def callback_menu_stats(callback: CallbackQuery):
    """Показать меню статистики"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    await callback.message.edit_text(
        "📊 <b>СТАТИСТИКА</b>\n\n"
        "Выберите период или действие:",
        reply_markup=Keyboards.stats_menu()
    )
    await callback.answer()


@router.callback_query(F.data == "menu:top")
async def callback_menu_top(callback: CallbackQuery):
    """Показать меню топ постов"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    await callback.message.edit_text(
        "🏆 <b>ТОП ПОСТЫ</b>\n\n"
        "Выберите метрику для сортировки:",
        reply_markup=Keyboards.top_posts_menu()
    )
    await callback.answer()


@router.callback_query(F.data == "menu:schedule")
async def callback_menu_schedule(callback: CallbackQuery):
    """Показать настройки автопостинга"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    await callback.message.edit_text(
        "⏰ <b>АВТОПОСТИНГ</b>\n\n"
        "Включите/выключите автоматическую генерацию\n"
        "для каждого типа контента:",
        reply_markup=Keyboards.auto_schedule_settings()
    )
    await callback.answer()


@router.callback_query(F.data == "menu:help")
async def callback_menu_help(callback: CallbackQuery):
    """Показать справку"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    await callback.message.edit_text(
        "📖 <b>СПРАВКА</b>\n\n"
        "<b>📝 Создание контента</b>\n"
        "• Создать пост → выбрать тип → одобрить/отклонить\n"
        "• Можно редактировать и перегенерировать\n"
        "• Добавлять изображения (из базы)\n\n"
        "<b>📊 Аналитика</b>\n"
        "• Просмотры, реакции, вовлечённость\n"
        "• Топ постов по метрикам\n\n"
        "<b>⏰ Автопостинг</b>\n"
        "• Автоматическая генерация по расписанию\n"
        "• Настройка для каждого типа контента\n\n"
        "<b>Типы контента:</b>\n"
        "📦 product | 💪 motivation | 📰 news\n"
        "💡 tips | 🌟 success_story | 🎁 promo",
        reply_markup=Keyboards.back_to_menu()
    )
    await callback.answer()


# === Обработчики статистики ===

@router.callback_query(F.data.startswith("stats:"))
async def callback_stats_period(callback: CallbackQuery):
    """Показать статистику за период"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    period = callback.data.split(":")[1]

    if period == "update":
        # Обновление метрик
        await callback.message.edit_text("⏳ Обновляю метрики постов...")
        try:
            from content_manager_bot.services.analytics_service import AnalyticsService
            async with AsyncSessionLocal() as session:
                analytics_service = AnalyticsService(session)
                updated = await analytics_service.update_all_post_metrics(callback.bot)

            await callback.message.edit_text(
                f"✅ <b>Метрики обновлены!</b>\n\n"
                f"Обновлено постов: {updated}",
                reply_markup=Keyboards.stats_menu()
            )
        except Exception as e:
            await callback.message.edit_text(
                f"❌ Ошибка при обновлении:\n{str(e)}",
                reply_markup=Keyboards.stats_menu()
            )
        await callback.answer()
        return

    # Статистика за период
    async with AsyncSessionLocal() as session:
        from sqlalchemy import func as sql_func

        # Базовый запрос
        base_query = select(Post)

        if period != "all":
            days = int(period)
            from datetime import datetime, timedelta
            cutoff = datetime.utcnow() - timedelta(days=days)
            base_query = base_query.where(Post.published_at >= cutoff)

        # Считаем статистику
        stats = {}
        for status in ["draft", "pending", "published", "rejected"]:
            if period == "all":
                result = await session.execute(
                    select(sql_func.count(Post.id)).where(Post.status == status)
                )
            else:
                days = int(period)
                cutoff = datetime.utcnow() - timedelta(days=days)
                result = await session.execute(
                    select(sql_func.count(Post.id))
                    .where(Post.status == status)
                    .where(Post.generated_at >= cutoff)
                )
            stats[status] = result.scalar() or 0

        # Общее
        if period == "all":
            total_result = await session.execute(select(sql_func.count(Post.id)))
        else:
            total_result = await session.execute(
                select(sql_func.count(Post.id))
                .where(Post.generated_at >= cutoff)
            )
        total = total_result.scalar() or 0

    period_text = f"за {period} дней" if period != "all" else "за всё время"

    await callback.message.edit_text(
        f"📊 <b>Статистика {period_text}</b>\n\n"
        f"📝 Всего сгенерировано: <b>{total}</b>\n"
        f"✅ Опубликовано: <b>{stats['published']}</b>\n"
        f"⏳ На модерации: <b>{stats['pending']}</b>\n"
        f"📋 Черновики: <b>{stats['draft']}</b>\n"
        f"❌ Отклонено: <b>{stats['rejected']}</b>",
        reply_markup=Keyboards.stats_menu()
    )
    await callback.answer()


# === Обработчики топ постов ===

@router.callback_query(F.data.startswith("top:"))
async def callback_top_posts(callback: CallbackQuery):
    """Показать топ постов по метрике"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    sort_by = callback.data.split(":")[1]

    await callback.message.edit_text("⏳ Получаю топ постов...")

    try:
        from content_manager_bot.services.analytics_service import AnalyticsService
        async with AsyncSessionLocal() as session:
            analytics_service = AnalyticsService(session)
            top_posts = await analytics_service.get_top_posts(
                limit=10,
                days=30,
                sort_by=sort_by
            )

        if not top_posts:
            await callback.message.edit_text(
                "📭 Нет опубликованных постов за последние 30 дней",
                reply_markup=Keyboards.top_posts_menu()
            )
            await callback.answer()
            return

        sort_names = {
            'views': 'просмотрам',
            'reactions': 'реакциям',
            'engagement': 'вовлечённости'
        }

        type_emojis = {
            'product': '📦',
            'motivation': '💪',
            'news': '📰',
            'tips': '💡',
            'success_story': '🌟',
            'promo': '🎁'
        }

        response = f"🏆 <b>Топ-10 постов</b> (по {sort_names[sort_by]})\n\n"

        for i, post in enumerate(top_posts, 1):
            emoji = type_emojis.get(post['type'], '📝')
            response += f"{i}. {emoji} #{post['id']}\n"
            response += f"   👁 {post['views']} | ❤️ {post['reactions']} | "
            response += f"📊 {post['engagement_rate']:.1f}%\n"

        await callback.message.edit_text(
            response,
            reply_markup=Keyboards.top_posts_menu()
        )

    except Exception as e:
        logger.error(f"Error getting top posts: {e}")
        await callback.message.edit_text(
            f"❌ Ошибка при получении топа:\n{str(e)}",
            reply_markup=Keyboards.top_posts_menu()
        )

    await callback.answer()


# === Обработка текста в состояниях ===

@router.message(EditPostStates.waiting_for_edit)
async def process_edit_instructions(message: Message, state: FSMContext):
    """Обработка инструкций по редактированию"""
    if not is_admin(message.from_user.id):
        return

    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Редактирование отменено")
        return

    data = await state.get_data()
    post_id = data.get("editing_post_id")

    if not post_id:
        await state.clear()
        return

    status_msg = await message.answer("⏳ Редактирую пост...")

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Post).where(Post.id == post_id)
        )
        post = result.scalar_one_or_none()

        if not post:
            await status_msg.edit_text("❌ Пост не найден")
            await state.clear()
            return

        try:
            original_content = post.content

            # Редактируем через AI
            new_content = await content_generator.edit_post(
                original_post=post.content,
                edit_instructions=message.text
            )

            post.content = new_content

            action = AdminAction(
                admin_id=message.from_user.id,
                post_id=post_id,
                action="edit",
                details={"instructions": message.text}
            )
            session.add(action)

            await session.commit()

            # AI Director: логируем правку для ReflectionEngine
            segment = post.segment or "main"
            try:
                reflection = get_reflection_engine()
                await reflection.on_edit(
                    segment=segment,
                    original=original_content,
                    edited=new_content,
                    post_type=post.post_type or "unknown",
                )
            except Exception as e:
                logger.warning(f"[DIRECTOR] ReflectionEngine edit error: {e}")

            await status_msg.delete()

            type_names = ContentGenerator.get_available_post_types()
            type_name = type_names.get(post.post_type, post.post_type)

            await message.answer(
                f"📝 <b>Отредактированный пост ({type_name})</b>\n"
                f"ID: #{post_id}\n\n"
                f"{new_content}\n\n"
                f"<i>Что делаем с постом?</i>",
                reply_markup=Keyboards.post_moderation(post_id)
            )

        except Exception as e:
            logger.error(f"Error editing post: {e}")
            await status_msg.edit_text(f"❌ Ошибка редактирования: {str(e)}")

    await state.clear()


@router.message(EditPostStates.waiting_for_manual_edit)
async def process_manual_edit_text(message: Message, state: FSMContext):
    """Обработка нового текста при ручном редактировании"""
    if not is_admin(message.from_user.id):
        return

    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Редактирование отменено")
        return

    data = await state.get_data()
    post_id = data.get("manual_edit_post_id")

    if not post_id:
        await state.clear()
        return

    new_text = message.text.strip()

    if len(new_text) < 50:
        await message.answer(
            "⚠️ Текст слишком короткий (минимум 50 символов).\n"
            "Отправьте более развёрнутый текст или /cancel для отмены."
        )
        return

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Post).where(Post.id == post_id)
        )
        post = result.scalar_one_or_none()

        if not post:
            await message.answer("❌ Пост не найден")
            await state.clear()
            return

        original_content = post.content

        # Сохраняем новый текст
        post.content = new_text

        action = AdminAction(
            admin_id=message.from_user.id,
            post_id=post_id,
            action="manual_edit",
            details={"new_length": len(new_text)}
        )
        session.add(action)

        await session.commit()

        # AI Director: логируем ручную правку для ReflectionEngine
        segment = post.segment or "main"
        try:
            reflection = get_reflection_engine()
            await reflection.on_edit(
                segment=segment,
                original=original_content,
                edited=new_text,
                post_type=post.post_type or "unknown",
            )
        except Exception as e:
            logger.warning(f"[DIRECTOR] ReflectionEngine manual_edit error: {e}")

        type_names = ContentGenerator.get_available_post_types()
        type_name = type_names.get(post.post_type, post.post_type)
        has_image = bool(post.image_url)

        await message.answer(
            f"✅ <b>Текст обновлён!</b>\n\n"
            f"📝 <b>Пост ({type_name})</b>\n"
            f"ID: #{post_id}\n\n"
            f"{new_text}\n\n"
            f"<i>Что делаем с постом?</i>",
            reply_markup=Keyboards.post_moderation(post_id, has_image)
        )

        logger.info(f"Post #{post_id} manually edited by admin {message.from_user.id}")

    await state.clear()


@router.message(EditPostStates.waiting_for_feedback)
async def process_regenerate_feedback(message: Message, state: FSMContext):
    """Обработка фидбека для перегенерации"""
    if not is_admin(message.from_user.id):
        return

    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Перегенерация отменена")
        return

    data = await state.get_data()
    post_id = data.get("regenerating_post_id")

    if not post_id:
        await state.clear()
        return

    status_msg = await message.answer("⏳ Генерирую новый вариант...")

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Post).where(Post.id == post_id)
        )
        post = result.scalar_one_or_none()

        if not post:
            await status_msg.edit_text("❌ Пост не найден")
            await state.clear()
            return

        try:
            # Перегенерируем через AI
            new_content = await content_generator.regenerate_post(
                original_post=post.content,
                feedback=message.text
            )

            post.content = new_content

            action = AdminAction(
                admin_id=message.from_user.id,
                post_id=post_id,
                action="regenerate",
                details={"feedback": message.text}
            )
            session.add(action)

            await session.commit()

            await status_msg.delete()

            type_names = ContentGenerator.get_available_post_types()
            type_name = type_names.get(post.post_type, post.post_type)

            await message.answer(
                f"🔄 <b>Перегенерированный пост ({type_name})</b>\n"
                f"ID: #{post_id}\n\n"
                f"{new_content}\n\n"
                f"<i>Что делаем с постом?</i>",
                reply_markup=Keyboards.post_moderation(post_id)
            )

        except Exception as e:
            logger.error(f"Error regenerating post: {e}")
            await status_msg.edit_text(f"❌ Ошибка перегенерации: {str(e)}")

    await state.clear()


# === Автопостинг ===

@router.callback_query(F.data.startswith("autosched:"))
async def callback_autoschedule(callback: CallbackQuery):
    """Управление автопостингом"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    action = callback.data.split(":")[1]
    logger.info(f"Autoschedule callback: action={action}, user={callback.from_user.id}")

    try:
        if action == "status":
            # Показываем статус расписаний
            async with AsyncSessionLocal() as session:
                result = await session.execute(select(ContentSchedule))
                schedules = result.scalars().all()

                if not schedules:
                    await callback.message.edit_text(
                        "📅 <b>Расписание автопостинга</b>\n\n"
                        "Пока нет активных расписаний.\n\n"
                        "Нажмите на тип поста чтобы включить автогенерацию:",
                        reply_markup=Keyboards.auto_schedule_settings()
                    )
                else:
                    status_text = "📅 <b>Расписание автопостинга</b>\n\n"
                    type_names = ContentGenerator.get_available_post_types()

                    for sched in schedules:
                        type_name = type_names.get(sched.post_type, sched.post_type)
                        status_emoji = "✅" if sched.is_active else "❌"
                        next_run = sched.next_run.strftime("%d.%m %H:%M") if sched.next_run else "—"

                        status_text += f"{status_emoji} {type_name}\n"
                        status_text += f"   Следующий: {next_run}\n"
                        status_text += f"   Всего: {sched.total_generated} постов\n\n"

                    await callback.message.edit_text(
                        status_text,
                        reply_markup=Keyboards.auto_schedule_settings()
                    )

        else:
            # Включаем/выключаем расписание для типа поста
            post_type = action

            # Используем конфигурацию из ContentScheduler (единый источник истины)
            config = ContentScheduler.SCHEDULE_CONFIG.get(post_type, {"hours": 24, "desc": "ежедневно"})

            async with AsyncSessionLocal() as session:
                # Ищем существующее расписание
                result = await session.execute(
                    select(ContentSchedule).where(ContentSchedule.post_type == post_type)
                )
                schedule = result.scalar_one_or_none()

                if schedule:
                    # Переключаем статус
                    schedule.is_active = not schedule.is_active
                    status = "включен" if schedule.is_active else "выключен"
                else:
                    # Создаём новое расписание с настройками для типа
                    schedule = ContentSchedule(
                        post_type=post_type,
                        cron_expression=f"Every {config['hours']} hours",  # Описательное поле для справки
                        is_active=True,
                        next_run=datetime.utcnow() + timedelta(hours=config["hours"]),
                        total_generated=0
                    )
                    session.add(schedule)
                    status = "включен"
                    logger.info(f"Created new schedule for {post_type}: interval={config['hours']}h, next_run={schedule.next_run}")

                await session.commit()

                # Получаем ВСЕ расписания для отображения полного статуса
                all_result = await session.execute(select(ContentSchedule))
                all_schedules = all_result.scalars().all()

            type_names = ContentGenerator.get_available_post_types()
            type_name = type_names.get(post_type, post_type)

            await callback.answer(f"Автопостинг {type_name}: {status}", show_alert=True)

            # Формируем статус ВСЕХ расписаний
            status_text = "⚙️ <b>Настройки автопостинга</b>\n\n"

            if all_schedules:
                for sched in all_schedules:
                    sched_name = type_names.get(sched.post_type, sched.post_type)
                    emoji = "✅" if sched.is_active else "❌"
                    next_run = sched.next_run.strftime("%d.%m %H:%M") if sched.next_run else "—"
                    sched_config = ContentScheduler.SCHEDULE_CONFIG.get(sched.post_type, {})
                    desc = sched_config.get("desc", "")
                    status_text += f"{emoji} <b>{sched_name}</b>\n"
                    status_text += f"   📅 {desc}\n"
                    if sched.is_active:
                        status_text += f"   ⏰ Следующий: {next_run}\n"
                    status_text += "\n"
            else:
                status_text += "Нет настроенных расписаний.\n\n"

            status_text += "<i>Нажмите на тип для включения/выключения</i>"

            await callback.message.edit_text(
                status_text,
                reply_markup=Keyboards.auto_schedule_settings()
            )

    except Exception as e:
        logger.error(f"Error in autoschedule callback: {e}")
        await callback.answer(f"❌ Ошибка: {str(e)[:100]}", show_alert=True)


# === Работа с изображениями ===

@router.callback_query(F.data.startswith("gen_image:"))
async def callback_generate_image(callback: CallbackQuery):
    """Генерация изображения для поста"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    post_id = int(callback.data.split(":")[1])

    # Проверяем доступность генерации
    if not content_generator.is_image_generation_available():
        await callback.answer(
            "❌ Поиск фото продуктов недоступен.",
            show_alert=True
        )
        return

    # Сразу отвечаем что началась генерация
    await callback.answer("🖼 Генерирую изображение...", show_alert=False)

    # Обновляем сообщение
    await callback.message.edit_text(
        f"🖼 Генерирую изображение для поста #{post_id}...\n"
        "Это может занять 30-60 секунд."
    )

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Post).where(Post.id == post_id)
        )
        post = result.scalar_one_or_none()

        if not post:
            await callback.message.edit_text("❌ Пост не найден")
            return

        try:
            # Генерируем изображение
            image_base64, image_prompt = await content_generator.generate_image(
                post_type=post.post_type,
                post_content=post.content
            )

            if image_base64:
                # Сохраняем в БД
                post.image_url = image_base64
                post.image_prompt = image_prompt
                post.image_status = "generated"

                action = AdminAction(
                    admin_id=callback.from_user.id,
                    post_id=post_id,
                    action="generate_image",
                    details={"prompt": image_prompt}
                )
                session.add(action)
                await session.commit()

                # Показываем пост с изображением
                await _show_post_with_image(callback.message, post)

                logger.info(f"Image generated for post #{post_id}")

            else:
                await callback.message.edit_text(
                    f"❌ Не удалось сгенерировать изображение для поста #{post_id}\n\n"
                    "Попробуйте ещё раз или продолжите без изображения.",
                    reply_markup=Keyboards.post_moderation(post_id, has_image=False)
                )

        except Exception as e:
            logger.error(f"Error generating image for post #{post_id}: {e}")
            await callback.message.edit_text(
                f"❌ Ошибка при генерации изображения:\n{str(e)}\n\n"
                "Попробуйте ещё раз или продолжите без изображения.",
                reply_markup=Keyboards.post_moderation(post_id, has_image=False)
            )


@router.callback_query(F.data.startswith("regen_image:"))
async def callback_regenerate_image(callback: CallbackQuery, state: FSMContext):
    """Перегенерация изображения с возможностью указать фидбек"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    post_id = int(callback.data.split(":")[1])

    # Проверяем доступность генерации
    if not content_generator.is_image_generation_available():
        await callback.answer(
            "❌ Поиск фото продуктов недоступен.",
            show_alert=True
        )
        return

    # Сразу отвечаем что началась генерация
    await callback.answer("🖼 Генерирую новое изображение...", show_alert=False)

    # Обновляем сообщение
    await callback.message.edit_text(
        f"🖼 Генерирую новое изображение для поста #{post_id}...\n"
        "Это может занять 30-60 секунд."
    )

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Post).where(Post.id == post_id)
        )
        post = result.scalar_one_or_none()

        if not post:
            await callback.message.edit_text("❌ Пост не найден")
            return

        try:
            # Перегенерируем изображение (с другим seed - получится другой результат)
            image_base64, image_prompt = await content_generator.generate_image(
                post_type=post.post_type,
                post_content=post.content
            )

            if image_base64:
                # Обновляем в БД
                post.image_url = image_base64
                post.image_prompt = image_prompt
                post.image_status = "generated"

                action = AdminAction(
                    admin_id=callback.from_user.id,
                    post_id=post_id,
                    action="regenerate_image",
                    details={"prompt": image_prompt}
                )
                session.add(action)
                await session.commit()

                # Показываем пост с новым изображением
                await _show_post_with_image(callback.message, post)

                logger.info(f"Image regenerated for post #{post_id}")

            else:
                await callback.message.edit_text(
                    f"❌ Не удалось сгенерировать изображение для поста #{post_id}\n\n"
                    "Попробуйте ещё раз.",
                    reply_markup=Keyboards.post_moderation(post_id, has_image=bool(post.image_url))
                )

        except Exception as e:
            logger.error(f"Error regenerating image for post #{post_id}: {e}")
            await callback.message.edit_text(
                f"❌ Ошибка при генерации изображения:\n{str(e)}",
                reply_markup=Keyboards.post_moderation(post_id, has_image=bool(post.image_url))
            )


@router.callback_query(F.data.startswith("remove_image:"))
async def callback_remove_image(callback: CallbackQuery):
    """Удаление изображения из поста"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    post_id = int(callback.data.split(":")[1])

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Post).where(Post.id == post_id)
        )
        post = result.scalar_one_or_none()

        if not post:
            await callback.answer("❌ Пост не найден", show_alert=True)
            return

        # Удаляем изображение
        post.image_url = None
        post.image_prompt = None
        post.image_status = None

        action = AdminAction(
            admin_id=callback.from_user.id,
            post_id=post_id,
            action="remove_image"
        )
        session.add(action)
        await session.commit()

        type_names = ContentGenerator.get_available_post_types()
        type_name = type_names.get(post.post_type, post.post_type)

        # Показываем пост без изображения
        await callback.message.edit_text(
            f"📝 <b>Пост ({type_name})</b>\n"
            f"ID: #{post_id}\n\n"
            f"{post.content}\n\n"
            f"<i>Что делаем с постом?</i>",
            reply_markup=Keyboards.post_moderation(post_id, has_image=False)
        )

    await callback.answer("✅ Изображение удалено")
    logger.info(f"Image removed from post #{post_id}")


async def _show_post_with_image(message: Message, post: Post):
    """
    Helper функция для показа поста с изображением

    Args:
        message: Сообщение для редактирования
        post: Объект поста с изображением
    """
    import base64
    import io
    from aiogram.types import BufferedInputFile

    type_names = ContentGenerator.get_available_post_types()
    type_name = type_names.get(post.post_type, post.post_type)

    try:
        # Конвертируем base64 в файл
        image_bytes = base64.b64decode(post.image_url)
        image_file = BufferedInputFile(image_bytes, filename=f"post_{post.id}.jpg")

        # Удаляем старое сообщение (с текстом "генерирую...")
        try:
            await message.delete()
        except:
            pass

        # Отправляем новое сообщение с изображением
        await message.answer_photo(
            photo=image_file,
            caption=(
                f"📝 <b>Пост ({type_name})</b>\n"
                f"ID: #{post.id}\n\n"
                f"{post.content}\n\n"
                f"<i>Что делаем с постом?</i>"
            ),
            reply_markup=Keyboards.post_moderation(post.id, has_image=True)
        )

    except Exception as e:
        logger.error(f"Error showing post with image: {e}")
        # Фолбэк: показываем без изображения
        await message.edit_text(
            f"📝 <b>Пост ({type_name})</b>\n"
            f"ID: #{post.id}\n\n"
            f"{post.content}\n\n"
            f"🖼 <i>Изображение сгенерировано, но ошибка отображения</i>\n\n"
            f"<i>Что делаем с постом?</i>",
            reply_markup=Keyboards.post_moderation(post.id, has_image=True)
        )


# === Обработчик кастомного времени публикации ===

@router.message(EditPostStates.waiting_for_custom_time)
async def process_custom_time(message: Message, state: FSMContext):
    """Обработка ввода кастомного времени публикации"""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещён")
        await state.clear()
        return

    # Получаем post_id из состояния
    data = await state.get_data()
    post_id = data.get("post_id")

    if not post_id:
        await message.answer("❌ Ошибка: ID поста не найден")
        await state.clear()
        return

    # Парсим дату и время
    try:
        # Формат: ДД.ММ.ГГГГ ЧЧ:ММ
        datetime_str = message.text.strip()
        custom_time = datetime.strptime(datetime_str, "%d.%m.%Y %H:%M")

        # Преобразуем из МСК в UTC (МСК = UTC+3)
        scheduled_time = custom_time - timedelta(hours=3)

        # Проверяем, что время в будущем
        if scheduled_time <= datetime.utcnow():
            await message.answer(
                "❌ <b>Ошибка!</b>\n\n"
                "Время публикации должно быть в будущем.\n\n"
                "Попробуйте еще раз или отправьте /cancel для отмены."
            )
            return

        # Сохраняем в БД
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Post).where(Post.id == post_id)
            )
            post = result.scalar_one_or_none()

            if not post:
                await message.answer("❌ Пост не найден")
                await state.clear()
                return

            post.status = "scheduled"
            post.scheduled_for = scheduled_time

            action = AdminAction(
                admin_id=message.from_user.id,
                post_id=post_id,
                action="schedule",
                details={"scheduled_for": scheduled_time.isoformat(), "custom": True}
            )
            session.add(action)

            await session.commit()

            await message.answer(
                f"✅ <b>Пост #{post_id} запланирован!</b>\n\n"
                f"📅 Время публикации: {custom_time.strftime('%d.%m.%Y %H:%M')} (МСК)\n\n"
                f"<i>Пост будет автоматически опубликован в указанное время.</i>"
            )

        # Очищаем состояние
        await state.clear()

    except ValueError:
        await message.answer(
            "❌ <b>Неверный формат!</b>\n\n"
            "Используйте формат: <code>ДД.ММ.ГГГГ ЧЧ:ММ</code>\n"
            "Например: <code>25.01.2026 14:30</code>\n\n"
            "Или отправьте /cancel для отмены."
        )


# === Catch-all для необработанных callback'ов ===

@router.callback_query()
async def callback_unhandled(callback: CallbackQuery):
    """
    Catch-all handler для необработанных callback'ов.
    Помогает отлаживать проблемы с кнопками.
    """
    logger.warning(f"[CALLBACK] UNHANDLED: user={callback.from_user.id}, data={callback.data}")
    await callback.answer(f"⚠️ Неизвестная команда: {callback.data}", show_alert=True)
