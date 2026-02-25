"""
Обработчики команд администратора
"""
from datetime import datetime, timedelta
from typing import Optional
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from loguru import logger
from sqlalchemy import select, func, case, and_
from sqlalchemy.ext.asyncio import AsyncSession

from shared.config.settings import settings
from shared.database.base import AsyncSessionLocal
from shared.style_monitor import get_style_service
from content_manager_bot.ai.content_generator import ContentGenerator
from content_manager_bot.database.models import Post, PostStatus, AdminAction, DiaryEntry
from content_manager_bot.utils.keyboards import Keyboards
from content_manager_bot.analytics import StatsCollector, AnalyticsService

router = Router()

# Инициализируем генератор контента
content_generator = ContentGenerator()


class DiaryStates(StatesGroup):
    """FSM для дневника — ожидание ввода текста записи"""
    waiting_for_entry = State()


def is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь администратором"""
    return user_id in settings.admin_ids_list


async def get_pending_count() -> int:
    """Получить количество постов на модерации"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(func.count(Post.id)).where(Post.status == "pending")
        )
        return result.scalar() or 0


@router.message(CommandStart())
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    if not is_admin(message.from_user.id):
        await message.answer(
            "⛔ Этот бот доступен только администраторам.\n"
            "Если вы администратор, убедитесь что ваш ID добавлен в настройки."
        )
        return

    pending_count = await get_pending_count()
    pending_text = f"\n\n📋 На модерации: <b>{pending_count}</b> постов" if pending_count > 0 else ""

    await message.answer(
        "🔥 <b>APEXFLOW Command Center</b>\n\n"
        "Всё управление контентом — в Mini App.\n"
        "Нажми кнопку меню внизу чтобы открыть.\n\n"
        "📓 <b>Дневник</b> — используй кнопку ниже для быстрых записей."
        f"{pending_text}",
        reply_markup=Keyboards.reply_main_menu()
    )

    # Логируем действие
    async with AsyncSessionLocal() as session:
        action = AdminAction(
            admin_id=message.from_user.id,
            action="start_bot"
        )
        session.add(action)
        await session.commit()


@router.message(Command("menu"))
async def cmd_menu(message: Message):
    """Обработчик команды /menu - направить в Mini App"""
    if not is_admin(message.from_user.id):
        return

    await message.answer(
        "🔥 <b>APEXFLOW Command Center</b>\n\n"
        "Всё управление — в Mini App.\n"
        "Нажми кнопку меню внизу чтобы открыть."
    )


# === Обработчики текстовых кнопок (Reply Keyboard) ===

@router.message(F.text == "📓 Дневник")
async def btn_diary(message: Message):
    """Кнопка: Дневник — показать записи и предложить добавить новую"""
    if not is_admin(message.from_user.id):
        return
    await show_diary(message)


