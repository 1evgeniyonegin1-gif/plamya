"""Чтение сообщений от Данила в личке.

Чаппи использует это чтобы:
- Прочитать советы и указания от Данила
- Увидеть ответы на свои отчёты
- Получить разрешения на действия

Использование:
    python -m chappie_engine.run read_messages [limit]
"""

import json
import logging
from datetime import datetime, timezone, timedelta

from chappie_engine.client import PersonalAccountClient
from chappie_engine.config import DANIL_TELEGRAM_ID, DANIL_USERNAME

logger = logging.getLogger("chappie.read_messages")

MSK = timezone(timedelta(hours=3))


async def run(limit: int = 10):
    """Прочитать последние сообщения из диалога с Данилом."""

    async with PersonalAccountClient() as account:
        try:
            # Находим Данила
            try:
                entity = await account.client.get_entity(DANIL_TELEGRAM_ID)
            except (ValueError, Exception):
                logger.info(f"Ищу Данила через @{DANIL_USERNAME}...")
                entity = await account.client.get_entity(DANIL_USERNAME)

            # Читаем последние сообщения
            messages = []
            async for msg in account.client.iter_messages(entity, limit=limit):
                if msg.text:
                    sender = "Данил" if msg.sender_id == DANIL_TELEGRAM_ID else "Чаппи"
                    msg_time = msg.date.astimezone(MSK).strftime("%Y-%m-%d %H:%M")
                    messages.append({
                        "from": sender,
                        "time": msg_time,
                        "text": msg.text,
                    })

            # Выводим в формате JSON для AI
            messages.reverse()  # хронологический порядок
            result = {
                "dialog_with": "Данил (@DanilLysenkoNL)",
                "messages_count": len(messages),
                "messages": messages,
            }
            print(json.dumps(result, ensure_ascii=False, indent=2))

            # Отмечаем как прочитанные
            await account.client.send_read_acknowledge(entity)
            logger.info(f"Прочитано {len(messages)} сообщений из диалога с Данилом")

        except Exception as e:
            logger.error(f"Ошибка чтения сообщений: {e}")
            print(f'{{"error": "{e}"}}')
