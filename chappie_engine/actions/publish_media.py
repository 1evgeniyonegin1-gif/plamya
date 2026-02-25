"""Опубликовать медиа (голосовое, кружочек, фото, видео) от имени Чаппи.

Сценарий:
1. Чаппи просит Данила записать контент (кружочек, голосовое)
2. Данил присылает файл Чаппи в личку
3. Чаппи скачивает файл
4. Публикует в целевой канал/группу от своего имени

Варианты:
- download + send_file (надёжнее — нет "forwarded from")
- forward без автора (ограничения: канал должен разрешать)
"""

import logging
import os
from pathlib import Path

from chappie_engine.client import PersonalAccountClient
from chappie_engine.state.state_manager import StateManager
from chappie_engine.safety import SafetyGuard

logger = logging.getLogger("chappie.publish_media")

# Расширения для автоопределения типа
VOICE_EXTENSIONS = {".ogg", ".oga", ".opus"}
VIDEO_NOTE_EXTENSIONS = {".mp4"}  # кружочки обычно mp4
PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv"}


def _detect_media_type(file_path: str) -> str:
    """Автоопределение типа медиа по расширению."""
    ext = Path(file_path).suffix.lower()

    if ext in VOICE_EXTENSIONS:
        return "voice"
    if ext in PHOTO_EXTENSIONS:
        return "photo"
    if ext in VIDEO_EXTENSIONS:
        return "video"  # может быть и video_note, определяется по --type
    return "document"


async def run(target: str, media_path: str, media_type: str = "auto"):
    """Опубликовать медиа в канал/группу/чат.

    Args:
        target: Username или ID канала/группы
        media_path: Путь к медиа файлу
        media_type: Тип: voice, video_note, photo, video, auto
    """
    sm = StateManager()
    sg = SafetyGuard(sm)

    can, reason = sg.can_perform("post")
    if not can:
        print(f"Нельзя: {reason}")
        return

    if not os.path.exists(media_path):
        print(f"Файл не найден: {media_path}")
        return

    target = target.lstrip("@")

    if media_type == "auto":
        media_type = _detect_media_type(media_path)

    file_size = os.path.getsize(media_path)
    print(f"Публикую {media_type} ({file_size} bytes) в {target}...")

    try:
        async with PersonalAccountClient() as pac:
            client = pac.client

            # Получить entity
            try:
                entity = await client.get_entity(target)
            except Exception:
                try:
                    entity = await client.get_entity(int(target))
                except Exception:
                    print(f"Чат {target} не найден")
                    return

            # Отправить в зависимости от типа
            if media_type == "voice":
                message = await client.send_file(
                    entity,
                    media_path,
                    voice_note=True,
                )
                print(f"Голосовое опубликовано (ID: {message.id})")

            elif media_type == "video_note":
                message = await client.send_file(
                    entity,
                    media_path,
                    video_note=True,
                )
                print(f"Кружочек опубликован (ID: {message.id})")

            elif media_type == "photo":
                message = await client.send_file(
                    entity,
                    media_path,
                    force_document=False,
                )
                print(f"Фото опубликовано (ID: {message.id})")

            elif media_type == "video":
                message = await client.send_file(
                    entity,
                    media_path,
                    supports_streaming=True,
                )
                print(f"Видео опубликовано (ID: {message.id})")

            else:
                message = await client.send_file(entity, media_path)
                print(f"Файл опубликован (ID: {message.id})")

            sg.record_action("post", success=True)
            sm.update_status(f"Опубликовано {media_type} в {target}")

    except Exception as e:
        logger.error(f"Ошибка публикации медиа: {e}")
        sg.record_action("post", success=False)
        print(f"Ошибка: {e}")


async def download_and_publish(source_chat_id: int, message_id: int, target: str):
    """Скачать медиа из сообщения Данила и опубликовать в target.

    Вариант 'download + send_file' — без 'forwarded from'.

    Args:
        source_chat_id: ID чата откуда скачивать (обычно Данил)
        message_id: ID сообщения с медиа
        target: Куда публиковать (username канала)
    """
    sm = StateManager()
    sg = SafetyGuard(sm)

    can, reason = sg.can_perform("post")
    if not can:
        print(f"Нельзя: {reason}")
        return

    try:
        async with PersonalAccountClient() as pac:
            client = pac.client
            tmp_dir = Path(__file__).parent.parent / "content" / "tmp_media"
            tmp_dir.mkdir(parents=True, exist_ok=True)

            # Скачать
            source_entity = await client.get_entity(source_chat_id)
            messages = await client.get_messages(source_entity, ids=message_id)
            if not messages or not messages.media:
                print(f"Сообщение {message_id} не содержит медиа")
                return

            msg = messages
            path = await client.download_media(msg, file=str(tmp_dir))
            if not path:
                print("Не удалось скачать медиа")
                return

            print(f"Скачано: {path}")

            # Определить тип
            from chappie_engine.actions.download_media import _classify_media
            mtype = _classify_media(msg)

            # Отправить в target
            target_entity = await client.get_entity(target.lstrip("@"))

            kwargs = {}
            if mtype == "voice":
                kwargs["voice_note"] = True
            elif mtype == "video":
                # Проверить — если это кружочек (video_note)
                if hasattr(msg.media, "document"):
                    for attr in msg.media.document.attributes:
                        if hasattr(attr, "round_message") and attr.round_message:
                            kwargs["video_note"] = True
                            break
                if "video_note" not in kwargs:
                    kwargs["supports_streaming"] = True

            new_msg = await client.send_file(
                target_entity,
                path,
                caption=msg.text or "",
                **kwargs,
            )

            # Удалить временный файл
            try:
                os.unlink(path)
            except OSError:
                pass

            sg.record_action("post", success=True)
            sm.update_status(f"Переопубликовано {mtype} в {target}")
            print(f"Опубликовано в {target} (ID: {new_msg.id})")

    except Exception as e:
        logger.error(f"Ошибка download_and_publish: {e}")
        sg.record_action("post", success=False)
        print(f"Ошибка: {e}")
