"""Прочитать и проанализировать Telegram группу/чат.

Чаппи читает сообщения (текст + медиа), анализирует через LLM,
извлекает инсайты о продуктах, ценах, рецептах, лайфхаках
и записывает в свой "дневник" — CHAPPIE_KNOWLEDGE.json.

Медиа (голосовые, кружочки) скачиваются и помечаются для
последующей транскрипции через Whisper.
"""

import asyncio
import json
import logging
import re
from pathlib import Path

from shared.ai_client_cli import claude_call

from chappie_engine.client import PersonalAccountClient
from chappie_engine.state.state_manager import StateManager
from chappie_engine.safety import SafetyGuard

logger = logging.getLogger("chappie.read_group")

MEDIA_DIR = Path(__file__).parent.parent / "content" / "downloaded_media"

ANALYSIS_PROMPT = """Ты — аналитик NL International. Проанализируй эти сообщения из Telegram-группы.

Извлеки полезные знания в JSON:
{
  "products_mentioned": [{"name": "...", "price": null, "pv": null, "context": "..."}],
  "recipes_tips": ["описание рецепта или совета"],
  "business_insights": ["инсайт про бизнес/квалификации/партнёрство"],
  "audience_interests": ["тема интересов аудитории"],
  "key_phrases": ["характерные фразы из группы, которые можно переиспользовать"],
  "summary": "краткое резюме в 2-3 предложениях"
}

Если полезного нет — верни {"summary": "нет полезной информации"}.
Верни ТОЛЬКО JSON, без markdown.

СООБЩЕНИЯ:
"""


async def _call_llm(
    instruction_prompt: str,
    messages_text: str,
    max_tokens: int = 2000,
) -> str | None:
    """Вызвать LLM через общий AI-клиент (Claude CLI).

    Args:
        instruction_prompt: Инструкции для LLM (доверенный промпт)
        messages_text: Текст сообщений из Telegram (внешние данные, изолируются)
        max_tokens: Игнорируется Claude CLI (оставлен для совместимости)
    """
    # claude_call — синхронный (subprocess), запускаем в thread pool.
    # Сообщения из Telegram передаются как untrusted_data — они изолируются
    # Input Guard'ом, что предотвращает prompt injection.
    result = await asyncio.to_thread(
        claude_call,
        instruction_prompt,
        "chappie",
        "",                      # system_prompt
        messages_text,           # untrusted_data
        "telegram_group",        # untrusted_source
    )
    return result


def _parse_llm_json(text: str) -> dict:
    """Извлечь JSON из ответа LLM."""
    if not text:
        return {}
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    return {}


def _classify_media(message) -> str:
    """Определить тип медиа в сообщении."""
    media = message.media
    if not media:
        return "none"
    type_name = type(media).__name__
    if "Photo" in type_name:
        return "photo"
    if "Document" in type_name:
        if hasattr(media, 'document') and media.document:
            mime = getattr(media.document, 'mime_type', '') or ''
            if 'audio/ogg' in mime or 'opus' in mime:
                return "voice"
            if 'video' in mime:
                # Проверяем кружочек
                for attr in getattr(media.document, 'attributes', []):
                    if hasattr(attr, 'round_message') and attr.round_message:
                        return "video_note"
                return "video"
            if 'image' in mime:
                return "photo"
        return "document"
    return "other"


