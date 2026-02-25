"""
Планировщик автоматической генерации и публикации контента
"""
import asyncio
import random
from datetime import datetime, timedelta
from typing import Optional, List
from aiogram import Bot
from loguru import logger
from sqlalchemy import select, and_, func

from shared.config.settings import settings
from shared.database.base import AsyncSessionLocal
from content_manager_bot.database.models import Post, ContentSchedule
from content_manager_bot.database.funnel_models import ChannelTier, InviteLink, TierLevel
from content_manager_bot.ai.content_generator import ContentGenerator
from content_manager_bot.ai.prompts import FunnelPrompts
from content_manager_bot.utils.keyboards import Keyboards
from content_manager_bot.analytics import StatsCollector
from content_manager_bot.routing.channel_router import ChannelRouter
from content_manager_bot.invites.invite_manager import InviteManager
from content_manager_bot.director import (
    get_editorial_planner,
    get_channel_memory,
    get_self_reviewer,
    get_competitor_analyzer,
    get_performance_analyzer,
)


class ContentScheduler:
    """
    Планировщик для автоматической публикации запланированных постов
    и генерации нового контента по расписанию
    """

    # Конфигурация расписания для каждого типа контента
    SCHEDULE_CONFIG = {
        "product": {"hours": 24, "desc": "ежедневно в 10:00"},
        "motivation": {"hours": 24, "desc": "ежедневно в 08:00"},
        "tips": {"hours": 48, "desc": "через день в 14:00"},
        "news": {"hours": 56, "desc": "пн/ср/пт в 12:00"},
        "success_story": {"hours": 84, "desc": "вт/сб в 18:00"},
        "promo": {"hours": 84, "desc": "чт/вс в 16:00"},
    }

    def __init__(self, bot: Bot):
        """
        Инициализация планировщика

        Args:
            bot: Экземпляр бота для публикации
        """
        self.bot = bot
        self.content_generator = ContentGenerator()
        self.running = False
        self._task: Optional[asyncio.Task] = None
        self._last_stats_update: Optional[datetime] = None
        self._daily_report_sent_today: bool = False
        self._last_director_check: Optional[datetime] = None
        logger.info("ContentScheduler initialized")

    async def start(self):
        """Запуск планировщика"""
        if self.running:
            logger.warning("Scheduler already running")
            return

        self.running = True
        self._task = asyncio.create_task(self._scheduler_loop())
        logger.info("ContentScheduler started")

    async def stop(self):
        """Остановка планировщика"""
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("ContentScheduler stopped")

    async def _scheduler_loop(self):
        """Основной цикл планировщика"""
        while self.running:
            try:
                # Проверяем запланированные посты
                await self._publish_scheduled_posts()

                # Проверяем расписание автогенерации
                await self._check_auto_generation()

                # === Тематические каналы ===
                await self._check_thematic_channels()

                # === Воронка каналов ===
                # Проверяем нужно ли опубликовать инвайт-пост
                await self._check_invite_post_needed()

                # Удаляем истёкшие инвайт-посты
                await self._delete_expired_invite_posts()

                # Очищаем истёкшие инвайт-ссылки
                await self._cleanup_expired_invites()

                # Обновляем статистику постов (каждые 30 минут)
                await self._update_stats_if_needed()

                # Ежедневный отчёт Traffic Engine в 23:00 MSK (20:00 UTC)
                await self._check_daily_traffic_report()

                # AI Director: weekly tasks (competitor analysis, self-review)
                await self._check_director_tasks()

                # Ждём 60 секунд до следующей проверки
                await asyncio.sleep(60)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(60)

    async def _publish_scheduled_posts(self):
        """Публикация постов, время которых наступило"""
        async with AsyncSessionLocal() as session:
            now = datetime.utcnow()

            # Находим посты для публикации
            result = await session.execute(
                select(Post).where(
                    and_(
                        Post.status == "scheduled",
                        Post.scheduled_for <= now
                    )
                )
            )
            posts = result.scalars().all()

            if posts:
                logger.info(f"📤 Found {len(posts)} scheduled posts ready for publication")

            for post in posts:
                try:
                    logger.info(f"📢 Publishing scheduled post #{post.id} (type: {post.post_type}, scheduled_for: {post.scheduled_for})")
                    await self._publish_post(post, session)
                except Exception as e:
                    logger.error(f"❌ Error publishing scheduled post #{post.id}: {e}", exc_info=True)

    async def _publish_post(self, post: Post, session):
        """
        Публикация поста в группу с Topics или канал.
        Поддерживает публикацию с картинкой (send_photo) и без (send_message).
        Тематические каналы: если у поста есть segment, публикуем в соответствующий канал.

        Args:
            post: Пост для публикации
            session: Сессия БД
        """
        import base64
        from aiogram.types import BufferedInputFile

        try:
            # Определяем целевой канал
            target_chat = settings.channel_username  # по умолчанию — основной

            if post.segment and post.segment in settings.thematic_channels:
                target_chat = settings.thematic_channels[post.segment]
                logger.info(f"Publishing to thematic channel: {target_chat} (segment={post.segment})")

            # Для тематических каналов — без приписки куратора (другая аудитория)
            if post.segment:
                post_with_curator = post.content
            else:
                # Добавляем ссылку на куратора (только основной канал)
                post_with_curator = (
                    f"{post.content}\n\n"
                    f"━━━━━━━━━━━━━━━\n"
                    f"❓ Есть вопросы? Спроси AI-Куратора → {settings.curator_bot_username}"
                )

            message = None
            publish_target = target_chat

            # === ПУБЛИКАЦИЯ С КАРТИНКОЙ ===
            if post.image_url:
                try:
                    image_bytes = base64.b64decode(post.image_url)
                    image_file = BufferedInputFile(image_bytes, filename=f"post_{post.id}.jpg")

                    # Ограничение Telegram: caption max 1024 символа
                    caption = post_with_curator[:1024] if len(post_with_curator) > 1024 else post_with_curator

                    message = await self.bot.send_photo(
                        chat_id=target_chat,
                        photo=image_file,
                        caption=caption,
                        parse_mode="HTML"
                    )

                    logger.info(f"Published post #{post.id} WITH IMAGE to {publish_target}")

                    # Если текст длиннее 1024 символов - отправляем остаток
                    if len(post_with_curator) > 1024:
                        rest_text = post_with_curator[1024:]
                        await self.bot.send_message(
                            chat_id=target_chat,
                            text=rest_text,
                            parse_mode="HTML"
                        )

                except Exception as e:
                    logger.error(f"Error sending image for post #{post.id}: {e}, falling back to text")
                    # Fallback на текст
                    message = None

            # === ПУБЛИКАЦИЯ БЕЗ КАРТИНКИ (или fallback) ===
            if message is None:
                message = await self.bot.send_message(
                    chat_id=target_chat,
                    text=post_with_curator,
                    parse_mode="HTML"
                )
                logger.info(f"Published post #{post.id} (text only) to {publish_target}")

            # Обновляем статус
            post.status = "published"
            post.published_at = datetime.utcnow()
            post.channel_message_id = message.message_id

            await session.commit()

            logger.info(f"Scheduled post #{post.id} published to {publish_target}")

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

            # Создаём событие для curator_bot (рассылка уведомлений)
            try:
                from shared.database.models import SystemEvent

                event = SystemEvent(
                    event_type="post_published",
                    source="content_manager",
                    payload={
                        "post_id": post.id,
                        "post_type": post.post_type,
                        "content_preview": post.content[:200] if post.content else "",
                        "full_content": post.content,
                        "published_at": post.published_at.isoformat() if post.published_at else None,
                        "has_image": bool(post.image_url)
                    },
                    target_module="curator",
                    expires_at=datetime.utcnow() + timedelta(hours=72)
                )
                session.add(event)
                await session.commit()

                logger.info(f"Event 'post_published' created for post #{post.id}")
            except Exception as e:
                logger.error(f"Failed to create event for post #{post.id}: {e}")

            # Уведомляем админов
            await self._notify_admins(
                f"📢 Автопубликация\n\n"
                f"Пост #{post.id} опубликован в {publish_target} по расписанию."
                + (" (с картинкой)" if post.image_url else "")
            )

        except Exception as e:
            logger.error(f"Failed to publish post #{post.id}: {e}")
            raise

    async def _check_auto_generation(self):
        """Проверка расписания автоматической генерации"""
        async with AsyncSessionLocal() as session:
            now = datetime.utcnow()

            # Находим активные расписания, время которых наступило
            result = await session.execute(
                select(ContentSchedule).where(
                    and_(
                        ContentSchedule.is_active == True,
                        ContentSchedule.next_run <= now
                    )
                )
            )
            schedules = result.scalars().all()

            if schedules:
                logger.info(f"🤖 Found {len(schedules)} active schedules ready for auto-generation")

            for schedule in schedules:
                try:
                    logger.info(f"⚙️ Starting auto-generation for schedule #{schedule.id} (type: {schedule.post_type}, next_run: {schedule.next_run})")
                    await self._run_auto_generation(schedule, session)
                except Exception as e:
                    logger.error(f"❌ Error in auto generation for schedule #{schedule.id}: {e}", exc_info=True)

    async def _run_auto_generation(self, schedule: ContentSchedule, session):
        """
        Запуск автоматической генерации по расписанию

        Args:
            schedule: Расписание
            session: Сессия БД
        """
        logger.info(f"Running auto generation for schedule #{schedule.id} ({schedule.post_type})")

        # Генерируем пост
        content, prompt_used = await self.content_generator.generate_post(
            post_type=schedule.post_type
        )

        # Сохраняем как pending (требует модерации)
        post = Post(
            content=content,
            post_type=schedule.post_type,
            status="pending",
            generated_at=datetime.utcnow(),
            ai_model=settings.content_manager_ai_model,
            prompt_used=prompt_used
        )
        session.add(post)

        # Обновляем расписание
        schedule.last_run = datetime.utcnow()
        schedule.total_generated += 1

        # Вычисляем следующий запуск на основе конфига для типа контента
        config = self.SCHEDULE_CONFIG.get(schedule.post_type, {"hours": 24})
        schedule.next_run = datetime.utcnow() + timedelta(hours=config["hours"])

        await session.commit()
        await session.refresh(post)

        logger.info(
            f"✅ Auto-generated post #{post.id} ({schedule.post_type}). "
            f"Total generated: {schedule.total_generated}. "
            f"Next run: {schedule.next_run.strftime('%Y-%m-%d %H:%M UTC')} "
            f"(interval: {config['hours']}h - {config.get('desc', 'N/A')})"
        )

        # Отправляем пост админам сразу с кнопками модерации
        type_names = ContentGenerator.get_available_post_types()
        type_name = type_names.get(schedule.post_type, schedule.post_type)

        await self._send_post_for_moderation(
            post_id=post.id,
            content=content,
            post_type=type_name
        )

    async def _send_post_for_moderation(self, post_id: int, content: str, post_type: str):
        """
        Отправка поста админам с кнопками модерации

        Args:
            post_id: ID поста
            content: Текст поста
            post_type: Название типа поста
        """
        message_text = (
            f"🤖 <b>Автогенерация: {post_type}</b>\n"
            f"ID: #{post_id}\n\n"
            f"{content}\n\n"
            f"<i>Что делаем с постом?</i>"
        )

        for admin_id in settings.admin_ids_list:
            try:
                await self.bot.send_message(
                    chat_id=admin_id,
                    text=message_text,
                    reply_markup=Keyboards.post_moderation(post_id),
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"Failed to send post for moderation to admin {admin_id}: {e}")

    async def _notify_admins(self, message: str):
        """
        Уведомление всех админов

        Args:
            message: Текст уведомления
        """
        for admin_id in settings.admin_ids_list:
            try:
                await self.bot.send_message(chat_id=admin_id, text=message, parse_mode="HTML")
            except Exception as e:
                logger.error(f"Failed to notify admin {admin_id}: {e}")

    async def add_schedule(
        self,
        post_type: str,
        cron_expression: str = "0 9 * * *"
    ) -> ContentSchedule:
        """
        Добавление нового расписания автогенерации

        Args:
            post_type: Тип поста
            cron_expression: Cron выражение (по умолчанию каждый день в 9:00)

        Returns:
            ContentSchedule: Созданное расписание
        """
        async with AsyncSessionLocal() as session:
            schedule = ContentSchedule(
                post_type=post_type,
                cron_expression=cron_expression,
                is_active=True,
                next_run=datetime.utcnow() + timedelta(days=1)
            )
            session.add(schedule)
            await session.commit()
            await session.refresh(schedule)

            logger.info(f"Created schedule #{schedule.id} for {post_type}")
            return schedule

    async def get_schedules(self) -> List[ContentSchedule]:
        """
        Получение всех активных расписаний

        Returns:
            List[ContentSchedule]: Список расписаний
        """
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(ContentSchedule).where(ContentSchedule.is_active == True)
            )
            return result.scalars().all()

    async def toggle_schedule(self, schedule_id: int) -> bool:
        """
        Включение/выключение расписания

        Args:
            schedule_id: ID расписания

        Returns:
            bool: Новое состояние (True = активно)
        """
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(ContentSchedule).where(ContentSchedule.id == schedule_id)
            )
            schedule = result.scalar_one_or_none()

            if schedule:
                schedule.is_active = not schedule.is_active
                await session.commit()
                return schedule.is_active

            return False

    async def _update_stats_if_needed(self):
        """
        Обновление статистики постов (каждые 30 минут)
        """
        now = datetime.utcnow()

        # Проверяем, нужно ли обновлять статистику
        if self._last_stats_update:
            time_since_update = now - self._last_stats_update
            if time_since_update.total_seconds() < 1800:  # 30 минут
                return

        try:
            logger.info("📊 Starting automatic stats update...")

            async with AsyncSessionLocal() as session:
                stats_collector = StatsCollector(self.bot, session)

                # Обновляем статистику всех опубликованных постов
                updated_count = await stats_collector.update_all_published_posts()

                logger.info(f"✅ Stats updated for {updated_count} posts")

                # Обновляем время последнего обновления
                self._last_stats_update = now

        except Exception as e:
            logger.error(f"❌ Error updating stats: {e}")

    # ═══════════════════════════════════════════════════════════════
    # ТЕМАТИЧЕСКИЕ КАНАЛЫ: Автогенерация контента по сегментам
    # ═══════════════════════════════════════════════════════════════

    async def _check_thematic_channels(self):
        """
        Проверяет нужно ли сгенерировать и запланировать посты
        для тематических каналов (zozh, business).

        Логика:
        - Проверяем каждый час (MSK) из thematic_post_hours
        - Если сейчас подходящий час и нет запланированного поста — генерируем
        - Пост сначала отправляется на модерацию (pending)
        """
        thematic_channels = settings.thematic_channels
        if not thematic_channels:
            return

        now = datetime.utcnow()
        msk_hour = (now.hour + 3) % 24  # UTC → MSK

        # Проверяем только в подходящие часы
        if msk_hour not in settings.thematic_post_hours_list:
            return

        # Проверяем только в первые 2 минуты часа (чтобы не дублировать)
        if now.minute > 2:
            return

        for segment, channel_id in thematic_channels.items():
            try:
                await self._generate_thematic_post(segment, channel_id)
            except Exception as e:
                logger.error(f"Error generating thematic post for {segment}: {e}")

    async def _generate_thematic_post(self, segment: str, channel_id: str):
        """
        Генерирует пост для тематического канала.

        Args:
            segment: Сегмент (zozh, business)
            channel_id: ID или @username канала
        """
        # Проверяем нет ли уже pending/scheduled поста для этого сегмента за сегодня
        async with AsyncSessionLocal() as session:
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

            result = await session.execute(
                select(func.count(Post.id)).where(
                    and_(
                        Post.segment == segment,
                        Post.generated_at >= today_start,
                        Post.status.in_(["pending", "scheduled", "published"]),
                    )
                )
            )
            count = result.scalar() or 0

            if count >= settings.thematic_posts_per_day:
                return

            logger.info(f"Generating thematic post for segment={segment} (today: {count}/{settings.thematic_posts_per_day})")

            # AI Director: берём тип и тему из EditorialPlanner (если доступен)
            custom_topic = None
            post_type = None
            try:
                planner = get_editorial_planner()
                slot = await planner.get_next_planned_post(segment)
                if slot:
                    post_type = slot.get("post_type")
                    custom_topic = slot.get("topic_hint")
                    logger.info(f"[DIRECTOR] Using planned slot: type={post_type}, topic={custom_topic}")
            except Exception as e:
                logger.warning(f"[DIRECTOR] EditorialPlanner unavailable: {e}")

            # Fallback: случайный тип
            if not post_type:
                from content_manager_bot.ai.style_dna import get_content_segment_overlay
                overlay = get_content_segment_overlay(segment)
                post_types = overlay.get("post_types", ["observation", "thought", "journey"])
                post_type = random.choice(post_types)

            # Генерируем через 3-stage pipeline с сегментом
            content, prompt_used = await self.content_generator.generate_post(
                post_type=post_type,
                custom_topic=custom_topic,
                segment=segment,
            )

            # Сохраняем как pending (модерация)
            post = Post(
                content=content,
                post_type=post_type,
                status="pending",
                generated_at=datetime.utcnow(),
                ai_model=settings.content_manager_ai_model,
                prompt_used=prompt_used,
                segment=segment,
            )
            session.add(post)
            await session.commit()
            await session.refresh(post)

            logger.info(
                f"Thematic post #{post.id} generated for {segment} "
                f"(type={post_type}, {len(content)} chars)"
            )

            # Отправляем на модерацию с пометкой сегмента
            type_names = ContentGenerator.get_available_post_types()
            type_name = type_names.get(post_type, post_type)

            segment_names = {"zozh": "ЗОЖ", "business": "Бизнес", "mama": "Мамы", "student": "Студенты"}
            segment_label = segment_names.get(segment, segment)

            await self._send_thematic_post_for_moderation(
                post_id=post.id,
                content=content,
                post_type=type_name,
                segment=segment,
                segment_label=segment_label,
                channel_id=channel_id,
            )

    async def _send_thematic_post_for_moderation(
        self,
        post_id: int,
        content: str,
        post_type: str,
        segment: str,
        segment_label: str,
        channel_id: str,
    ):
        """
        Отправка тематического поста админам с кнопками модерации.
        """
        message_text = (
            f"📝 <b>Тематический канал: {segment_label}</b>\n"
            f"Тип: {post_type} | Канал: {channel_id}\n"
            f"ID: #{post_id}\n\n"
            f"{content}\n\n"
            f"<i>Что делаем с постом?</i>"
        )

        for admin_id in settings.admin_ids_list:
            try:
                await self.bot.send_message(
                    chat_id=admin_id,
                    text=message_text,
                    reply_markup=Keyboards.post_moderation(post_id),
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"Failed to send thematic post for moderation to admin {admin_id}: {e}")

    # ═══════════════════════════════════════════════════════════════
    # ВОРОНКА КАНАЛОВ: Инвайт-посты и автоудаление
    # ═══════════════════════════════════════════════════════════════

    async def _check_invite_post_needed(self):
        """
        Проверяет нужно ли опубликовать инвайт-пост в публичный канал.

        Условия:
        - Подходящее время (18:00-21:00 MSK, не воскресенье)
        - Есть публичные каналы с разрешением на инвайт-посты
        - Прошло минимум N дней с последнего инвайт-поста
        """
        try:
            async with AsyncSessionLocal() as session:
                router = ChannelRouter(session)

                # Проверяем нужно ли публиковать
                if not await router.should_publish_invite_post():
                    return

                # Получаем публичный канал для инвайт-поста
                channels = await router.get_channels_for_invite()
                if not channels:
                    return

                # Выбираем канал, который давно не получал инвайт
                public_channel = sorted(
                    channels,
                    key=lambda c: c.last_invite_post_at or datetime.min
                )[0]

                # Получаем VIP канал
                vip_channel = await router.get_vip_channel()
                if not vip_channel:
                    logger.warning("VIP канал не настроен — пропускаем инвайт-пост")
                    return

                logger.info(f"🎯 Публикуем инвайт-пост в канал: {public_channel.channel_title}")

                # Создаём инвайт-ссылку и публикуем пост
                await self._create_and_publish_invite_post(
                    session, public_channel, vip_channel
                )

        except Exception as e:
            logger.error(f"❌ Error checking invite post: {e}", exc_info=True)

    async def _create_and_publish_invite_post(
        self,
        session,
        public_channel: ChannelTier,
        vip_channel: ChannelTier
    ):
        """
        Создаёт инвайт-ссылку и публикует инвайт-пост.

        Args:
            session: Сессия БД
            public_channel: Публичный канал для публикации
            vip_channel: VIP канал для инвайт-ссылки
        """
        # Настройки
        hours_valid = getattr(settings, 'invite_post_hours_valid', 6)
        usage_limit = getattr(settings, 'invite_post_usage_limit', 100)

        # Создаём инвайт-ссылку через InviteManager
        # ПРИМЕЧАНИЕ: Для MVP можем создать заглушку ссылки, пока Telethon не подключён
        invite_manager = InviteManager(session, telethon_client=None)

        # Пробуем создать реальную ссылку
        invite_link = await invite_manager.create_temporary_invite(
            target_channel=vip_channel,
            hours_valid=hours_valid,
            usage_limit=usage_limit,
            title=f"VIP доступ {datetime.utcnow().strftime('%d.%m')}"
        )

        if not invite_link:
            # Fallback: используем статическую ссылку из настроек (для тестирования)
            static_invite = getattr(settings, 'vip_channel_invite_link', None)
            if static_invite:
                logger.warning("Telethon не подключён, используем статическую ссылку")
                invite_url = static_invite
                invite_link_id = None
            else:
                logger.error("Не удалось создать инвайт-ссылку и нет статической")
                return
        else:
            invite_url = invite_link.invite_link
            invite_link_id = invite_link.id

        # Генерируем текст инвайт-поста с учётом сегмента канала
        segment = public_channel.segment or "universal"
        prompt, system_prompt = FunnelPrompts.get_prompt_by_segment(
            segment=segment,
            invite_link=invite_url,
            hours=hours_valid
        )

        logger.info(f"Генерируем инвайт-пост для сегмента: {segment}")

        content, _ = await self.content_generator.generate_post(
            post_type="invite_teaser",
            custom_prompt=prompt,
            system_prompt=system_prompt
        )

        # Вычисляем время автоудаления
        expire_date = datetime.utcnow() + timedelta(hours=hours_valid)
        auto_delete_at = expire_date + timedelta(minutes=30)

        # Создаём пост в БД
        post = Post(
            content=content,
            post_type="invite_teaser",
            status="pending",  # Или сразу published если автопубликация
            generated_at=datetime.utcnow(),
            ai_model=settings.content_manager_ai_model,
            prompt_used=prompt,
            target_channel_id=public_channel.id,
            is_invite_post=True,
            invite_link_id=invite_link_id,
            auto_delete_at=auto_delete_at
        )
        session.add(post)
        await session.commit()
        await session.refresh(post)

        # Связываем инвайт-ссылку с постом
        if invite_link:
            invite_link.invite_post_id = post.id
            invite_link.published_channel_id = public_channel.id
            await session.commit()

        # Обновляем время последнего инвайт-поста для канала
        public_channel.last_invite_post_at = datetime.utcnow()
        await session.commit()

        logger.info(
            f"✅ Создан инвайт-пост #{post.id} для канала {public_channel.channel_title}. "
            f"Ссылка: {invite_url[:30]}..., TTL: {hours_valid}ч, автоудаление: {auto_delete_at}"
        )

        # Уведомляем админов
        await self._notify_admins(
            f"🎫 Создан инвайт-пост\n\n"
            f"Канал: {public_channel.channel_title}\n"
            f"Ссылка действует: {hours_valid} часов\n"
            f"Пост #{post.id} ожидает модерации (или настрой автопубликацию)"
        )

    async def _delete_expired_invite_posts(self):
        """
        Удаляет инвайт-посты, время которых истекло.

        Проверяет посты с is_invite_post=True и auto_delete_at <= NOW().
        """
        try:
            async with AsyncSessionLocal() as session:
                now = datetime.utcnow()

                # Находим посты для удаления
                result = await session.execute(
                    select(Post).where(
                        and_(
                            Post.is_invite_post == True,
                            Post.auto_delete_at.isnot(None),
                            Post.auto_delete_at <= now,
                            Post.status == "published",
                            Post.channel_message_id.isnot(None)
                        )
                    )
                )
                posts = list(result.scalars().all())

                if not posts:
                    return

                logger.info(f"🗑️ Найдено {len(posts)} инвайт-постов для удаления")

                for post in posts:
                    try:
                        # Получаем Telegram channel_id
                        channel_result = await session.execute(
                            select(ChannelTier).where(ChannelTier.id == post.target_channel_id)
                        )
                        channel = channel_result.scalar_one_or_none()

                        if channel:
                            # Удаляем сообщение из Telegram
                            await self.bot.delete_message(
                                chat_id=channel.channel_id,
                                message_id=post.channel_message_id
                            )
                            logger.info(f"🗑️ Удалён инвайт-пост #{post.id} из канала {channel.channel_title}")

                        # Обновляем статус поста
                        post.status = "deleted"
                        await session.commit()

                    except Exception as e:
                        logger.error(f"Ошибка удаления инвайт-поста #{post.id}: {e}")
                        # Помечаем как удалённый даже при ошибке (пост мог быть уже удалён)
                        post.status = "deleted"
                        await session.commit()

        except Exception as e:
            logger.error(f"❌ Error deleting expired invite posts: {e}", exc_info=True)

    async def _cleanup_expired_invites(self):
        """
        Очищает истёкшие инвайт-ссылки.

        Запускается каждые 30 минут (вместе с обновлением статистики).
        """
        # Используем ту же проверку времени что и для статистики
        if self._last_stats_update:
            time_since_update = datetime.utcnow() - self._last_stats_update
            if time_since_update.total_seconds() < 1800:
                return

        try:
            async with AsyncSessionLocal() as session:
                invite_manager = InviteManager(session, telethon_client=None)
                count = await invite_manager.cleanup_expired_invites()

                if count > 0:
                    logger.info(f"🧹 Очищено {count} истёкших инвайт-ссылок")

        except Exception as e:
            logger.error(f"❌ Error cleaning up expired invites: {e}")

    # ═══════════════════════════════════════════════════════════════
    # AI DIRECTOR: периодические задачи
    # ═══════════════════════════════════════════════════════════════

    async def _check_director_tasks(self):
        """
        Запускает периодические задачи AI Director:
        - Competitor analysis (раз в неделю, по понедельникам в 06:00 UTC)
        - Self-review (каждые 10 постов)
        """
        now = datetime.utcnow()

        # Проверяем не чаще раза в час
        if self._last_director_check:
            if (now - self._last_director_check).total_seconds() < 3600:
                return
        self._last_director_check = now

        thematic_channels = settings.thematic_channels
        if not thematic_channels:
            return

        for segment in thematic_channels:
            try:
                # Self-review: каждые 10 постов
                reviewer = get_self_reviewer()
                if await reviewer.should_run(segment):
                    logger.info(f"[DIRECTOR] Running self-review for {segment}")
                    review = await reviewer.run_review(segment)
                    if review:
                        await self._notify_admins(
                            f"🔍 <b>AI Self-Review ({segment})</b>\n\n"
                            f"Проанализировано 10 последних постов.\n"
                            f"Рекомендации: {', '.join(review.get('recommendations', [])[:3])}\n\n"
                            f"Подробнее: /review {segment}"
                        )

                # Competitor analysis: по понедельникам
                if now.weekday() == 0 and now.hour == 6:
                    logger.info(f"[DIRECTOR] Running competitor analysis for {segment}")
                    analyzer = get_competitor_analyzer()
                    insights = await analyzer.analyze(segment)
                    if insights:
                        topics = insights.get("trending_topics", [])
                        await self._notify_admins(
                            f"🔍 <b>Конкуренты ({segment})</b>\n\n"
                            f"Trending: {', '.join(topics[:5])}\n"
                            f"Подробнее: /competitors {segment}"
                        )

            except Exception as e:
                logger.error(f"[DIRECTOR] Director task error for {segment}: {e}")

    # ═══════════════════════════════════════════════════════════════
    # ЕЖЕДНЕВНЫЙ ОТЧЁТ TRAFFIC ENGINE (23:00 MSK = 20:00 UTC)
    # ═══════════════════════════════════════════════════════════════

    async def _check_daily_traffic_report(self):
        """Проверяет, пора ли отправить ежедневный отчёт TE."""
        now = datetime.utcnow()

        # Сбрасываем флаг в полночь UTC
        if now.hour == 0 and self._daily_report_sent_today:
            self._daily_report_sent_today = False

        # 20:00 UTC = 23:00 MSK
        if now.hour == 20 and not self._daily_report_sent_today:
            self._daily_report_sent_today = True
            await self._send_daily_traffic_report()

    async def _send_daily_traffic_report(self):
        """Отправляет ежедневный отчёт Traffic Engine админам."""
        try:
            from traffic_engine.database.models import UserBotAccount, TrafficAction
            from traffic_engine.database import get_session as te_get_session

            today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

            async with te_get_session() as session:
                # Аккаунты
                accounts_result = await session.execute(
                    select(UserBotAccount).order_by(UserBotAccount.id)
                )
                accounts = accounts_result.scalars().all()

                # Действия за сегодня (по типу и статусу)
                actions_result = await session.execute(
                    select(
                        TrafficAction.action_type,
                        TrafficAction.status,
                        func.count(TrafficAction.id),
                    ).where(
                        TrafficAction.created_at >= today,
                    ).group_by(
                        TrafficAction.action_type,
                        TrafficAction.status,
                    )
                )
                stats = {}
                for atype, status, cnt in actions_result.all():
                    stats[f"{atype}_{status}"] = cnt

                # Стратегии за сегодня
                strategy_result = await session.execute(
                    select(
                        TrafficAction.strategy_used,
                        func.count(TrafficAction.id),
                    ).where(
                        TrafficAction.created_at >= today,
                        TrafficAction.action_type == "comment",
                        TrafficAction.status == "success",
                        TrafficAction.strategy_used.isnot(None),
                    ).group_by(TrafficAction.strategy_used)
                )
                strategies = {row[0]: row[1] for row in strategy_result.all()}

                # Replies
                replies_result = await session.execute(
                    select(func.count(TrafficAction.id)).where(
                        TrafficAction.got_reply == True,
                        TrafficAction.created_at >= today,
                    )
                )
                replies = replies_result.scalar() or 0

            # Формируем отчёт
            comments_ok = stats.get("comment_success", 0)
            comments_fail = stats.get("comment_failed", 0)
            stories = stats.get("story_view_success", 0)
            invites = stats.get("invite_success", 0)

            report = "📊 <b>Traffic Engine — Итоги дня</b>\n"
            report += f"<i>{datetime.utcnow().strftime('%d.%m.%Y')}</i>\n\n"

            # Аккаунты
            active_count = sum(1 for a in accounts if a.status in ("active", "warming"))
            report += f"<b>👤 Аккаунты:</b> {active_count} активных из {len(accounts)}\n"
            for acc in accounts:
                seg = acc.segment or "—"
                report += f"  {acc.phone} [{seg}]: 💬{acc.daily_comments} 👁{acc.daily_story_views}\n"

            report += f"\n<b>📈 Действия:</b>\n"
            report += f"  💬 Комменты: {comments_ok} ✅ / {comments_fail} ❌\n"
            report += f"  👁 Сторис: {stories}\n"
            report += f"  📨 Инвайты: {invites}\n"
            report += f"  💬→ Ответы: {replies}\n"

            if strategies:
                report += f"\n<b>🎯 Стратегии:</b>\n"
                for strat, cnt in sorted(strategies.items(), key=lambda x: -x[1]):
                    report += f"  {strat}: {cnt}\n"

            await self._notify_admins(report)
            logger.info("Daily traffic report sent")

        except ImportError:
            logger.debug("Traffic Engine models not available for daily report")
        except Exception as e:
            logger.error(f"Error sending daily traffic report: {e}")
