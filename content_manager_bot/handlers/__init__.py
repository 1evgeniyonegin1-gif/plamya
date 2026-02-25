"""
Обработчики команд и callback для контент-менеджер бота
"""
from content_manager_bot.handlers.admin import router as admin_router
from content_manager_bot.handlers.callbacks import router as callbacks_router
from content_manager_bot.handlers.channel_admin import router as channel_admin_router
from content_manager_bot.handlers.vip_welcome import router as vip_welcome_router

__all__ = ["admin_router", "callbacks_router", "channel_admin_router", "vip_welcome_router"]
