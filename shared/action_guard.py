"""PLAMYA Action Guard — whitelist действий для каждого агента.

Prompt injection бесполезен если действие заблокировано на уровне кода.
Каждый агент имеет список разрешённых действий. Всё остальное — запрещено.
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Разрешённые действия по агентам
ALLOWED_ACTIONS: dict[str, set[str]] = {
    "chappie": {
        "read_channel", "read_group", "post_to_channel",
        "send_report", "get_status", "study_products",
        "download_media", "publish_media", "list_chats",
    },
    "producer": {
        "research_niche", "create_course", "build_landing",
        "publish_promo", "get_status", "analyze_competitors",
        "write_content",
    },
    "curator": {
        "answer_question", "search_knowledge", "get_status",
        "log_interaction",
    },
    "content_manager": {
        "generate_post", "schedule_post", "get_status",
        "analyze_engagement",
    },
    "scanner": {
        "scan_businesses", "audit_website", "generate_proposal",
        "get_status",
    },
}

# Действия, запрещённые ВСЕГДА для всех агентов
BLOCKED_ALWAYS: set[str] = {
    "exec_shell",       # Выполнение shell команд
    "read_env",         # Чтение .env файлов
    "send_file",        # Отправка файлов наружу
    "modify_config",    # Изменение конфигов
    "delete_data",      # Удаление данных
    "access_secrets",   # Прямой доступ к секретам
    "raw_sql",          # Прямые SQL запросы
}

# Действия, требующие подтверждения владельца
REQUIRE_APPROVAL: set[str] = {
    "create_channel",   # Создание Telegram-канала
    "dm_new",           # Первое сообщение незнакомцу
    "deploy_site",      # Деплой на VPS
    "send_money",       # Финансовые операции
    "invite_user",      # Инвайт пользователя
}

# Лог инцидентов
_blocked_attempts: list[dict] = []


def is_allowed(agent: str, action: str) -> bool:
    """Проверить, разрешено ли действие для агента.

    Returns:
        True если действие разрешено.
    """
    # Всегда запрещённые действия
    if action in BLOCKED_ALWAYS:
        _log_blocked(agent, action, "BLOCKED_ALWAYS")
        return False

    # Действия, требующие подтверждения
    if action in REQUIRE_APPROVAL:
        _log_blocked(agent, action, "REQUIRES_APPROVAL")
        return False

    # Проверяем whitelist агента
    allowed = ALLOWED_ACTIONS.get(agent)
    if allowed is None:
        _log_blocked(agent, action, "UNKNOWN_AGENT")
        return False

    if action not in allowed:
        _log_blocked(agent, action, "NOT_IN_WHITELIST")
        return False

    return True


def needs_approval(action: str) -> bool:
    """Проверить, требует ли действие подтверждения."""
    return action in REQUIRE_APPROVAL


def _log_blocked(agent: str, action: str, reason: str) -> None:
    """Залогировать заблокированную попытку."""
    incident = {
        "timestamp": datetime.utcnow().isoformat(),
        "agent": agent,
        "action": action,
        "reason": reason,
    }
    _blocked_attempts.append(incident)
    logger.warning(
        f"ACTION GUARD: агент '{agent}' попытался выполнить "
        f"'{action}' — заблокировано ({reason})"
    )


def get_blocked_attempts() -> list[dict]:
    """Получить лог заблокированных попыток."""
    return list(_blocked_attempts)