async def show_diary(message: Message):
    """Показать последние записи дневника"""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(DiaryEntry)
            .where(DiaryEntry.admin_id == message.from_user.id)
            .order_by(DiaryEntry.created_at.desc())
            .limit(5)
        )
        entries = result.scalars().all()

    if not entries:
        text = (
            "📓 <b>ДНЕВНИК</b>\n\n"
            "Пока записей нет.\n\n"
            "Записывай мысли, события, идеи — "
            "бот будет использовать их как контекст при генерации постов.\n\n"
            "<i>Нажми кнопку ниже чтобы добавить первую запись.</i>"
        )
    else:
        text = "📓 <b>ДНЕВНИК</b>\n\n"
        for entry in entries:
            date_str = entry.created_at.strftime("%d.%m %H:%M") if entry.created_at else "?"
            preview = entry.entry_text[:150]
            if len(entry.entry_text) > 150:
                preview += "..."
            text += f"<b>{date_str}</b>\n{preview}\n\n"

        text += f"<i>Показаны последние {len(entries)} записей</i>"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Новая запись", callback_data="diary:new")],
        [InlineKeyboardButton(text="🔙 В меню", callback_data="menu:main")],
    ])

    await message.answer(text, reply_markup=keyboard)


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Обработчик команды /help"""
    if not is_admin(message.from_user.id):
        return

    await message.answer(
        "📖 <b>APEXFLOW Command Center</b>\n\n"
        "Основное управление — через Mini App (кнопка меню).\n\n"
        "<b>Быстрые действия в боте:</b>\n"
        "📓 <b>Дневник</b> — кнопка внизу или /diary\n"
        "📝 /generate — быстрая генерация поста\n"
        "📋 /pending — посты на модерации\n\n"
        "<i>Посты, аналитика, Traffic Engine, AI Director — всё в Mini App.</i>"
    )


@router.message(Command("generate"))
async def cmd_generate(message: Message):
    """Обработчик команды /generate"""
    import random

    if not is_admin(message.from_user.id):
        return

    # Парсим аргументы команды
    args = message.text.split(maxsplit=1)

    if len(args) == 1:
        # Без аргументов - выбираем случайный тип
        valid_types = list(ContentGenerator.get_available_post_types().keys())
        post_type = random.choice(valid_types)
        await message.answer(f"🎲 Генерирую случайный тип: {post_type}")
    else:
        post_type = args[1].lower().strip()

        # Проверяем валидность типа
        valid_types = ContentGenerator.get_available_post_types()
        if post_type not in valid_types:
            await message.answer(
                f"❌ Неизвестный тип поста: {post_type}\n\n"
                f"Доступные типы: {', '.join(valid_types.keys())}"
            )
            return

    # Генерируем пост
    await generate_and_show_post(message, post_type)


async def generate_and_show_post(
    message: Message,
    post_type: str,
    custom_topic: Optional[str] = None
):
    """
    Генерирует пост и показывает админу на модерацию
    Автоматически подставляет фото продукта из базы, если найдено

    Args:
        message: Сообщение от админа
        post_type: Тип поста
        custom_topic: Дополнительная тема
    """
    from aiogram.types import BufferedInputFile
    import base64

    type_names = ContentGenerator.get_available_post_types()
    type_name = type_names.get(post_type, post_type)

    # Отправляем сообщение о генерации
    status_msg = await message.answer(f"⏳ Генерирую пост ({type_name})...")

    try:
        # Генерируем контент
        content, prompt_used = await content_generator.generate_post(
            post_type=post_type,
            custom_topic=custom_topic
        )

        # Сохраняем в БД
        async with AsyncSessionLocal() as session:
            post = Post(
                content=content,
                post_type=post_type,
                status="pending",
                generated_at=datetime.utcnow(),
                ai_model="GigaChat",
                prompt_used=prompt_used
            )
            session.add(post)
            await session.commit()
            await session.refresh(post)

            # Логируем действие
            action = AdminAction(
                admin_id=message.from_user.id,
                post_id=post.id,
                action="generate",
                details={"post_type": post_type}
            )
            session.add(action)
            await session.commit()

            post_id = post.id

        # Генерируем изображение (если доступно)
        has_image = False
        if content_generator.is_image_generation_available():
            try:
                await status_msg.edit_text(
                    f"⏳ Пост сгенерирован!\n"
                    f"🖼 Генерирую изображение ({type_name})...\n"
                    "Это может занять 30-60 секунд."
                )

                image_base64, image_prompt = await content_generator.generate_image(
                    post_type=post_type,
                    post_content=content
                )

                if image_base64:
                    # Сохраняем изображение в БД
                    async with AsyncSessionLocal() as session:
                        result = await session.execute(
                            select(Post).where(Post.id == post_id)
                        )
                        post = result.scalar_one()
                        post.image_url = image_base64
                        post.image_prompt = image_prompt
                        post.image_status = "generated"
                        await session.commit()

                    has_image = True
                    logger.info(f"Image generated for post #{post_id}")
                else:
                    logger.warning(f"Failed to generate image for post #{post_id}")

            except Exception as e:
                logger.error(f"Error generating image for post #{post_id}: {e}")
                # Продолжаем без изображения

        # Удаляем статусное сообщение
        await status_msg.delete()

        # Показываем пост на модерацию
        if has_image:
            try:
                # Конвертируем base64 в файл
                async with AsyncSessionLocal() as session:
                    result = await session.execute(
                        select(Post).where(Post.id == post_id)
                    )
                    post = result.scalar_one()

                    image_bytes = base64.b64decode(post.image_url)
                    image_file = BufferedInputFile(image_bytes, filename=f"post_{post_id}.jpg")

                    await message.answer_photo(
                        photo=image_file,
                        caption=(
                            f"📝 <b>Новый пост ({type_name})</b>\n"
                            f"ID: #{post_id}\n\n"
                            f"{content}\n\n"
                            f"<i>Что делаем с постом?</i>"
                        ),
                        reply_markup=Keyboards.post_moderation(post_id, has_image=True)
                    )
            except Exception as e:
                logger.error(f"Error showing image: {e}")
                # Фолбэк: показываем без изображения
                await message.answer(
                    f"📝 <b>Новый пост ({type_name})</b>\n"
                    f"ID: #{post_id}\n\n"
                    f"{content}\n\n"
                    f"🖼 <i>Изображение сгенерировано, но ошибка отображения</i>\n\n"
                    f"<i>Что делаем с постом?</i>",
                    reply_markup=Keyboards.post_moderation(post_id, has_image=True)
                )
        else:
            # Без изображения
            await message.answer(
                f"📝 <b>Новый пост ({type_name})</b>\n"
                f"ID: #{post_id}\n\n"
                f"{content}\n\n"
                f"<i>Что делаем с постом?</i>",
                reply_markup=Keyboards.post_moderation(post_id, has_image=False)
            )

    except Exception as e:
        logger.error(f"Error generating post: {e}")
        await status_msg.edit_text(
            f"❌ Ошибка при генерации поста:\n{str(e)}\n\n"
            "Попробуйте ещё раз."
        )


@router.message(Command("pending"))
async def cmd_pending(message: Message):
    """Обработчик команды /pending - показать посты на модерации"""
    if not is_admin(message.from_user.id):
        return

    async with AsyncSessionLocal() as session:
        # Получаем посты со статусом pending
        result = await session.execute(
            select(Post)
            .where(Post.status == "pending")
            .order_by(Post.generated_at.desc())
            .limit(10)
        )
        posts = result.scalars().all()

        if not posts:
            await message.answer(
                "📭 <b>Нет постов на модерации</b>\n\n"
                "Используйте /generate для создания нового поста."
            )
            return

        await message.answer(f"📋 <b>Посты на модерации ({len(posts)}):</b>")

        type_names = ContentGenerator.get_available_post_types()

        for post in posts:
            type_name = type_names.get(post.post_type, post.post_type)
            preview = post.content[:200] + "..." if len(post.content) > 200 else post.content

            await message.answer(
                f"📝 <b>#{post.id}</b> ({type_name})\n\n"
                f"{preview}\n\n"
                f"<i>Создан: {post.generated_at.strftime('%d.%m.%Y %H:%M')}</i>",
                reply_markup=Keyboards.post_moderation(post.id)
            )


@router.message(Command("stats"))
async def cmd_stats(message: Message):
    """Обработчик команды /stats - статистика"""
    if not is_admin(message.from_user.id):
        return

    async with AsyncSessionLocal() as session:
        # Считаем статистику по статусам
        stats = {}
        for status in ["draft", "pending", "published", "rejected"]:
            result = await session.execute(
                select(func.count(Post.id)).where(Post.status == status)
            )
            stats[status] = result.scalar() or 0

        # Общее количество
        total_result = await session.execute(select(func.count(Post.id)))
        total = total_result.scalar() or 0

        # Статистика по типам
        type_stats_result = await session.execute(
            select(Post.post_type, func.count(Post.id))
            .where(Post.status == "published")
            .group_by(Post.post_type)
        )
        type_stats = {row[0]: row[1] for row in type_stats_result.all()}

    type_names = ContentGenerator.get_available_post_types()

    type_stats_text = "\n".join([
        f"  • {type_names.get(t, t)}: {c}"
        for t, c in type_stats.items()
    ]) or "  Пока нет публикаций"

    await message.answer(
        "📊 <b>Статистика контент-менеджера</b>\n\n"
        f"📝 Всего сгенерировано: <b>{total}</b>\n"
        f"✅ Опубликовано: <b>{stats['published']}</b>\n"
        f"⏳ На модерации: <b>{stats['pending']}</b>\n"
        f"📋 Черновики: <b>{stats['draft']}</b>\n"
        f"❌ Отклонено: <b>{stats['rejected']}</b>\n\n"
        f"<b>Опубликовано по типам:</b>\n{type_stats_text}\n\n"
        f"<i>Используйте /analytics для детальной аналитики постов</i>",
        reply_markup=Keyboards.analytics_menu()
    )


@router.message(Command("schedule"))
async def cmd_schedule(message: Message):
    """Обработчик команды /schedule - настройки автопостинга"""
    if not is_admin(message.from_user.id):
        return

    await message.answer(
        "⚙️ <b>Настройки автоматической генерации</b>\n\n"
        "Выберите тип контента для включения/отключения автопостинга:\n\n"
        "• <b>Продукты</b> — ежедневно в 10:00\n"
        "• <b>Мотивация</b> — ежедневно в 08:00\n"
        "• <b>Советы</b> — через день в 14:00\n"
        "• <b>Новости</b> — пн/ср/пт в 12:00\n"
        "• <b>Истории успеха</b> — вт/сб в 18:00\n"
        "• <b>Промо</b> — чт/вс в 16:00\n\n"
        "Нажмите на тип, чтобы включить/выключить.",
        reply_markup=Keyboards.auto_schedule_settings()
    )


@router.message(Command("analytics"))
async def cmd_analytics(message: Message):
    """Обработчик команды /analytics - детальная аналитика постов"""
    if not is_admin(message.from_user.id):
        return

    # Парсим аргументы команды
    args = message.text.split(maxsplit=1)
    days = 7  # По умолчанию 7 дней

    if len(args) > 1:
        try:
            days = int(args[1])
            if days < 1 or days > 365:
                days = 7
        except ValueError:
            days = 7

    status_msg = await message.answer("⏳ Собираю аналитику...")

    try:
        async with AsyncSessionLocal() as session:
            analytics_service = AnalyticsService(session)
            dashboard = await analytics_service.format_dashboard(days=days)

        await status_msg.delete()
        await message.answer(dashboard, reply_markup=Keyboards.analytics_menu())

    except Exception as e:
        logger.error(f"Error generating analytics: {e}")
        await status_msg.edit_text(
            f"❌ Ошибка при генерации аналитики:\n{str(e)}"
        )


@router.message(Command("update_stats"))
async def cmd_update_stats(message: Message):
    """Обработчик команды /update_stats - обновление статистики всех постов"""
    if not is_admin(message.from_user.id):
        return

    from aiogram import Bot

    status_msg = await message.answer("⏳ Обновляю статистику постов из Telegram...")

    try:
        async with AsyncSessionLocal() as session:
            # Получаем бота из message
            bot = message.bot
            stats_collector = StatsCollector(bot, session)

            # Обновляем все опубликованные посты
            updated_count = await stats_collector.update_all_published_posts()

        await status_msg.edit_text(
            f"✅ Статистика обновлена!\n\n"
            f"Обновлено постов: {updated_count}\n\n"
            f"Используйте /analytics для просмотра аналитики."
        )

    except Exception as e:
        logger.error(f"Error updating stats: {e}")
        await status_msg.edit_text(
            f"❌ Ошибка при обновлении статистики:\n{str(e)}"
        )


@router.message(Command("top"))
async def cmd_top(message: Message):
    """Обработчик команды /top - топ постов по метрикам"""
    if not is_admin(message.from_user.id):
        return

    # Парсим аргументы: /top [views|reactions|engagement] [количество] [дней]
    args = message.text.split()
    sort_by = args[1] if len(args) > 1 else 'engagement'
    limit = int(args[2]) if len(args) > 2 and args[2].isdigit() else 10
    days = int(args[3]) if len(args) > 3 and args[3].isdigit() else 30

    if sort_by not in ['views', 'reactions', 'engagement']:
        sort_by = 'engagement'

    status_msg = await message.answer("⏳ Получаю топ постов...")

    try:
        async with AsyncSessionLocal() as session:
            analytics_service = AnalyticsService(session)
            top_posts = await analytics_service.get_top_posts(
                limit=limit,
                days=days,
                sort_by=sort_by
            )

        if not top_posts:
            await status_msg.edit_text(
                f"📭 Нет опубликованных постов за последние {days} дней"
            )
            return

        sort_names = {
            'views': 'просмотрам',
            'reactions': 'реакциям',
            'engagement': 'вовлеченности'
        }

        type_names = {
            'product': '🛍️',
            'motivation': '💪',
            'news': '📰',
            'tips': '💡',
            'success_story': '⭐',
            'promo': '🎁'
        }

        response = f"🏆 <b>Топ-{limit} постов</b> (по {sort_names[sort_by]})\n"
        response += f"<i>За последние {days} дней</i>\n\n"

        for i, post in enumerate(top_posts, 1):
            emoji = type_names.get(post['type'], '📝')
            response += f"{i}. {emoji} ID #{post['id']}\n"
            response += f"   👁 {post['views']} | ❤️ {post['reactions']} | "
            response += f"📊 {post['engagement_rate']:.2f}%\n"
            response += f"   <i>{post['content_preview']}</i>\n\n"

        await status_msg.edit_text(response)

    except Exception as e:
        logger.error(f"Error getting top posts: {e}")
        await status_msg.edit_text(
            f"❌ Ошибка при получении топ постов:\n{str(e)}"
        )


@router.message(Command("traffic"))
async def cmd_traffic(message: Message):
    """
    /traffic — Статус Traffic Engine.

    Показывает:
    - Аккаунты (статус, сегмент, действия за сегодня)
    - Последний коммент (текст + канал + время)
    - Общая статистика за сегодня
    """
    if not is_admin(message.from_user.id):
        return

    status_msg = await message.answer("Загружаю статистику Traffic Engine...")

    try:
        # Импортируем TE модели (они могут не быть доступны если TE не установлен)
        from traffic_engine.database.models import UserBotAccount, TrafficAction, TargetChannel
        from traffic_engine.database import get_session as te_get_session

        async with te_get_session() as session:
            # 1. Аккаунты
            accounts_result = await session.execute(
                select(UserBotAccount).order_by(UserBotAccount.id)
            )
            accounts = accounts_result.scalars().all()

            # 2. Действия за сегодня
            today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            actions_result = await session.execute(
                select(
                    TrafficAction.action_type,
                    TrafficAction.status,
                    func.count(TrafficAction.id).label("cnt"),
                ).where(
                    TrafficAction.created_at >= today,
                ).group_by(
                    TrafficAction.action_type,
                    TrafficAction.status,
                )
            )
            action_stats = {}
            for row in actions_result.all():
                key = f"{row[0]}_{row[1]}"
                action_stats[key] = row[2]

            # 3. Последний успешный коммент
            last_comment_result = await session.execute(
                select(TrafficAction).where(
                    TrafficAction.action_type == "comment",
                    TrafficAction.status == "success",
                ).order_by(TrafficAction.created_at.desc()).limit(1)
            )
            last_comment = last_comment_result.scalar_one_or_none()

            # 4. Replies за сегодня
            replies_result = await session.execute(
                select(func.count(TrafficAction.id)).where(
                    TrafficAction.got_reply == True,
                    TrafficAction.created_at >= today,
                )
            )
            replies_today = replies_result.scalar() or 0

        # Формируем отчёт
        now = datetime.utcnow()
        response = "📊 <b>Traffic Engine — Статус</b>\n"
        response += f"<i>{now.strftime('%d.%m.%Y %H:%M')} UTC</i>\n\n"

        # Аккаунты
        response += "<b>👤 Аккаунты:</b>\n"
        for acc in accounts:
            status_emoji = {"active": "🟢", "warming": "🟡", "banned": "🔴", "disabled": "⚪"}.get(acc.status, "❓")
            segment = acc.segment or "—"
            cooldown = ""
            if acc.cooldown_until and acc.cooldown_until > now:
                mins_left = int((acc.cooldown_until - now).total_seconds() / 60)
                cooldown = f" ⏸ {mins_left}мин"

            response += (
                f"  {status_emoji} {acc.phone} "
                f"[{segment}] "
                f"💬{acc.daily_comments} "
                f"👁{acc.daily_story_views} "
                f"📨{acc.daily_invites}"
                f"{cooldown}\n"
            )

        # Статистика за сегодня
        comments_ok = action_stats.get("comment_success", 0)
        comments_fail = action_stats.get("comment_failed", 0)
        comments_flood = action_stats.get("comment_flood_wait", 0)
        stories_ok = action_stats.get("story_view_success", 0)
        invites_ok = action_stats.get("invite_success", 0)

        response += f"\n<b>📈 Сегодня:</b>\n"
        response += f"  💬 Комменты: {comments_ok} ✅ / {comments_fail} ❌ / {comments_flood} ⏳\n"
        response += f"  👁 Сторис: {stories_ok}\n"
        response += f"  📨 Инвайты: {invites_ok}\n"
        response += f"  💬→ Ответы на комменты: {replies_today}\n"

        # Последний коммент
        if last_comment:
            comment_time = last_comment.created_at.strftime("%H:%M") if last_comment.created_at else "?"
            comment_preview = (last_comment.content or "")[:80]
            strategy = last_comment.strategy_used or "?"
            topic = last_comment.post_topic or "?"
            relevance = f"{last_comment.relevance_score:.2f}" if last_comment.relevance_score else "?"

            response += f"\n<b>💬 Последний коммент ({comment_time}):</b>\n"
            response += f"  📝 {comment_preview}...\n"
            response += f"  🎯 Стратегия: {strategy} | Тема: {topic}\n"
            response += f"  📊 Релевантность: {relevance}\n"

        await status_msg.edit_text(response, parse_mode="HTML")

    except ImportError:
        await status_msg.edit_text(
            "❌ Traffic Engine модели недоступны.\n"
            "Убедитесь что traffic_engine установлен."
        )
    except Exception as e:
        logger.error(f"Error in /traffic: {e}")
        await status_msg.edit_text(f"❌ Ошибка:\n{str(e)[:300]}")


# === Traffic Engine: расширенный мониторинг ===

# Диагнозы (дублируем из notifier для /errors)
_TE_DIAGNOSIS = {
    "FloodWait": "Уменьши лимиты или увеличь интервалы",
    "ChatWriteForbidden": "Проверь дискуссионную группу канала",
    "UserBannedInChannel": "Убери канал из списка для этого аккаунта",
    "SlowModeWait": "Увеличь min_comment_interval_sec",
    "AuthKeyDuplicated": "Убедись что работает только один экземпляр",
    "ChannelPrivate": "Канал стал приватным",
    "AI_GenerationFailed": "Проверь API ключи AI провайдера",
    "InviteFailed": "Проверь права аккаунта на инвайты",
}


@router.callback_query(F.data == "te:status")
async def callback_te_status(callback: CallbackQuery):
    """Callback: статус TE (= /traffic)"""
    if not is_admin(callback.from_user.id):
        return
    await callback.answer()
    # Создаём фейковое сообщение для вызова cmd_traffic
    await cmd_traffic(callback.message)


@router.callback_query(F.data == "te:accounts")
async def callback_te_accounts(callback: CallbackQuery):
    """Callback: аккаунты TE (= /accounts)"""
    if not is_admin(callback.from_user.id):
        return
    await callback.answer()
    await _show_accounts(callback.message, edit=True)


@router.callback_query(F.data == "te:errors")
async def callback_te_errors(callback: CallbackQuery):
    """Callback: ошибки TE (= /errors)"""
    if not is_admin(callback.from_user.id):
        return
    await callback.answer()
    await _show_errors(callback.message, edit=True)


@router.callback_query(F.data.startswith("te:acc_detail:"))
async def callback_te_account_detail(callback: CallbackQuery):
    """Callback: детали аккаунта"""
    if not is_admin(callback.from_user.id):
        return
    await callback.answer()

    account_id = int(callback.data.split(":")[-1])
    await _show_account_detail(callback.message, account_id)


@router.message(Command("accounts"))
async def cmd_accounts(message: Message):
    """/accounts — Аккаунты Traffic Engine с последними действиями"""
    if not is_admin(message.from_user.id):
        return
    await _show_accounts(message, edit=False)


@router.message(Command("errors"))
async def cmd_errors(message: Message):
    """/errors — Ошибки Traffic Engine за 24 часа"""
    if not is_admin(message.from_user.id):
        return
    await _show_errors(message, edit=False)


async def _show_accounts(message: Message, edit: bool = False):
    """Показать все аккаунты TE с последними действиями."""
    try:
        from traffic_engine.database.models import UserBotAccount, TrafficAction, TargetChannel
        from traffic_engine.database import get_session as te_get_session

        async with te_get_session() as session:
            # Аккаунты
            accounts_result = await session.execute(
                select(UserBotAccount).order_by(UserBotAccount.id)
            )
            accounts = accounts_result.scalars().all()

            if not accounts:
                text = "👤 <b>Аккаунты Traffic Engine</b>\n\n<i>Нет аккаунтов. Добавь аккаунт через скрипт.</i>"
                if edit:
                    await message.edit_text(text, parse_mode="HTML")
                else:
                    await message.answer(text, parse_mode="HTML")
                return

            # Каналы (для маппинга channel_id -> username)
            channels_result = await session.execute(select(TargetChannel))
            channels_map = {ch.channel_id: ch.username for ch in channels_result.scalars().all()}

            now = datetime.utcnow()
            today = now.replace(hour=0, minute=0, second=0, microsecond=0)

            response = "👤 <b>Аккаунты Traffic Engine</b>\n\n"

            for acc in accounts:
                # Статус emoji
                status_emoji = {
                    "active": "🟢", "warming": "🟡", "banned": "🔴",
                    "disabled": "⚪", "cooldown": "⏸"
                }.get(acc.status, "❓")

                # Маскируем телефон
                phone = acc.phone
                phone_masked = phone[:4] + "***" + phone[-2:] if len(phone) > 6 else phone
                segment = acc.segment or "—"

                # Cooldown
                cooldown = ""
                if acc.cooldown_until and acc.cooldown_until > now:
                    mins_left = int((acc.cooldown_until - now).total_seconds() / 60)
                    cooldown = f" ⏸ {mins_left}мин"

                # День прогрева
                warmup = ""
                if acc.status == "warming" and hasattr(acc, "warmup_started_at") and acc.warmup_started_at:
                    days = (now - acc.warmup_started_at).days + 1
                    warmup = f" День {days}/14"

                # Лимиты
                comments_limit = getattr(acc, "daily_comments", 0) or 0
                stories_limit = getattr(acc, "daily_story_views", 0) or 0
                invites_limit = getattr(acc, "daily_invites", 0) or 0

                response += (
                    f"{status_emoji} <code>{phone_masked}</code> [{segment}]{warmup}{cooldown}\n"
                    f"  Сегодня: 💬{comments_limit} 👁{stories_limit} 📨{invites_limit}\n"
                )

                # Последние 5 действий этого аккаунта
                actions_result = await session.execute(
                    select(TrafficAction).where(
                        TrafficAction.account_id == acc.id,
                    ).order_by(TrafficAction.created_at.desc()).limit(5)
                )
                actions = actions_result.scalars().all()

                for action in actions:
                    time_str = action.created_at.strftime("%H:%M") if action.created_at else "?"

                    # Тип действия emoji
                    type_emoji = {
                        "comment": "💬", "story_view": "👁",
                        "story_reaction": "🔥", "invite": "📨",
                    }.get(action.action_type, "❓")

                    # Статус
                    status_icon = "✅" if action.status == "success" else "❌"

                    # Канал
                    channel_name = ""
                    if action.target_channel_id and action.target_channel_id in channels_map:
                        channel_name = f" @{channels_map[action.target_channel_id]}"
                    elif action.target_channel_id:
                        channel_name = f" ch:{action.target_channel_id}"

                    # Контент или ошибка
                    detail = ""
                    if action.status == "success" and action.content:
                        detail = f' "{action.content[:40]}..."'
                    elif action.status != "success" and action.error_message:
                        detail = f" {action.error_message[:50]}"

                    response += f"  {time_str} {type_emoji}{channel_name} {status_icon}{detail}\n"

                response += "\n"

            # Обрезаем если слишком длинное
            if len(response) > 4000:
                response = response[:3950] + "\n\n<i>...обрезано. Нажми кнопку аккаунта для деталей.</i>"

        if edit:
            await message.edit_text(
                response, parse_mode="HTML",
                reply_markup=Keyboards.account_detail_buttons(accounts) if len(accounts) <= 10 else None,
            )
        else:
            await message.answer(
                response, parse_mode="HTML",
                reply_markup=Keyboards.account_detail_buttons(accounts) if len(accounts) <= 10 else None,
            )

    except ImportError:
        text = "❌ Traffic Engine модели недоступны."
        if edit:
            await message.edit_text(text)
        else:
            await message.answer(text)
    except Exception as e:
        logger.error(f"Error in /accounts: {e}")
        text = f"❌ Ошибка:\n{str(e)[:300]}"
        if edit:
            await message.edit_text(text)
        else:
            await message.answer(text)


async def _show_account_detail(message: Message, account_id: int):
    """Показать детальный лог действий аккаунта (20 последних)."""
    try:
        from traffic_engine.database.models import UserBotAccount, TrafficAction, TargetChannel
        from traffic_engine.database import get_session as te_get_session

        async with te_get_session() as session:
            # Аккаунт
            acc = await session.get(UserBotAccount, account_id)
            if not acc:
                await message.edit_text("❌ Аккаунт не найден")
                return

            # Каналы
            channels_result = await session.execute(select(TargetChannel))
            channels_map = {ch.channel_id: ch.username for ch in channels_result.scalars().all()}

            phone_masked = acc.phone[:4] + "***" + acc.phone[-2:] if len(acc.phone) > 6 else acc.phone

            response = f"📋 <b>Аккаунт {phone_masked} [{acc.segment or '—'}]</b>\n"
            response += f"Статус: {acc.status}\n\n"
            response += "<b>Последние 20 действий:</b>\n\n"

            # Последние 20 действий
            actions_result = await session.execute(
                select(TrafficAction).where(
                    TrafficAction.account_id == account_id,
                ).order_by(TrafficAction.created_at.desc()).limit(20)
            )
            actions = actions_result.scalars().all()

            if not actions:
                response += "<i>Нет действий</i>"
            else:
                for action in actions:
                    time_str = action.created_at.strftime("%d.%m %H:%M") if action.created_at else "?"

                    type_emoji = {
                        "comment": "💬", "story_view": "👁",
                        "story_reaction": "🔥", "invite": "📨",
                    }.get(action.action_type, "❓")

                    status_icon = "✅" if action.status == "success" else "❌"

                    channel_name = ""
                    if action.target_channel_id and action.target_channel_id in channels_map:
                        channel_name = f"@{channels_map[action.target_channel_id]}"

                    response += f"{time_str} {type_emoji} {channel_name} {status_icon}\n"

                    if action.status == "success" and action.content:
                        response += f"  <i>{action.content[:60]}</i>\n"
                        if action.strategy_used:
                            response += f"  Стратегия: {action.strategy_used}"
                            if action.relevance_score:
                                response += f" | Рел: {action.relevance_score:.2f}"
                            response += "\n"
                        if action.got_reply:
                            response += f"  💬→ Получен ответ ({action.reply_count or 1})\n"
                    elif action.error_message:
                        response += f"  ⚠️ {action.error_message[:80]}\n"

                    response += "\n"

            if len(response) > 4000:
                response = response[:3950] + "\n\n<i>...обрезано</i>"

            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            from aiogram.utils.keyboard import InlineKeyboardBuilder
            back_kb = InlineKeyboardBuilder()
            back_kb.row(InlineKeyboardButton(text="🔙 К аккаунтам", callback_data="te:accounts"))
            await message.edit_text(response, parse_mode="HTML", reply_markup=back_kb.as_markup())

    except Exception as e:
        logger.error(f"Error in account detail: {e}")
        await message.edit_text(f"❌ Ошибка:\n{str(e)[:300]}")


async def _show_errors(message: Message, edit: bool = False):
    """Показать ошибки TE за 24 часа, сгруппированные по типу."""
    try:
        from traffic_engine.database.models import TrafficAction, UserBotAccount, TargetChannel
        from traffic_engine.database import get_session as te_get_session
        from sqlalchemy import text

        async with te_get_session() as session:
            # Ошибки за 24 часа с группировкой
            yesterday = datetime.utcnow() - timedelta(hours=24)

            errors_result = await session.execute(
                text("""
                    SELECT
                        CASE
                            WHEN error_message LIKE 'FloodWait%' THEN 'FloodWait'
                            WHEN error_message LIKE '%ChatWriteForbidden%' THEN 'ChatWriteForbidden'
                            WHEN error_message LIKE '%Banned%' THEN 'UserBannedInChannel'
                            WHEN error_message LIKE '%SlowMode%' THEN 'SlowModeWait'
                            WHEN error_message LIKE '%AuthKeyDuplicated%' THEN 'AuthKeyDuplicated'
                            WHEN error_message LIKE '%ChannelPrivate%' THEN 'ChannelPrivate'
                            WHEN error_message LIKE '%discussion%' THEN 'ChatWriteForbidden'
                            WHEN error_message LIKE '%AI%' OR error_message LIKE '%generat%' THEN 'AI_GenerationFailed'
                            ELSE 'Other'
                        END as error_category,
                        COUNT(*) as cnt,
                        MAX(created_at) as last_at,
                        COUNT(DISTINCT account_id) as accounts_affected,
                        COUNT(DISTINCT target_channel_id) as channels_affected
                    FROM traffic_actions
                    WHERE status != 'success'
                      AND created_at >= :yesterday
                      AND error_message IS NOT NULL
                    GROUP BY error_category
                    ORDER BY cnt DESC
                """),
                {"yesterday": yesterday},
            )
            error_groups = errors_result.fetchall()

            if not error_groups:
                text_response = "❌ <b>Ошибки Traffic Engine (24ч)</b>\n\n✅ Ошибок нет!"
                if edit:
                    await message.edit_text(text_response, parse_mode="HTML")
                else:
                    await message.answer(text_response, parse_mode="HTML")
                return

            # Собираем детали: какие аккаунты и каналы
            details_result = await session.execute(
                text("""
                    SELECT
                        ta.account_id, a.phone, a.segment,
                        ta.target_channel_id, tc.username as channel_username,
                        ta.error_message, ta.created_at
                    FROM traffic_actions ta
                    LEFT JOIN traffic_userbot_accounts a ON a.id = ta.account_id
                    LEFT JOIN traffic_target_channels tc ON tc.channel_id = ta.target_channel_id
                    WHERE ta.status != 'success'
                      AND ta.created_at >= :yesterday
                      AND ta.error_message IS NOT NULL
                    ORDER BY ta.created_at DESC
                """),
                {"yesterday": yesterday},
            )
            all_errors = details_result.fetchall()

            # Группируем по категории
            errors_by_cat = {}
            for row in all_errors:
                err_msg = row.error_message or ""
                if "FloodWait" in err_msg:
                    cat = "FloodWait"
                elif "ChatWriteForbidden" in err_msg or "discussion" in err_msg:
                    cat = "ChatWriteForbidden"
                elif "Banned" in err_msg:
                    cat = "UserBannedInChannel"
                elif "SlowMode" in err_msg:
                    cat = "SlowModeWait"
                elif "AuthKeyDuplicated" in err_msg:
                    cat = "AuthKeyDuplicated"
                elif "ChannelPrivate" in err_msg:
                    cat = "ChannelPrivate"
                elif "AI" in err_msg or "generat" in err_msg:
                    cat = "AI_GenerationFailed"
                else:
                    cat = "Other"

                if cat not in errors_by_cat:
                    errors_by_cat[cat] = {"phones": set(), "channels": set()}
                if row.phone:
                    phone_masked = row.phone[:4] + "***" + row.phone[-2:] if len(row.phone) > 6 else row.phone
                    errors_by_cat[cat]["phones"].add(phone_masked)
                if row.channel_username:
                    errors_by_cat[cat]["channels"].add(row.channel_username)

            # Формируем отчёт
            total_errors = sum(row.cnt for row in error_groups)
            response = f"❌ <b>Ошибки Traffic Engine (24ч)</b>\n"
            response += f"Всего: {total_errors} ошибок\n\n"

            for row in error_groups:
                cat = row.error_category
                count = row.cnt
                last_at = row.last_at.strftime("%H:%M") if row.last_at else "?"

                diagnosis = _TE_DIAGNOSIS.get(cat, "Проверь логи")
                details = errors_by_cat.get(cat, {"phones": set(), "channels": set()})

                response += f"<b>{cat}</b>: {count} раз (последний: {last_at})\n"
                if details["phones"]:
                    response += f"  Аккаунты: {', '.join(sorted(details['phones']))}\n"
                if details["channels"]:
                    response += f"  Каналы: {', '.join('@' + c for c in sorted(details['channels']))}\n"
                response += f"  💡 {diagnosis}\n\n"

            if len(response) > 4000:
                response = response[:3950] + "\n\n<i>...обрезано</i>"

        if edit:
            await message.edit_text(response, parse_mode="HTML")
        else:
            await message.answer(response, parse_mode="HTML")

    except ImportError:
        text_response = "❌ Traffic Engine модели недоступны."
        if edit:
            await message.edit_text(text_response)
        else:
            await message.answer(text_response)
    except Exception as e:
        logger.error(f"Error in /errors: {e}")
        text_response = f"❌ Ошибка:\n{str(e)[:300]}"
        if edit:
            await message.edit_text(text_response)
        else:
            await message.answer(text_response)


# === AI Content Director ===

@router.message(Command("plan"))
async def cmd_plan(message: Message):
    """
    /plan [segment] — Контент-план (AI Director).

    Показывает активный план или генерирует новый.
    Без аргументов показывает план для segment=zozh.
    """
    if not is_admin(message.from_user.id):
        return

    args = message.text.split(maxsplit=1)
    segment = args[1].strip() if len(args) > 1 else "zozh"

    status_msg = await message.answer(f"⏳ Загружаю контент-план для {segment}...")

    try:
        from content_manager_bot.director import get_editorial_planner

        planner = get_editorial_planner()
        plan = await planner.get_active_plan(segment)

        if not plan:
            await status_msg.edit_text(
                f"📋 Нет активного плана для <b>{segment}</b>.\n\n"
                f"Генерирую новый...",
                parse_mode="HTML",
            )
            result = await planner.generate_weekly_plan(segment)
            if not result:
                await status_msg.edit_text("❌ Не удалось сгенерировать план. Проверь логи.")
                return
            plan = await planner.get_active_plan(segment)
            if not plan:
                await status_msg.edit_text("❌ План создан, но не найден.")
                return

        # Форматируем план
        slots = plan.get("slots", [])
        used = plan.get("used", 0)
        total = plan.get("total", len(slots))

        response = f"📋 <b>Контент-план [{segment}]</b>\n"
        response += f"Неделя: {plan.get('week_start', '?')}\n"
        response += f"Прогресс: {used}/{total}\n\n"

        energy_emoji = {"low": "🔵", "medium": "🟡", "high": "🔴"}
        role_emoji = {
            "standalone": "📄", "thread_start": "🔗",
            "thread_continue": "➡️", "thread_payoff": "🎯",
        }

        for i, slot in enumerate(slots):
            marker = "✅" if i < used else "⬜"
            e = energy_emoji.get(slot.get("energy", "medium"), "⚪")
            r = role_emoji.get(slot.get("narrative_role", "standalone"), "📄")
            pt = slot.get("post_type", "?")
            topic = slot.get("topic_hint", "")[:60]
            day = slot.get("day", "?")

            response += f"{marker} Д{day} {e}{r} <b>{pt}</b>\n"
            if topic:
                response += f"    <i>{topic}</i>\n"

        if len(response) > 4000:
            response = response[:3950] + "\n\n<i>...обрезано</i>"

        await status_msg.edit_text(response, parse_mode="HTML")

    except Exception as e:
        logger.error(f"Error in /plan: {e}")
        await status_msg.edit_text(f"❌ Ошибка:\n{str(e)[:300]}")


@router.message(Command("review"))
async def cmd_review(message: Message):
    """
    /review [segment] — AI Self-Review контента.

    Показывает последний review или запускает новый.
    """
    if not is_admin(message.from_user.id):
        return

    args = message.text.split(maxsplit=1)
    segment = args[1].strip() if len(args) > 1 else "zozh"

    status_msg = await message.answer(f"⏳ Загружаю self-review для {segment}...")

    try:
        from content_manager_bot.director import get_self_reviewer

        reviewer = get_self_reviewer()
        review_data = await reviewer.get_last_review(segment)

        if not review_data:
            await status_msg.edit_text(
                f"🔍 Нет ревью для <b>{segment}</b>. Запускаю анализ...",
                parse_mode="HTML",
            )
            result = await reviewer.run_review(segment)
            if not result:
                await status_msg.edit_text("❌ Не удалось провести ревью. Мало постов или ошибка AI.")
                return
            review_data = await reviewer.get_last_review(segment)
            if not review_data:
                await status_msg.edit_text("❌ Ревью создан, но не найден.")
                return

        review = review_data.get("review", {})
        posts_reviewed = review_data.get("posts_reviewed", 0)
        created = review_data.get("created_at", "?")
        if isinstance(created, str) and len(created) > 19:
            created = created[:19]

        response = f"🔍 <b>Self-Review [{segment}]</b>\n"
        response += f"Проанализировано: {posts_reviewed} постов\n"
        response += f"Дата: {created}\n\n"

        strengths = review.get("strengths", [])
        if strengths:
            response += "<b>✅ Сильные стороны:</b>\n"
            for s in strengths:
                response += f"  • {s}\n"
            response += "\n"

        weaknesses = review.get("weaknesses", [])
        if weaknesses:
            response += "<b>⚠️ Слабые стороны:</b>\n"
            for w in weaknesses:
                response += f"  • {w}\n"
            response += "\n"

        recommendations = review.get("recommendations", [])
        if recommendations:
            response += "<b>💡 Рекомендации:</b>\n"
            for r in recommendations:
                response += f"  • {r}\n"
            response += "\n"

        topics = review.get("topic_suggestions", [])
        if topics:
            response += "<b>🎯 Предложенные темы:</b>\n"
            for t in topics:
                response += f"  • {t}\n"
            response += "\n"

        avoid = review.get("avoid", [])
        if avoid:
            response += "<b>🚫 Избегать:</b>\n"
            for a in avoid:
                response += f"  • {a}\n"

        if len(response) > 4000:
            response = response[:3950] + "\n\n<i>...обрезано</i>"

        await status_msg.edit_text(response, parse_mode="HTML")

    except Exception as e:
        logger.error(f"Error in /review: {e}")
        await status_msg.edit_text(f"❌ Ошибка:\n{str(e)[:300]}")


@router.message(Command("insights"))
async def cmd_insights(message: Message):
    """
    /insights [segment] — Performance Insights (LinUCB + metrics).

    Показывает аналитику по типам постов, лучшие часы, рекомендации.
    """
    if not is_admin(message.from_user.id):
        return

    args = message.text.split(maxsplit=1)
    segment = args[1].strip() if len(args) > 1 else "zozh"

    status_msg = await message.answer(f"⏳ Считаю insights для {segment}...")

    try:
        from content_manager_bot.director import get_performance_analyzer

        analyzer = get_performance_analyzer()
        insights = await analyzer.get_insights(segment)

        await status_msg.edit_text(insights, parse_mode="HTML")

    except Exception as e:
        logger.error(f"Error in /insights: {e}")
        await status_msg.edit_text(f"❌ Ошибка:\n{str(e)[:300]}")


@router.message(Command("competitors"))
async def cmd_competitors(message: Message):
    """
    /competitors [segment] — Анализ конкурентов.

    Показывает последний анализ или запускает новый.
    """
    if not is_admin(message.from_user.id):
        return

    args = message.text.split(maxsplit=1)
    segment = args[1].strip() if len(args) > 1 else "zozh"

    status_msg = await message.answer(f"⏳ Загружаю анализ конкурентов для {segment}...")

    try:
        from content_manager_bot.director import (
            get_competitor_analyzer,
            get_trend_detector,
        )

        analyzer = get_competitor_analyzer()

        # Сначала пробуем показать кэшированные insights
        insights_str = await analyzer.get_competitor_insights(segment)

        if not insights_str:
            await status_msg.edit_text(
                f"🔍 Нет данных о конкурентах для <b>{segment}</b>. Запускаю анализ...\n"
                f"Это может занять 30-60 секунд.",
                parse_mode="HTML",
            )
            result = await analyzer.analyze(segment)
            if not result:
                await status_msg.edit_text(
                    "❌ Не удалось проанализировать конкурентов.\n"
                    "Проверь: каналы конкурентов настроены? Telethon подключен?"
                )
                return
            insights_str = await analyzer.get_competitor_insights(segment)

        # Добавляем trending
        detector = get_trend_detector()
        trend_context = await detector.get_trend_context(segment)

        response = f"<b>🏆 Конкуренты [{segment}]</b>\n\n"
        response += insights_str or "Нет данных"

        if trend_context:
            response += f"\n\n📈 {trend_context}"

        if len(response) > 4000:
            response = response[:3950] + "\n\n<i>...обрезано</i>"

        await status_msg.edit_text(response, parse_mode="HTML")

    except Exception as e:
        logger.error(f"Error in /competitors: {e}")
        await status_msg.edit_text(f"❌ Ошибка:\n{str(e)[:300]}")


# === Дневник ===

@router.message(Command("diary"))
async def cmd_diary(message: Message):
    """Команда /diary — показать дневник"""
    if not is_admin(message.from_user.id):
        return
    await show_diary(message)


@router.callback_query(F.data == "diary:new")
async def callback_diary_new(callback: CallbackQuery, state: FSMContext):
    """Начать ввод новой записи дневника"""
    if not is_admin(callback.from_user.id):
        return

    await state.set_state(DiaryStates.waiting_for_entry)
    await callback.message.answer(
        "📓 <b>Новая запись</b>\n\n"
        "Напиши что произошло, о чём думаешь, какие идеи.\n"
        "Бот будет использовать это при генерации постов.\n\n"
        "<i>Отправь текст сообщением:</i>"
    )
    await callback.answer()


@router.message(DiaryStates.waiting_for_entry)
async def diary_save_entry(message: Message, state: FSMContext):
    """Сохранить запись дневника"""
    if not is_admin(message.from_user.id):
        await state.clear()
        return

    entry_text = message.text
    if not entry_text or len(entry_text.strip()) < 3:
        await message.answer("❌ Запись слишком короткая. Напиши хотя бы пару слов.")
        return

    async with AsyncSessionLocal() as session:
        entry = DiaryEntry(
            admin_id=message.from_user.id,
            entry_text=entry_text.strip()
        )
        session.add(entry)
        await session.commit()

    await state.clear()

    await message.answer(
        "✅ <b>Запись сохранена!</b>\n\n"
        "Теперь бот будет учитывать её при генерации постов.",
        reply_markup=Keyboards.reply_main_menu()
    )
    logger.info(f"Diary entry saved by admin {message.from_user.id}, length={len(entry_text)}")
