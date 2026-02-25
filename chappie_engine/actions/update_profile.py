"""Обновление профиля Telegram аккаунта.

Чаппи может менять:
- Имя и фамилию
- Bio (описание)
- Username
- Аватарку (фото профиля)

Использование:
    python -m chappie_engine.run update_profile --name "Имя" [--last_name "Фамилия"] [--bio "Описание"] [--username "username"] [--photo "путь/к/фото.jpg"]
"""

import logging
from pathlib import Path

from telethon.tl.functions.account import UpdateProfileRequest, UpdateUsernameRequest
from telethon.tl.functions.photos import UploadProfilePhotoRequest, DeletePhotosRequest
from telethon.tl.types import InputPhoto

from chappie_engine.client import PersonalAccountClient

logger = logging.getLogger("chappie.update_profile")


async def run(first_name: str = "", last_name: str = "", bio: str = "", username: str = "", photo: str = ""):
    """Обновить профиль Telegram аккаунта."""

    if not any([first_name, last_name, bio, username, photo]):
        print("Ошибка: укажи хотя бы один параметр (--name, --last_name, --bio, --username, --photo)")
        return

    async with PersonalAccountClient() as account:
        try:
            changes = []

            # Обновляем имя/фамилию/bio
            if first_name or last_name or bio:
                kwargs = {}
                if first_name:
                    kwargs["first_name"] = first_name
                    changes.append(f"имя → {first_name}")
                if last_name:
                    kwargs["last_name"] = last_name
                    changes.append(f"фамилия → {last_name}")
                if bio:
                    kwargs["about"] = bio
                    changes.append(f"bio → {bio[:50]}...")

                await account.client(UpdateProfileRequest(**kwargs))

            # Обновляем username
            if username:
                # Убираем @ если есть
                username = username.lstrip("@")
                await account.client(UpdateUsernameRequest(username=username))
                changes.append(f"username → @{username}")

            # Обновляем аватарку
            if photo:
                photo_path = Path(photo)
                if not photo_path.exists():
                    print(f"❌ Файл не найден: {photo}")
                    return
                
                # Сначала удаляем старые фото (опционально, можно пропустить)
                # await _delete_old_photos(account.client)
                
                # Загружаем новое фото
                file = await account.client.upload_file(photo_path)
                result = await account.client(UploadProfilePhotoRequest(file=file))
                changes.append(f"аватарка → {photo_path.name}")
                logger.info(f"Аватарка загружена: {result}")

            print(f"✅ Профиль обновлён: {', '.join(changes)}")
            logger.info(f"Профиль обновлён: {', '.join(changes)}")

        except Exception as e:
            logger.error(f"Ошибка обновления профиля: {e}")
            print(f"❌ Ошибка: {e}")


async def _delete_old_photos(client):
    """Удалить старые фото профиля (опционально)."""
    try:
        photos = await client.get_profile_photos('me')
        if photos:
            photo_ids = [InputPhoto(id=p.id, access_hash=p.access_hash) for p in photos]
            await client(DeletePhotosRequest(id=photo_ids))
            logger.info(f"Удалено {len(photo_ids)} старых фото профиля")
    except Exception as e:
        logger.warning(f"Не удалось удалить старые фото: {e}")
