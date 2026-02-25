"""Создание Telegram канала.

Чаппи может создать broadcast-канал с заданными параметрами.

Использование:
    python -m chappie_engine.run create_channel --title "Название" --about "Описание" [--username "username"]
"""

import logging

from telethon.tl.functions.channels import CreateChannelRequest, UpdateUsernameRequest
from telethon.errors import UsernameOccupiedError, UsernameInvalidError

from chappie_engine.client import PersonalAccountClient

logger = logging.getLogger("chappie.create_channel")


async def run(title: str = "", about: str = "", username: str = ""):
    """Создать Telegram канал.
    
    Args:
        title: Название канала (обязательно)
        about: Описание канала (обязательно)
        username: Username для канала (опционально, можно установить позже)
    """

    if not title or not about:
        print("Ошибка: укажи --title и --about для создания канала")
        print('Пример: create_channel --title "Мой Канал" --about "Описание канала" --username "my_channel"')
        return

    async with PersonalAccountClient() as account:
        try:
            # Создаём канал (broadcast=True для публичного канала)
            result = await account.client(CreateChannelRequest(
                title=title,
                about=about,
                megagroup=False,  # False = канал (не группа)
                broadcast=True    # True = канал (broadcast)
            ))

            channel = result.chats[0]
            channel_id = channel.id
            
            print(f"✅ Канал создан!")
            print(f"   ID: {channel_id}")
            print(f"   Название: {title}")
            print(f"   Описание: {about[:50]}{'...' if len(about) > 50 else ''}")
            
            logger.info(f"Канал создан: {title} (ID: {channel_id})")

            # Устанавливаем username если указан
            if username:
                username = username.lstrip("@")
                try:
                    await account.client(UpdateUsernameRequest(
                        channel=channel,
                        username=username
                    ))
                    print(f"   Username: @{username}")
                    logger.info(f"Username установлен: @{username}")
                except UsernameOccupiedError:
                    print(f"   ⚠️  Username @{username} занят, канал создан без username")
                    logger.warning(f"Username @{username} занят")
                except UsernameInvalidError:
                    print(f"   ⚠️  Username @{username} недействителен, канал создан без username")
                    logger.warning(f"Username @{username} недействителен")
            else:
                print(f"   Username: не установлен (можно установить позже)")

        except Exception as e:
            logger.error(f"Ошибка создания канала: {e}")
            print(f"❌ Ошибка: {e}")
