"""Взаимодействие с Telegram ботами.

Возможности:
1. Отправка сообщений боту
2. Чтение ответов от бота
3. Получение информации о боте
"""

import asyncio
import json
import logging
import re
import time

from chappie_engine.client import PersonalAccountClient
from chappie_engine.state.state_manager import StateManager
from chappie_engine.safety import SafetyGuard

logger = logging.getLogger("chappie.interact_bot")


async def run(bot_username: str, message: str = None, limit: int = 5, wait_seconds: int = 3):
    """Взаимодействовать с ботом.

    Args:
        bot_username: Username бота (без @)
        message: Сообщение для отправки (если None - только чтение)
        limit: Сколько сообщений прочитать (макс 10)
        wait_seconds: Сколько секунд ждать ответа от бота
    """
    sm = StateManager()
    sg = SafetyGuard(sm)

    # Проверить можно ли взаимодействовать
    can, reason = sg.can_perform("interact")
    if not can:
        print(f"Нельзя: {reason}")
        return

    limit = min(limit, 10)  # Не больше 10 за раз
    bot_username = bot_username.lstrip("@")

    print(f"Взаимодействие с ботом @{bot_username}...")

    try:
        async with PersonalAccountClient() as pac:
            client = pac.client

            # Получить entity бота
            try:
                entity = await client.get_entity(bot_username)
            except Exception as e:
                error_msg = str(e)
                if "Could not find" in error_msg or "No user has" in error_msg:
                    print(f"Бот @{bot_username} не найден")
                    return
                raise

            # Проверить, что это бот
            if not getattr(entity, 'bot', False):
                print(f"@{bot_username} не является ботом")
                return

            print(f"Бот: {getattr(entity, 'first_name', '') or getattr(entity, 'title', '')}")
            print(f"Описание: {getattr(entity, 'about', 'не указано')}")

            # Получить информацию о боте
            bot_info = {
                "username": f"@{bot_username}",
                "name": getattr(entity, 'first_name', '') or getattr(entity, 'title', ''),
                "description": getattr(entity, 'about', ''),
                "is_bot": True,
                "verified": getattr(entity, 'verified', False),
                "premium": getattr(entity, 'premium', False),
            }

            # Если нужно отправить сообщение
            last_message_id = None
            if message:
                print(f"\nОтправляю сообщение боту: \"{message}\"")
                try:
                    sent_msg = await client.send_message(entity, message)
                    last_message_id = sent_msg.id
                    print(f"Сообщение отправлено (ID: {last_message_id})")
                    
                    # Ждем ответа
                    if wait_seconds > 0:
                        print(f"Жду ответа {wait_seconds} секунд...")
                        await asyncio.sleep(wait_seconds)
                except Exception as e:
                    print(f"Ошибка при отправке: {e}")
                    sg.record_action("interact", success=False)
                    return

            # Читаем сообщения от бота
            print(f"\nЧитаю последние {limit} сообщений от бота...")
            bot_messages = []
            async for msg in client.iter_messages(entity, limit=limit):
                if msg.text:
                    # Определяем, кто отправил
                    sender_is_bot = False
                    try:
                        if msg.sender:
                            sender_is_bot = getattr(msg.sender, 'bot', False)
                    except Exception:
                        pass

                    bot_messages.append({
                        "id": msg.id,
                        "date": msg.date.strftime("%Y-%m-%d %H:%M"),
                        "from_bot": sender_is_bot,
                        "text": msg.text[:1000],  # Первые 1000 символов
                        "has_buttons": _has_buttons(msg),
                        "has_media": msg.media is not None,
                        "is_reply_to_me": msg.reply_to and msg.reply_to.reply_to_msg_id == last_message_id if last_message_id else False,
                    })

            if not bot_messages:
                print("Сообщений от бота не найдено")
                return

            # Фильтруем сообщения от бота
            from_bot_messages = [m for m in bot_messages if m["from_bot"]]
            from_me_messages = [m for m in bot_messages if not m["from_bot"]]

            print(f"\nНайдено {len(bot_messages)} сообщений в диалоге:")
            print(f"  От бота: {len(from_bot_messages)}")
            print(f"  От меня: {len(from_me_messages)}")

            if from_bot_messages:
                print(f"\n--- ПОСЛЕДНИЕ СООБЩЕНИЯ ОТ БОТА ---")
                for msg in from_bot_messages[:3]:  # Показываем последние 3
                    print(f"\n[{msg['date']}] Бот:")
                    text_preview = msg["text"][:300]
                    if len(msg["text"]) > 300:
                        text_preview += "..."
                    print(f"  {text_preview}")
                    if msg["has_buttons"]:
                        print(f"  [Есть кнопки]")
                    if msg["is_reply_to_me"]:
                        print(f"  [Ответ на моё сообщение]")

            # Анализ бота
            bot_analysis = _analyze_bot(from_bot_messages, bot_info)

            print(f"\n--- АНАЛИЗ БОТА @{bot_username} ---")
            print(f"Тип: {bot_analysis['bot_type']}")
            print(f"Функции: {', '.join(bot_analysis['features'])}")
            if bot_analysis['common_patterns']:
                print(f"Паттерны: {', '.join(bot_analysis['common_patterns'])}")
            print(f"Активность: {bot_analysis['activity_level']}")

            # Сохранить информацию о боте
            knowledge = sm.load_knowledge()
            bot_data = {
                "username": f"@{bot_username}",
                "scanned_at": sm._today() if hasattr(sm, '_today') else None,
                "info": bot_info,
                "analysis": bot_analysis,
                "last_messages": from_bot_messages[:5],  # Сохраняем последние 5 сообщений
            }

            # Заменить старые данные или добавить новые
            existing = knowledge.get("bot_insights", [])
            existing = [b for b in existing if b.get("username") != f"@{bot_username}"]
            existing.append(bot_data)
            knowledge["bot_insights"] = existing
            sm.save_knowledge(knowledge)

            # Записать действие
            sg.record_action("interact", success=True)

            # Обновить STATUS
            sm.update_status(
                f"Взаимодействие с ботом @{bot_username}: {bot_analysis['bot_type']}, "
                f"{len(from_bot_messages)} сообщений"
            )

            # Вывести JSON для AI анализа
            print(f"\n--- JSON для анализа ---")
            print(json.dumps({
                "bot": f"@{bot_username}",
                "info": bot_info,
                "analysis": bot_analysis,
                "last_messages": from_bot_messages[:3],
            }, ensure_ascii=False, indent=2))

    except Exception as e:
        logger.error(f"Ошибка при взаимодействии с ботом @{bot_username}: {e}")
        sg.record_action("interact", success=False)

        error_msg = str(e).lower()
        if "flood" in error_msg:
            # Извлечь секунды из FloodWaitError
            match = re.search(r"(\d+)", str(e))
            if match:
                sg.handle_flood_wait(int(match.group(1)))
        elif "ban" in error_msg or "forbidden" in error_msg:
            sg.handle_ban_error(str(e))
        elif "bot" in error_msg and "blocked" in error_msg:
            print(f"Бот @{bot_username} заблокировал вас или недоступен.")

        print(f"Ошибка: {e}")


