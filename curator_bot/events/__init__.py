"""
События и уведомления для curator_bot.

Модули:
- event_consumer: Обработка событий из system_events
- notification_service: Отправка уведомлений пользователям
"""
from .event_consumer import process_pending_events
from .notification_service import send_post_notification

__all__ = ["process_pending_events", "send_post_notification"]
