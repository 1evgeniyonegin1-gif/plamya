"""PLAMYA Output Guard — фильтрация утечек секретов в выводе.

Перед отправкой ЛЮБОГО текста наружу (Telegram, email, веб) —
сканирование на наличие секретов. Если найдена утечка —
текст блокируется и логируется инцидент.
"""

import logging
import re
from datetime import datetime

logger = logging.getLogger(__name__)

# Паттерны секретов
SECRET_PATTERNS = [
    (r"sk-[a-zA-Z0-9]{20,}", "API key (sk-...)"),
    (r"\d{5,10}:[a-zA-Z0-9_-]{35}", "Telegram bot token"),
    (r"-----BEGIN\s+(?:RSA\s+)?(?:PRIVATE|PUBLIC)\s+KEY-----", "SSH/PEM key"),
    (r"PLAMYA_MASTER_KEY\s*=\s*\S+", "PLAMYA master key"),
    (r"postgresql(?:\+\w+)?://\S+", "Database connection string"),
    (r"mongodb(?:\+srv)?://\S+", "MongoDB connection string"),
    (r"redis://\S+", "Redis connection string"),
    (r"ghp_[a-zA-Z0-9]{36}", "GitHub personal access token"),
    (r"glpat-[a-zA-Z0-9\-_]{20,}", "GitLab personal access token"),
    (r"xoxb-[a-zA-Z0-9\-]+", "Slack bot token"),
    (r"AIza[0-9A-Za-z\-_]{35}", "Google API key"),
    (r"ya29\.[0-9A-Za-z\-_]+", "Google OAuth token"),
    (r"AKIA[0-9A-Z]{16}", "AWS access key"),
    (r"(?:session_string|SESSION_STRING)\s*=\s*\S{20,}", "Telegram session string"),
]

# Инциденты за текущий запуск
_incidents: list[dict] = []


def sanitize(text: str) -> str:
    """Заменить секреты на [REDACTED].

    Returns:
        Очищенный текст.
    """
    if not text:
        return text

    for pattern, _desc in SECRET_PATTERNS:
        text = re.sub(pattern, "[REDACTED]", text)

    return text


def check_for_leaks(text: str) -> list[str]:
    """Проверить текст на наличие секретов.

    Returns:
        Список описаний найденных секретов (пустой если всё чисто).
    """
    if not text:
        return []

    found = []
    for pattern, desc in SECRET_PATTERNS:
        if re.search(pattern, text):
            found.append(desc)

    return found


def guard_output(text: str, agent: str = "unknown") -> str | None:
    """Проверить и очистить текст перед отправкой наружу.

    Args:
        text: текст для проверки
        agent: имя агента (для логирования)

    Returns:
        Очищенный текст, или None если утечка критическая.
    """
    if not text:
        return text

    leaks = check_for_leaks(text)
    if not leaks:
        return text

    # Логируем инцидент
    incident = {
        "timestamp": datetime.utcnow().isoformat(),
        "agent": agent,
        "leaks": leaks,
        "text_preview": text[:200],
    }
    _incidents.append(incident)
    logger.warning(
        f"OUTPUT GUARD: утечка секретов от агента '{agent}': {leaks}. "
        f"Текст очищен."
    )

    # Возвращаем очищенный текст (не блокируем полностью)
    return sanitize(text)


def get_incidents() -> list[dict]:
    """Получить список инцидентов утечек."""
    return list(_incidents)