async def run(group_identifier: str, limit: int = 10):
    """Прочитать последние сообщения из группы/чата и проанализировать через LLM.

    Args:
        group_identifier: Username группы (без @) или ID группы
        limit: Сколько сообщений прочитать (макс 30)
    """
    sm = StateManager()
    sg = SafetyGuard(sm)

    can, reason = sg.can_perform("read")
    if not can:
        print(f"Нельзя: {reason}")
        return

    limit = min(limit, 30)
    group_identifier = group_identifier.lstrip("@")

    print(f"Читаю группу/чат {group_identifier} (последние {limit} сообщений)...")

    try:
        async with PersonalAccountClient() as pac:
            client = pac.client

            # Получить entity
            try:
                entity = await client.get_entity(group_identifier)
            except Exception as e:
                error_msg = str(e)
                if "Could not find" in error_msg or "No user has" in error_msg:
                    try:
                        entity = await client.get_entity(int(group_identifier))
                    except Exception:
                        print(f"Группа/чат {group_identifier} не найден")
                        return
                else:
                    raise

            if not hasattr(entity, 'title'):
                print(f"{group_identifier} не является группой или чатом")
                return

            print(f"Группа/чат: {entity.title}")
            print(f"Участников: {getattr(entity, 'participants_count', 'неизвестно')}")

            # Прочитать ВСЕ сообщения (не только с текстом!)
            messages = []
            media_to_download = []

            async for message in client.iter_messages(entity, limit=limit):
                sender_name = "Неизвестно"
                try:
                    if message.sender:
                        sender_name = (
                            getattr(message.sender, 'first_name', '')
                            or getattr(message.sender, 'title', '')
                            or getattr(message.sender, 'username', '')
                            or 'Неизвестно'
                        )
                except Exception:
                    pass

                media_type = _classify_media(message)

                msg_data = {
                    "id": message.id,
                    "date": message.date.strftime("%Y-%m-%d %H:%M"),
                    "sender": sender_name,
                    "text": (message.text or "")[:500],
                    "is_reply": message.reply_to is not None,
                    "has_media": message.media is not None,
                    "media_type": media_type,
                    "reactions_count": _count_reactions(message),
                }
                messages.append(msg_data)

                # Голосовые и кружочки → пометить для скачивания
                if media_type in ("voice", "video_note"):
                    media_to_download.append({
                        "message": message,
                        "type": media_type,
                        "msg_id": message.id,
                    })

            if not messages:
                print("Сообщений не найдено")
                return

            # Скачать голосовые и кружочки для транскрипции
            downloaded_media = []
            if media_to_download:
                MEDIA_DIR.mkdir(parents=True, exist_ok=True)
                print(f"\nСкачиваю {len(media_to_download)} медиа (голосовые/кружочки)...")

                for item in media_to_download:
                    try:
                        safe_name = re.sub(r'[^\w\-]', '_', group_identifier)
                        filename = f"{safe_name}_{item['msg_id']}"
                        path = await client.download_media(
                            item["message"],
                            file=str(MEDIA_DIR / filename),
                        )
                        if path:
                            downloaded_media.append({
                                "msg_id": item["msg_id"],
                                "type": item["type"],
                                "path": str(path),
                                "needs_transcription": True,
                            })
                            print(f"  Скачано: {item['type']} (msg {item['msg_id']})")
                    except Exception as e:
                        logger.warning(f"Не удалось скачать медиа {item['msg_id']}: {e}")

            # Вывод сообщений
            print(f"\nНайдено {len(messages)} сообщений:")
            print("-" * 40)

            total_reactions = 0
            senders = {}
            reply_count = 0
            text_messages = 0
            media_messages = 0

            for msg in messages:
                emoji = ""
                if msg["media_type"] == "voice":
                    emoji = "[голосовое] "
                elif msg["media_type"] == "video_note":
                    emoji = "[кружочек] "
                elif msg["media_type"] == "photo":
                    emoji = "[фото] "
                elif msg["media_type"] == "video":
                    emoji = "[видео] "

                text_preview = msg["text"][:200] if msg["text"] else "(без текста)"
                if len(msg["text"]) > 200:
                    text_preview += "..."

                print(f"\n[{msg['date']}] {msg['sender']}:")
                print(f"  {emoji}{text_preview}")
                if msg["reactions_count"] > 0:
                    print(f"  Реакции: {msg['reactions_count']}")

                total_reactions += msg["reactions_count"]
                if msg["is_reply"]:
                    reply_count += 1
                if msg["text"]:
                    text_messages += 1
                if msg["has_media"]:
                    media_messages += 1

                sender = msg["sender"]
                senders[sender] = senders.get(sender, 0) + 1

            # Статистика
            avg_reactions = total_reactions // len(messages) if messages else 0
            reply_percentage = (reply_count / len(messages) * 100) if messages else 0
            top_senders = sorted(senders.items(), key=lambda x: x[1], reverse=True)[:3]

            print(f"\n--- СТАТИСТИКА {group_identifier} ---")
            print(f"Всего сообщений: {len(messages)}")
            print(f"  С текстом: {text_messages}, с медиа: {media_messages}")
            print(f"Уникальных отправителей: {len(senders)}")
            print(f"Средние реакции: {avg_reactions}")
            print(f"Процент ответов: {reply_percentage:.1f}%")

            if top_senders:
                print("Топ отправителей:")
                for sender, count in top_senders:
                    print(f"  {sender}: {count}")

            active_hours = _analyze_activity_hours(messages)
            if active_hours:
                print(f"Активные часы: {', '.join(map(str, active_hours))}")

            if downloaded_media:
                print(f"\nСкачано для транскрипции: {len(downloaded_media)}")
                for dm in downloaded_media:
                    print(f"  {dm['type']}: {dm['path']}")

            # LLM анализ — извлечение инсайтов
            text_for_analysis = []
            for msg in messages:
                if msg["text"]:
                    text_for_analysis.append(
                        f"[{msg['date']}] {msg['sender']}: {msg['text']}"
                    )

            llm_insights = {}
            if text_for_analysis:
                print(f"\nАнализирую {len(text_for_analysis)} сообщений через LLM...")
                combined_text = "\n".join(text_for_analysis[:15])  # Макс 15 для LLM
                # Передаём ANALYSIS_PROMPT как инструкции, а combined_text — как
                # внешние данные (untrusted_data), чтобы Input Guard изолировал их.
                llm_result = await _call_llm(ANALYSIS_PROMPT, combined_text)
                llm_insights = _parse_llm_json(llm_result)

                if llm_insights.get("summary"):
                    print(f"\nLLM резюме: {llm_insights['summary']}")
                if llm_insights.get("products_mentioned"):
                    print(f"Упомянуты продукты: {len(llm_insights['products_mentioned'])}")
                    for p in llm_insights["products_mentioned"][:5]:
                        print(f"  - {p.get('name', '?')}: {p.get('context', '')[:100]}")
                if llm_insights.get("recipes_tips"):
                    print(f"Рецепты/советы: {len(llm_insights['recipes_tips'])}")
                if llm_insights.get("business_insights"):
                    print(f"Бизнес-инсайты: {len(llm_insights['business_insights'])}")

            # Сохранить в дневник
            knowledge = sm.load_knowledge()

            insight = {
                "group": group_identifier,
                "title": entity.title,
                "scanned_at": _today_str(),
                "messages_count": len(messages),
                "text_messages": text_messages,
                "media_messages": media_messages,
                "unique_senders": len(senders),
                "avg_reactions": avg_reactions,
                "reply_percentage": reply_percentage,
                "top_senders": dict(top_senders) if senders else {},
                "active_hours": active_hours,
                "llm_analysis": llm_insights,
                "media_downloaded": len(downloaded_media),
                "pending_transcription": [
                    dm for dm in downloaded_media if dm.get("needs_transcription")
                ],
            }

            # Обновить group_insights
            existing = knowledge.get("group_insights", [])
            existing = [i for i in existing if i.get("group") != group_identifier]
            existing.append(insight)
            knowledge["group_insights"] = existing

            # Накапливать знания о продуктах из групп
            if llm_insights.get("products_mentioned"):
                group_products = knowledge.get("products_from_groups", [])
                for prod in llm_insights["products_mentioned"]:
                    prod["discovered_in"] = group_identifier
                    prod["discovered_at"] = _today_str()
                    # Не дублировать
                    exists = any(
                        gp.get("name", "").lower() == prod.get("name", "").lower()
                        and gp.get("discovered_in") == group_identifier
                        for gp in group_products
                    )
                    if not exists:
                        group_products.append(prod)
                knowledge["products_from_groups"] = group_products[-200:]  # Последние 200

            # Накапливать рецепты/советы
            if llm_insights.get("recipes_tips"):
                tips = knowledge.get("tips_from_groups", [])
                for tip in llm_insights["recipes_tips"]:
                    tips.append({
                        "tip": tip,
                        "from_group": group_identifier,
                        "date": _today_str(),
                    })
                knowledge["tips_from_groups"] = tips[-100:]  # Последние 100

            # Накапливать бизнес-инсайты
            if llm_insights.get("business_insights"):
                biz = knowledge.get("business_from_groups", [])
                for ins in llm_insights["business_insights"]:
                    biz.append({
                        "insight": ins,
                        "from_group": group_identifier,
                        "date": _today_str(),
                    })
                knowledge["business_from_groups"] = biz[-100:]

            sm.save_knowledge(knowledge)

            # Записать действие
            sg.record_action("read", success=True)

            sm.update_status(
                f"Анализ группы {group_identifier}: {len(messages)} сообщ, "
                f"{media_messages} медиа, LLM: {'да' if llm_insights else 'нет'}"
            )

    except Exception as e:
        logger.error(f"Ошибка при чтении группы {group_identifier}: {e}")
        sg.record_action("read", success=False)

        error_msg = str(e).lower()
        if "flood" in error_msg:
            match = re.search(r"(\d+)", str(e))
            if match:
                sg.handle_flood_wait(int(match.group(1)))
        elif "ban" in error_msg or "forbidden" in error_msg:
            sg.handle_ban_error(str(e))
        elif "chat" in error_msg and "forbidden" in error_msg:
            print(f"Нет доступа к группе {group_identifier}. Нужно быть участником.")
        elif "channel" in error_msg and "private" in error_msg:
            print(f"Группа {group_identifier} является приватной. Нужно быть участником.")

        print(f"Ошибка: {e}")


def _count_reactions(message) -> int:
    """Посчитать реакции на сообщение."""
    try:
        if message.reactions and message.reactions.results:
            return sum(r.count for r in message.reactions.results)
    except Exception:
        pass
    return 0


def _analyze_activity_hours(messages: list) -> list:
    """Проанализировать активные часы в группе."""
    hour_counts = {}
    for msg in messages:
        try:
            hour = int(msg["date"].split(" ")[1].split(":")[0])
            hour_counts[hour] = hour_counts.get(hour, 0) + 1
        except Exception:
            continue

    if not hour_counts:
        return []

    avg_count = sum(hour_counts.values()) / len(hour_counts)
    active_hours = [hour for hour, count in hour_counts.items() if count > avg_count]
    return sorted(active_hours)


def _today_str() -> str:
    from datetime import datetime, timezone, timedelta
    msk = timezone(timedelta(hours=3))
    return datetime.now(msk).strftime("%Y-%m-%d")
