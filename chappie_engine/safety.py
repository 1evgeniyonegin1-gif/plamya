"""Защита от бана — лимиты, прогрев, аварийные стопы.

Личный аккаунт Данила НЕЗАМЕНИМ. Бан = катастрофа.
Все лимиты жёсткие и не могут быть обойдены.
"""

import logging
from datetime import datetime, timezone, timedelta

from chappie_engine.config import (
    LIMITS,
    WARMUP_SCHEDULE,
    WORK_HOURS_START,
    WORK_HOURS_END,
    UTC_OFFSET,
    EMERGENCY_FLOOD_WAIT_THRESHOLD,
    EMERGENCY_FLOOD_WAIT_CRITICAL,
    EMERGENCY_CONSECUTIVE_ERRORS,
)

logger = logging.getLogger("chappie.safety")

MSK = timezone(timedelta(hours=UTC_OFFSET))


class SafetyGuard:
    """Контролирует все действия Чаппи.

    Проверяет лимиты, прогрев, рабочие часы, аварийные стопы.
    Все проверки — перед КАЖДЫМ действием.
    """

    def __init__(self, state_manager):
        self.state = state_manager

    def get_warmup_day(self) -> int:
        """Сколько дней прошло с начала работы."""
        state = self.state.load_state()
        started = state.get("started_at")
        if not started:
            return 1
        start_date = datetime.strptime(started, "%Y-%m-%d").date()
        today = datetime.now(MSK).date()
        return max(1, (today - start_date).days + 1)

    def get_warmup_limits(self) -> dict:
        """Текущие лимиты на основе дня прогрева."""
        day = self.get_warmup_day()

        for (day_from, day_to), limits in WARMUP_SCHEDULE.items():
            if day_from <= day <= day_to:
                return limits

        # После 30 дней — полные лимиты
        return {
            "posts": LIMITS["max_posts_total_per_day"],
            "stories": LIMITS["max_stories_per_day"],
            "dms": LIMITS["max_dms_new_per_day"],
            "channels": 5,
        }

    def is_working_hours(self) -> bool:
        """Сейчас рабочие часы? (09:00-22:00 MSK)"""
        now = datetime.now(MSK)
        return WORK_HOURS_START <= now.hour < WORK_HOURS_END

    def is_banned(self) -> tuple[bool, str]:
        """Проверить аварийный стоп."""
        state = self.state.load_state()
        banned_until = state.get("banned_until")

        if not banned_until:
            return False, ""

        ban_time = datetime.fromisoformat(banned_until)
        now = datetime.now(MSK)

        if now < ban_time:
            remaining = ban_time - now
            return True, f"Стоп до {ban_time.strftime('%H:%M')} ({remaining.seconds // 60} мин осталось)"

        # Бан истёк — снимаем
        state["banned_until"] = None
        self.state.save_state(state)
        return False, ""

    def can_perform(self, action_type: str) -> tuple[bool, str]:
        """Проверить можно ли выполнить действие.

        Returns:
            (can_do, reason) — True если можно, иначе причина отказа.
        """
        # 1. Аварийный стоп
        banned, reason = self.is_banned()
        if banned:
            return False, f"Аварийный стоп: {reason}"

        # 2. Рабочие часы
        if not self.is_working_hours():
            return False, "Ночь (22:00-09:00 MSK). Сплю."

        # 3. Лимиты прогрева
        warmup = self.get_warmup_limits()
        state = self.state.load_state()
        today = datetime.now(MSK).strftime("%Y-%m-%d")
        daily = state.get("daily_actions", {}).get(today, {})

        action_map = {
            "post": ("posts", warmup.get("posts", 0)),
            "story": ("stories", warmup.get("stories", 0)),
            "dm_new": ("dms", warmup.get("dms", 0)),
            "dm_reply": ("dm_replies", LIMITS["max_dms_reply_per_day"]),
            "channel_join": ("channel_joins", LIMITS["max_channel_joins_per_day"]),
            "story_view": ("story_views", LIMITS["max_story_views_per_day"]),
            "read": ("reads", 999),  # Чтение не лимитируется
            "interact": ("interacts", 999),  # Взаимодействие с ботами не лимитируется
        }

        if action_type not in action_map:
            return False, f"Неизвестный тип действия: {action_type}"

        key, limit = action_map[action_type]
        current = daily.get(key, 0)

        if current >= limit:
            day = self.get_warmup_day()
            if limit == 0:
                return False, f"Действие '{action_type}' запрещено на дне прогрева {day}"
            return False, f"Лимит исчерпан: {key} = {current}/{limit} (день прогрева {day})"

        # 4. Общий лимит API вызовов
        total_api = sum(daily.get(k, 0) for k in ["posts", "stories", "dms", "dm_replies", "channel_joins", "story_views"])
        if total_api >= LIMITS["max_api_calls_per_day"]:
            return False, f"Общий лимит API вызовов исчерпан: {total_api}/{LIMITS['max_api_calls_per_day']}"

        # 5. Минимальный интервал
        interval_key = f"min_interval_{action_type}"
        if interval_key in LIMITS:
            last_action_key = f"last_{action_type}_at"
            last_at = state.get(last_action_key)
            if last_at:
                last_time = datetime.fromisoformat(last_at)
                elapsed = (datetime.now(MSK) - last_time).total_seconds()
                required = LIMITS[interval_key]
                if elapsed < required:
                    remaining = int(required - elapsed)
                    return False, f"Слишком рано. Подожди ещё {remaining // 60} мин ({action_type})"

        return True, "OK"

    def record_action(self, action_type: str, success: bool = True):
        """Записать выполненное действие."""
        state = self.state.load_state()
        today = datetime.now(MSK).strftime("%Y-%m-%d")

        if "daily_actions" not in state:
            state["daily_actions"] = {}
        if today not in state["daily_actions"]:
            state["daily_actions"][today] = {}

        action_map = {
            "post": "posts",
            "story": "stories",
            "dm_new": "dms",
            "dm_reply": "dm_replies",
            "channel_join": "channel_joins",
            "story_view": "story_views",
            "read": "reads",
            "interact": "interacts",
        }

        key = action_map.get(action_type, action_type)
        state["daily_actions"][today][key] = state["daily_actions"][today].get(key, 0) + 1

        # Обновить время последнего действия
        state[f"last_{action_type}_at"] = datetime.now(MSK).isoformat()

        # Обновить total
        if "total_actions" not in state:
            state["total_actions"] = {}
        total_key = key if key != "dms" else "dms_sent"
        state["total_actions"][total_key] = state["total_actions"].get(total_key, 0) + 1

        # Сбросить/инкрементировать ошибки
        if success:
            state["errors_today"] = 0
        else:
            state["errors_today"] = state.get("errors_today", 0) + 1
            if state["errors_today"] >= EMERGENCY_CONSECUTIVE_ERRORS:
                self._emergency_stop(state, hours=1, reason=f"{EMERGENCY_CONSECUTIVE_ERRORS} ошибок подряд")

        self.state.save_state(state)

    def handle_flood_wait(self, seconds: int):
        """Обработать FloodWaitError от Telegram."""
        state = self.state.load_state()

        if seconds >= EMERGENCY_FLOOD_WAIT_CRITICAL:
            self._emergency_stop(state, hours=24, reason=f"FloodWait {seconds}s (критический)")
        elif seconds >= EMERGENCY_FLOOD_WAIT_THRESHOLD:
            self._emergency_stop(state, hours=6, reason=f"FloodWait {seconds}s")
        else:
            logger.warning(f"FloodWait {seconds}s — подожду")

    def handle_ban_error(self, error_msg: str):
        """Обработать ошибку бана — ПОЛНЫЙ СТОП."""
        state = self.state.load_state()
        self._emergency_stop(state, hours=999, reason=f"БАН: {error_msg}")

        # Уведомить Данила через INBOX
        from chappie_engine.state.state_manager import StateManager
        sm = StateManager()
        sm.write_to_inbox(
            "ЧАППИ → АЛЬТРОН",
            f"КРИТИЧЕСКАЯ ОШИБКА: Возможный бан аккаунта!\n"
            f"Ошибка: {error_msg}\n"
            f"Все действия ОСТАНОВЛЕНЫ. Нужна проверка Данила!"
        )

    def _emergency_stop(self, state: dict, hours: int, reason: str):
        """Аварийный стоп на N часов."""
        ban_until = datetime.now(MSK) + timedelta(hours=hours)
        state["banned_until"] = ban_until.isoformat()
        self.state.save_state(state)
        logger.critical(f"АВАРИЙНЫЙ СТОП до {ban_until.strftime('%Y-%m-%d %H:%M')} MSK: {reason}")

    def get_status_report(self) -> str:
        """Текстовый отчёт о текущем состоянии безопасности."""
        state = self.state.load_state()
        today = datetime.now(MSK).strftime("%Y-%m-%d")
        daily = state.get("daily_actions", {}).get(today, {})
        warmup = self.get_warmup_limits()
        day = self.get_warmup_day()

        banned, ban_reason = self.is_banned()
        working = self.is_working_hours()

        lines = [
            f"День прогрева: {day}/30",
            f"Рабочие часы: {'Да' if working else 'Нет (сплю)'}",
            f"Аварийный стоп: {ban_reason if banned else 'Нет'}",
            f"",
            f"Лимиты сегодня (использовано/макс):",
            f"  Посты: {daily.get('posts', 0)}/{warmup.get('posts', 0)}",
            f"  Истории: {daily.get('stories', 0)}/{warmup.get('stories', 0)}",
            f"  DM новые: {daily.get('dms', 0)}/{warmup.get('dms', 0)}",
            f"  DM ответы: {daily.get('dm_replies', 0)}/{LIMITS['max_dms_reply_per_day']}",
            f"  Просмотры историй: {daily.get('story_views', 0)}/{LIMITS['max_story_views_per_day']}",
            f"  Ошибок подряд: {state.get('errors_today', 0)}/{EMERGENCY_CONSECUTIVE_ERRORS}",
        ]

        return "\n".join(lines)
