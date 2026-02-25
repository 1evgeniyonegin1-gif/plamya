"""
Модуль уведомлений о лидах
"""

from curator_bot.notifications.lead_alerts import (
    notify_hot_lead,
    notify_new_contact,
)

__all__ = [
    "notify_hot_lead",
    "notify_new_contact",
]
