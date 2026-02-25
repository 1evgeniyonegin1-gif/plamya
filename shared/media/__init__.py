"""
Модуль медиа-библиотеки

Экспорт:
- MediaLibrary: Основной класс для работы с медиа
- media_library: Singleton инстанс
"""

from .media_library import MediaLibrary, media_library

__all__ = ["MediaLibrary", "media_library"]
