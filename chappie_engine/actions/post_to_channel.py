"""Опубликовать пост в Telegram канал."""

import json
import logging
from pathlib import Path

from chappie_engine.client import PersonalAccountClient
from chappie_engine.state.state_manager import StateManager
from chappie_engine.safety import SafetyGuard

logger = logging.getLogger("chappie.post_to_channel")


async def run(channel_username: str, text: str = "", photo_path: str = ""):
    """Опубликовать пост в канал.

    Args:
        channel_username: Username канала (без @)
        text: Текст поста. Если пустой — генерируется через AI.
        photo_path: Путь к фото (опционально)
    """
    sm = StateManager()
    sg = SafetyGuard(sm)

    can, reason = sg.can_perform("post")
    if not can:
        print(f"Нельзя: {reason}")
        return

    channel_username = channel_username.lstrip("@")

    if not text:
        print("Текст поста не указан. Используй --text или добавь AI-генерацию.")
        return

    print(f"Публикую в @{channel_username}...")

    try:
        async with PersonalAccountClient() as pac:
            client = pac.client

            # Получить entity канала
            try:
                entity = await client.get_entity(channel_username)
            except Exception as e:
                print(f"Канал @{channel_username} не найден: {e}")
                return

            # Проверить что это канал и мы админ
            if not hasattr(entity, "broadcast") or not entity.broadcast:
                print(f"@{channel_username} не является каналом")
                return

            # Отправить
            if photo_path and Path(photo_path).exists():
                message = await client.send_file(
                    entity,
                    photo_path,
                    caption=text,
                    parse_mode="html",
                )
                print(f"Опубликован пост с фото (ID: {message.id})")
            else:
                message = await client.send_message(
                    entity,
                    text,
                    parse_mode="html",
                )
                print(f"Опубликован текстовый пост (ID: {message.id})")

            # Записать действие
            sg.record_action("post", success=True)

            # Сохранить в content_memory
            state = sm.load_state()
            memory = state.get("content_memory", [])
            memory.append({
                "channel": f"@{channel_username}",
                "text": text[:200],
                "msg_id": message.id,
                "date": message.date.strftime("%Y-%m-%d %H:%M"),
                "has_photo": bool(photo_path),
            })
            # Храним последние 50
            state["content_memory"] = memory[-50:]
            sm.save_state(state)

            sm.update_status(f"Пост в @{channel_username}: {text[:60]}...")

            print(f"\nГотово!")

    except Exception as e:
        logger.error(f"Ошибка публикации: {e}")
        sg.record_action("post", success=False)
        print(f"Ошибка: {e}")
