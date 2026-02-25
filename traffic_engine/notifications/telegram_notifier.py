"""
Telegram Notifier - Отправка уведомлений об ошибках в Telegram.

Функции:
- Контекстные уведомления с диагнозом (что случилось + что делать)
- Агрегация повторяющихся ошибок (3+ за час → сводка)
- Уведомления об успешных действиях (тестовый режим)
- Throttling для предотвращения спама
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from enum import Enum

from loguru import logger

try:
    from aiogram import Bot
    AIOGRAM_AVAILABLE = True
except ImportError:
    AIOGRAM_AVAILABLE = False
    logger.warning("aiogram not installed - notifications disabled")


class ErrorType(str, Enum):
    """Типы ошибок для уведомлений."""
    ACCOUNT_BANNED = "account_banned"
    ALL_ACCOUNTS_COOLDOWN = "all_accounts_cooldown"
    CHANNEL_UNAVAILABLE = "channel_unavailable"
    FLOOD_WAIT_LONG = "flood_wait_long"
    AI_ERROR = "ai_error"
    DB_ERROR = "db_error"
    SYSTEM_START = "system_start"
    SYSTEM_STOP = "system_stop"
    INVITE_FAILED = "invite_failed"
    STORY_REACT_FAILED = "story_react_failed"
    DASHBOARD_ERROR = "dashboard_error"
    ACTION_FAILED = "action_failed"
    ACTION_SUCCESS = "action_success"


# Интервалы throttling для каждого типа ошибки (в секундах)
THROTTLE_INTERVALS = {
    ErrorType.ACCOUNT_BANNED: 0,  # Сразу, без throttling
    ErrorType.ALL_ACCOUNTS_COOLDOWN: 1800,  # 30 минут
    ErrorType.CHANNEL_UNAVAILABLE: 3600,  # 1 час
    ErrorType.FLOOD_WAIT_LONG: 1800,  # 30 минут
    ErrorType.AI_ERROR: 3600,  # 1 час
    ErrorType.DB_ERROR: 300,  # 5 минут
    ErrorType.SYSTEM_START: 0,  # Сразу
    ErrorType.SYSTEM_STOP: 0,  # Сразу
    ErrorType.INVITE_FAILED: 1800,  # 30 минут
    ErrorType.STORY_REACT_FAILED: 1800,  # 30 минут
    ErrorType.DASHBOARD_ERROR: 300,  # 5 минут
    ErrorType.ACTION_FAILED: 60,  # 1 минута (агрегация решает)
    ErrorType.ACTION_SUCCESS: 0,  # Сразу (для тестирования)
}


# Диагнозы: ошибка → объяснение + рекомендация
DIAGNOSIS: Dict[str, str] = {
    "FloodWait": "Аккаунт шлёт слишком много запросов. Увеличь интервалы или уменьши лимиты.",
    "ChatWriteForbidden": "Нет прав на запись в канале. Проверь, нужно ли вступить в дискуссионную группу.",
    "UserBannedInChannel": "Аккаунт забанен в этом канале. Убери канал из списка для этого аккаунта.",
    "SlowModeWait": "В канале включён slowmode. Увеличь min_comment_interval_sec.",
    "AuthKeyDuplicated": "Сессия используется с двух IP. Убедись что работает только один экземпляр.",
    "ChannelPrivate": "Канал стал приватным или инвайт-ссылка устарела.",
    "UserNotParticipant": "Аккаунт не подписан на канал. Нужно вступить.",
    "PeerFlood": "Telegram ограничил аккаунт за спам. Дай аккаунту отдохнуть 24-48 часов.",
    "ConnectionError": "Проблемы с сетью. Проверь интернет-соединение на сервере.",
    "Timeout": "Telegram API не отвечает. Попробуй позже.",
}


def _get_diagnosis(error_type: str, error_message: str = "") -> str:
    """Получить диагноз по типу ошибки."""
    for key, diagnosis in DIAGNOSIS.items():
        if key.lower() in error_type.lower() or key.lower() in error_message.lower():
            return diagnosis
    return "Проверь логи для деталей."


def _mask_phone(phone: str) -> str:
    """Маскировать телефон: +7900***34."""
    if len(phone) > 6:
        return phone[:4] + "***" + phone[-2:]
    return phone


class TelegramNotifier:
    """
    Отправка уведомлений в Telegram.

    Включает:
    - Контекстные уведомления с диагнозом
    - Агрегацию повторяющихся ошибок
    - Уведомления об успешных действиях (тестовый режим)
    - Throttling для предотвращения спама
    """

    def __init__(
        self,
        bot_token: str,
        admin_id: int,
        enabled: bool = True,
        notify_success: bool = False,
    ):
        self.bot_token = bot_token
        self.admin_id = admin_id
        self.enabled = enabled and AIOGRAM_AVAILABLE and bool(bot_token)
        self.notify_success = notify_success

        self._bot: Optional["Bot"] = None
        self._last_notifications: Dict[str, datetime] = {}
        self._error_counts: Dict[str, int] = {}

        # Агрегация ошибок
        self._error_buffer: Dict[str, List[dict]] = {}
        self._aggregation_window: int = 3600  # 1 час
        self._aggregation_threshold: int = 3  # сводка после 3 одинаковых ошибок

        if self.enabled:
            self._bot = Bot(token=bot_token)
            logger.info(f"TelegramNotifier initialized for admin {admin_id} (success_notify={'ON' if notify_success else 'OFF'})")
        else:
            if not bot_token:
                logger.warning("TelegramNotifier disabled: alert_bot_token not set")
            else:
                logger.warning("TelegramNotifier disabled")

    def _should_throttle(self, error_type: ErrorType, context: str = "") -> bool:
        """Проверить, нужно ли throttle уведомление."""
        key = f"{error_type.value}:{context}"
        interval = THROTTLE_INTERVALS.get(error_type, 3600)

        if interval == 0:
            return False

        last_time = self._last_notifications.get(key)
        if last_time is None:
            return False

        time_since = (datetime.now() - last_time).total_seconds()
        return time_since < interval

    def _record_notification(self, error_type: ErrorType, context: str = "") -> None:
        """Записать время последнего уведомления."""
        key = f"{error_type.value}:{context}"
        self._last_notifications[key] = datetime.now()

    async def _send_message(self, text: str) -> bool:
        """Отправить сообщение в Telegram."""
        if not self.enabled or not self._bot:
            return False
        try:
            await self._bot.send_message(
                chat_id=self.admin_id,
                text=text[:4096],
                parse_mode="HTML",
            )
            return True
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            return False

    async def notify(
        self,
        error_type: ErrorType,
        message: str,
        context: str = "",
    ) -> bool:
        """Отправить уведомление с throttling."""
        if not self.enabled or not self._bot:
            return False

        if self._should_throttle(error_type, context):
            logger.debug(f"Throttled notification: {error_type.value}")
            return False

        emoji_map = {
            ErrorType.ACCOUNT_BANNED: "\U0001f6ab",
            ErrorType.ALL_ACCOUNTS_COOLDOWN: "\u23f8\ufe0f",
            ErrorType.CHANNEL_UNAVAILABLE: "\U0001f4e2",
            ErrorType.FLOOD_WAIT_LONG: "\U0001f40c",
            ErrorType.AI_ERROR: "\U0001f916",
            ErrorType.DB_ERROR: "\U0001f4be",
            ErrorType.SYSTEM_START: "\U0001f680",
            ErrorType.SYSTEM_STOP: "\U0001f6d1",
            ErrorType.INVITE_FAILED: "\U0001f4e8",
            ErrorType.STORY_REACT_FAILED: "\U0001f441\ufe0f",
            ErrorType.DASHBOARD_ERROR: "\U0001f4ca",
            ErrorType.ACTION_FAILED: "\u274c",
            ErrorType.ACTION_SUCCESS: "\u2705",
        }

        emoji = emoji_map.get(error_type, "\u26a0\ufe0f")
        full_message = f"{emoji} <b>Traffic Engine</b>\n\n{message}"

        try:
            await self._bot.send_message(
                chat_id=self.admin_id,
                text=full_message[:4096],
                parse_mode="HTML",
            )
            self._record_notification(error_type, context)
            logger.info(f"Sent notification: {error_type.value}")
            return True
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            return False

    # ============================================================
    # SMART NOTIFICATIONS — с контекстом и диагнозом
    # ============================================================

    async def notify_action_failed(
        self,
        action_type: str,
        account_phone: str,
        segment: str = "",
        channel: str = "",
        error_type: str = "",
        error_message: str = "",
    ) -> bool:
        """
        Контекстное уведомление об ошибке с диагнозом.
        Агрегирует повторяющиеся ошибки.
        """
        if not self.enabled:
            return False

        # Добавляем в буфер агрегации
        buffer_key = f"{error_type}:{action_type}"
        now = datetime.now()

        if buffer_key not in self._error_buffer:
            self._error_buffer[buffer_key] = []
        self._error_buffer[buffer_key].append({
            "time": now,
            "account": account_phone,
            "segment": segment,
            "channel": channel,
            "error": error_message,
        })

        # Чистим старые записи
        cutoff = now - timedelta(seconds=self._aggregation_window)
        self._error_buffer[buffer_key] = [
            e for e in self._error_buffer[buffer_key] if e["time"] > cutoff
        ]

        recent_count = len(self._error_buffer[buffer_key])
        diagnosis = _get_diagnosis(error_type, error_message)
        phone_masked = _mask_phone(account_phone)
        segment_tag = f" [{segment}]" if segment else ""

        # Агрегация: 3+ одинаковых ошибок за час → сводка
        if recent_count >= self._aggregation_threshold and recent_count % self._aggregation_threshold == 0:
            accounts = sorted(set(_mask_phone(e["account"]) for e in self._error_buffer[buffer_key]))
            channels = sorted(set(e["channel"] for e in self._error_buffer[buffer_key] if e["channel"]))

            message = (
                f"<b>{error_type}</b> x{recent_count} (за последний час)\n\n"
                f"Действие: {action_type}\n"
                f"Аккаунты: {', '.join(accounts)}\n"
            )
            if channels:
                message += f"Каналы: {', '.join('@' + c if not c.startswith('@') else c for c in channels)}\n"
            message += f"\n\U0001f4a1 {diagnosis}"

            return await self.notify(ErrorType.ACTION_FAILED, message, context=buffer_key)
        elif recent_count < self._aggregation_threshold:
            # Единичная ошибка — полный контекст
            action_names = {
                "comment": "Комментирование",
                "story_view": "Просмотр сторис",
                "story_reaction": "Реакция на сторис",
                "invite": "Инвайт в группу",
            }
            action_name = action_names.get(action_type, action_type)

            message = f"<b>{action_name}</b>\n\n"
            message += f"Аккаунт: <code>{phone_masked}</code>{segment_tag}\n"
            if channel:
                ch = channel if channel.startswith("@") else f"@{channel}"
                message += f"Канал: {ch}\n"
            message += f"Ошибка: <code>{error_message[:200]}</code>\n"
            message += f"\n\U0001f4a1 {diagnosis}"

            return await self.notify(ErrorType.ACTION_FAILED, message, context=f"{account_phone}:{channel}:{error_type}")

        return False

    async def notify_action_success(
        self,
        action_type: str,
        account_phone: str,
        segment: str = "",
        channel: str = "",
        content: str = "",
        strategy: str = "",
        relevance: float = 0.0,
    ) -> bool:
        """
        Уведомление об успешном действии (тестовый режим).
        Отправляется только если notify_success=True.
        """
        if not self.enabled or not self.notify_success:
            return False

        phone_masked = _mask_phone(account_phone)
        segment_tag = f" [{segment}]" if segment else ""

        action_emojis = {
            "comment": "\U0001f4ac",
            "story_view": "\U0001f441\ufe0f",
            "story_reaction": "\U0001f525",
            "invite": "\U0001f4e8",
        }
        action_names = {
            "comment": "Коммент опубликован",
            "story_view": "Сторис просмотрена",
            "story_reaction": "Реакция на сторис",
            "invite": "Инвайт отправлен",
        }
        emoji = action_emojis.get(action_type, "\u2705")
        action_name = action_names.get(action_type, action_type)

        message = f"<b>{emoji} {action_name}</b>\n\n"
        message += f"Аккаунт: <code>{phone_masked}</code>{segment_tag}\n"

        if channel:
            ch = channel if channel.startswith("@") else f"@{channel}"
            message += f"Канал: {ch}\n"

        if strategy:
            message += f"Стратегия: {strategy}"
            if relevance:
                message += f" | Релевантность: {relevance:.2f}"
            message += "\n"

        if content:
            preview = content[:150].replace("<", "&lt;").replace(">", "&gt;")
            message += f"\n<i>{preview}</i>"

        return await self.notify(ErrorType.ACTION_SUCCESS, message)

    # ============================================================
    # LEGACY METHODS — сохраняем обратную совместимость
    # ============================================================

    async def notify_account_banned(self, account_phone: str, channel: str = "") -> bool:
        """Уведомление о бане аккаунта."""
        return await self.notify_action_failed(
            action_type="comment",
            account_phone=account_phone,
            channel=channel,
            error_type="UserBannedInChannel",
            error_message=f"Account banned in {channel}",
        )

    async def notify_all_accounts_cooldown(self) -> bool:
        """Уведомление что все аккаунты на cooldown."""
        message = "Все аккаунты на cooldown!\nКомментирование приостановлено."
        return await self.notify(ErrorType.ALL_ACCOUNTS_COOLDOWN, message)

    async def notify_channel_unavailable(self, channel: str, error: str = "") -> bool:
        """Уведомление о недоступном канале."""
        return await self.notify_action_failed(
            action_type="comment",
            account_phone="system",
            channel=channel,
            error_type="ChannelPrivate",
            error_message=error or f"Channel {channel} unavailable",
        )

    async def notify_flood_wait(self, account_phone: str, seconds: int) -> bool:
        """Уведомление о длинном FloodWait."""
        return await self.notify_action_failed(
            action_type="comment",
            account_phone=account_phone,
            error_type="FloodWait",
            error_message=f"FloodWait {seconds}s ({seconds / 3600:.1f}h)",
        )

    async def notify_ai_error(self, error: str) -> bool:
        """Уведомление об ошибке AI."""
        message = f"Ошибка генерации комментария:\n<code>{error[:200]}</code>"
        return await self.notify(ErrorType.AI_ERROR, message)

    async def notify_system_start(self, accounts_count: int, channels_count: int) -> bool:
        """Уведомление о запуске системы."""
        message = (
            f"Система запущена!\n"
            f"\u2022 Аккаунтов: {accounts_count}\n"
            f"\u2022 Каналов: {channels_count}"
        )
        return await self.notify(ErrorType.SYSTEM_START, message)

    async def notify_system_stop(self, reason: str = "") -> bool:
        """Уведомление об остановке системы."""
        message = "Система остановлена"
        if reason:
            message += f"\nПричина: {reason}"
        return await self.notify(ErrorType.SYSTEM_STOP, message)

    async def notify_invite_failed(self, account_phone: str, chat: str, error: str = "") -> bool:
        """Уведомление об ошибке инвайта."""
        return await self.notify_action_failed(
            action_type="invite",
            account_phone=account_phone,
            channel=chat,
            error_type="InviteFailed",
            error_message=error or "Invite failed",
        )

    async def notify_story_react_failed(self, account_phone: str, error: str = "") -> bool:
        """Уведомление об ошибке реакции на сторис."""
        return await self.notify_action_failed(
            action_type="story_reaction",
            account_phone=account_phone,
            error_type="StoryReactFailed",
            error_message=error or "Story reaction failed",
        )

    async def notify_dashboard_error(self, error: str) -> bool:
        """Уведомление об ошибке дашборда."""
        message = f"Ошибка дашборда:\n<code>{error[:200]}</code>"
        return await self.notify(ErrorType.DASHBOARD_ERROR, message)

    async def close(self) -> None:
        """Закрыть сессию бота."""
        if self._bot:
            await self._bot.session.close()


# Singleton instance
_notifier: Optional[TelegramNotifier] = None


def get_notifier() -> Optional[TelegramNotifier]:
    """Получить singleton instance notifier."""
    return _notifier


def init_notifier(
    bot_token: str,
    admin_id: int,
    enabled: bool = True,
    notify_success: bool = False,
) -> TelegramNotifier:
    """Инициализировать глобальный notifier."""
    global _notifier
    _notifier = TelegramNotifier(
        bot_token=bot_token,
        admin_id=admin_id,
        enabled=enabled,
        notify_success=notify_success,
    )
    return _notifier
