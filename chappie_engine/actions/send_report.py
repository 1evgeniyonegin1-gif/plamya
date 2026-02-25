"""Отправка отчёта Данилу в личные сообщения Telegram.

Чаппи использует это действие чтобы:
- Рассказать что он сейчас делает / думает
- Отчитаться о прогрессе
- Спросить разрешение на действие
- Сообщить о проблеме

Использование:
    python -m chappie_engine.run send_report "Текст сообщения"
"""

import logging

from chappie_engine.client import PersonalAccountClient
from chappie_engine.config import DANIL_TELEGRAM_ID, DANIL_USERNAME
from chappie_engine.state.state_manager import StateManager

logger = logging.getLogger("chappie.send_report")


async def run(message: str):
    """Отправить сообщение Данилу в личку."""

    if not message or not message.strip():
        print("Ошибка: пустое сообщение")
        return

    state = StateManager()

    # Проверяем бан
    state_data = state.load_state()
    if state_data.get("banned_until"):
        print("Аккаунт заблокирован. Не могу отправить сообщение.")
        return

    async with PersonalAccountClient() as account:
        try:
            # Находим Данила — сначала по ID, потом по username
            entity = None
            try:
                entity = await account.client.get_entity(DANIL_TELEGRAM_ID)
            except (ValueError, Exception):
                # По ID не нашли — ищем через username
                logger.info(f"Ищу Данила через @{DANIL_USERNAME}...")
                try:
                    entity = await account.client.get_entity(DANIL_USERNAME)
                except (ValueError, Exception) as e:
                    print(f"❌ Не могу найти @{DANIL_USERNAME}: {e}")
                    return

            # Отправляем сообщение Данилу
            await account.client.send_message(
                entity,
                message,
                parse_mode="html",
            )

            # Записываем в state — считаем как report, не DM
            today = __import__("datetime").date.today().isoformat()
            if today not in state_data.get("daily_actions", {}):
                state_data.setdefault("daily_actions", {})[today] = {}
            state_data["daily_actions"][today]["reports"] = (
                state_data["daily_actions"][today].get("reports", 0) + 1
            )
            state_data.setdefault("total_actions", {})["reports"] = (
                state_data["total_actions"].get("reports", 0) + 1
            )
            state.save_state(state_data)

            print(f"✅ Отчёт отправлен Данилу ({len(message)} символов)")
            logger.info(f"Отчёт отправлен Данилу: {message[:80]}...")

        except Exception as e:
            logger.error(f"Ошибка отправки отчёта: {e}")
            print(f"❌ Ошибка: {e}")