def _has_buttons(message) -> bool:
    """Проверить, есть ли у сообщения кнопки."""
    try:
        return message.reply_markup is not None
    except Exception:
        return False


def _analyze_bot(messages: list, bot_info: dict) -> dict:
    """Проанализировать бота на основе его сообщений."""
    
    features = set()
    common_patterns = []
    all_text = " ".join(m["text"].lower() for m in messages)
    
    # Определение типа бота
    bot_type = "unknown"
    
    # Ключевые слова для определения типа
    type_keywords = {
        "assistant": ["помощ", "ассистент", "help", "assistant", "подскаж", "совет"],
        "news": ["новост", "news", "обновлен", "update", "релиз"],
        "product": ["продукт", "товар", "product", "купи", "заказ", "цена", "стоимость"],
        "service": ["сервис", "service", "услуг", "подписк", "subscription"],
        "education": ["обучен", "курс", "education", "урок", "задани", "тест"],
        "entertainment": ["игр", "game", "развлеч", "entertainment", "музык", "music"],
        "utility": ["погод", "weather", "перевод", "translate", "калькулятор", "calculator"],
    }
    
    for bot_type_name, keywords in type_keywords.items():
        if any(keyword in all_text for keyword in keywords):
            bot_type = bot_type_name
            break
    
    # Определение функций
    if any(word in all_text for word in ["меню", "menu", "кнопк", "button", "выбор", "choose"]):
        features.add("menu_buttons")
    
    if any(word in all_text for word in ["команд", "command", "/start", "/help"]):
        features.add("commands")
    
    if any(word in all_text for word in ["оплат", "payment", "купи", "buy", "цена"]):
        features.add("payments")
    
    if any(word in all_text for word in ["подписк", "subscribe", "канал", "channel"]):
        features.add("subscriptions")
    
    if any(word in all_text for word in ["опрос", "poll", "голосован", "vote"]):
        features.add("polls")
    
    if any(word in all_text for word in ["файл", "file", "документ", "document", "изображен", "image"]):
        features.add("file_sharing")
    
    # Определение паттернов
    if len(messages) > 1:
        # Проверяем на шаблонные ответы
        texts = [m["text"].lower() for m in messages]
        if any(text.startswith("привет") or text.startswith("hello") for text in texts):
            common_patterns.append("greeting")
        
        if any("спасибо" in text or "thank you" in text for text in texts):
            common_patterns.append("thanks")
        
        if any("ошибк" in text or "error" in text for text in texts):
            common_patterns.append("error_messages")
        
        if any("выбор" in text or "select" in text or "вариант" in text for text in texts):
            common_patterns.append("choice_prompts")
    
    # Уровень активности
    activity_level = "low"
    if len(messages) >= 5:
        activity_level = "high"
    elif len(messages) >= 2:
        activity_level = "medium"
    
    return {
        "bot_type": bot_type,
        "features": list(features),
        "common_patterns": common_patterns,
        "activity_level": activity_level,
        "messages_analyzed": len(messages),
    }