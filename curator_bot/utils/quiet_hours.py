"""
Тихие часы — не отправлять проактивные сообщения ночью.

Окно отправки: 10:00–21:00 МСК.
"""
from datetime import datetime, timezone, timedelta

MSK = timezone(timedelta(hours=3))

SEND_HOUR_START = 10  # включительно
SEND_HOUR_END = 21    # не включительно


def is_sending_allowed() -> bool:
    """Можно ли сейчас отправлять проактивные сообщения (10:00–21:00 МСК)."""
    current_hour = datetime.now(MSK).hour
    return SEND_HOUR_START <= current_hour < SEND_HOUR_END
