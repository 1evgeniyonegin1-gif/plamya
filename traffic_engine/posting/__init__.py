"""
Posting Module — автопостинг контента в тематические каналы.

Публикует контент в каналы, привязанные к бот-аккаунтам (linked_channel_id).
Использует Telethon для реальной публикации, HumanSimulator для тайминга.
"""

from .auto_poster import AutoPoster

__all__ = ["AutoPoster"]
