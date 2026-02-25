"""Прочитать и проанализировать Telegram канал."""

import asyncio
import json
import logging

from chappie_engine.client import PersonalAccountClient
from chappie_engine.state.state_manager import StateManager
from chappie_engine.safety import SafetyGuard

logger = logging.getLogger("chappie.read_channel")


async def run(channel_username: str, limit: int = 10):
    """Прочитать последние посты из канала и проанализировать.

    Args:
        channel_username: Username канала (без @)
        limit: Сколько постов прочитать (макс 20)
    """
    sm = StateManager()
    sg = SafetyGuard(sm)

    # Проверить можно ли читать
    can, reason = sg.can_perform("read")
    if not can:
        print(f"Нельзя: {reason}")
        return

    limit = min(limit, 20)  # Не больше 20 за раз
    channel_username = channel_username.lstrip("@")

    print(f"Читаю канал @{channel_username} (последние {limit} постов)...")

    try:
        async with PersonalAccountClient() as pac:
            client = pac.client

            # Получить entity канала
            try:
                entity = await client.get_entity(channel_username)
            except Exception as e:
                error_msg = str(e)
                if "Could not find" in error_msg or "No user has" in error_msg:
                    print(f"Канал @{channel_username} не найден")
                    return
                raise

            print(f"Канал: {entity.title}")

            # Прочитать посты
            posts = []
            async for message in client.iter_messages(entity, limit=limit):
                if message.text:
                    posts.append({
                        "id": message.id,
                        "date": message.date.strftime("%Y-%m-%d %H:%M"),
                        "text": message.text[:500],  # Первые 500 символов
                        "views": getattr(message, "views", 0) or 0,
                        "forwards": getattr(message, "forwards", 0) or 0,
                        "has_media": message.media is not None,
                        "reactions_count": _count_reactions(message),
                    })

            if not posts:
                print("Постов с текстом не найдено")
                return

            print(f"\nНайдено {len(posts)} постов:")
            print("-" * 40)

            total_views = 0
            total_reactions = 0
            total_forwards = 0

            for post in posts:
                print(f"\n[{post['date']}] Views: {post['views']} | Reactions: {post['reactions_count']} | Forwards: {post['forwards']}")
                # Показываем первые 200 символов
                text_preview = post["text"][:200]
                if len(post["text"]) > 200:
                    text_preview += "..."
                print(f"  {text_preview}")

                total_views += post["views"]
                total_reactions += post["reactions_count"]
                total_forwards += post["forwards"]

            # Статистика
            avg_views = total_views // len(posts) if posts else 0
            avg_reactions = total_reactions // len(posts) if posts else 0

            print(f"\n--- СТАТИСТИКА @{channel_username} ---")
            print(f"Постов: {len(posts)}")
            print(f"Средние просмотры: {avg_views}")
            print(f"Средние реакции: {avg_reactions}")
            print(f"Всего репостов: {total_forwards}")

            # Сохранить инсайт
            knowledge = sm.load_knowledge()
            insight = {
                "channel": f"@{channel_username}",
                "scanned_at": sm._today() if hasattr(sm, '_today') else None,
                "posts_count": len(posts),
                "avg_views": avg_views,
                "avg_reactions": avg_reactions,
                "top_themes": _extract_themes(posts),
            }

            # Заменить старый инсайт или добавить новый
            existing = knowledge.get("competitor_insights", [])
            existing = [i for i in existing if i.get("channel") != f"@{channel_username}"]
            existing.append(insight)
            knowledge["competitor_insights"] = existing
            sm.save_knowledge(knowledge)

            # Записать действие
            sg.record_action("read", success=True)

            # Обновить STATUS
            sm.update_status(
                f"Анализ @{channel_username}: {len(posts)} постов, "
                f"avg {avg_views} views, {avg_reactions} reactions"
            )

            # Вывести JSON для AI анализа
            print(f"\n--- JSON для анализа ---")
            print(json.dumps({
                "channel": f"@{channel_username}",
                "posts": posts[:5],  # Первые 5 для AI
                "stats": {
                    "avg_views": avg_views,
                    "avg_reactions": avg_reactions,
                    "total_forwards": total_forwards,
                }
            }, ensure_ascii=False, indent=2))

    except Exception as e:
        logger.error(f"Ошибка при чтении @{channel_username}: {e}")
        sg.record_action("read", success=False)

        error_msg = str(e).lower()
        if "flood" in error_msg:
            # Извлечь секунды из FloodWaitError
            import re
            match = re.search(r"(\d+)", str(e))
            if match:
                sg.handle_flood_wait(int(match.group(1)))
        elif "ban" in error_msg or "forbidden" in error_msg:
            sg.handle_ban_error(str(e))

        print(f"Ошибка: {e}")


def _count_reactions(message) -> int:
    """Посчитать реакции на пост."""
    try:
        if message.reactions and message.reactions.results:
            return sum(r.count for r in message.reactions.results)
    except Exception:
        pass
    return 0


def _extract_themes(posts: list) -> list[str]:
    """Извлечь основные темы из постов (простой keyword анализ)."""
    keywords = {
        "здоровье": ["здоров", "витамин", "иммунит", "организм", "питан"],
        "продукт": ["продукт", "состав", "натуральн", "сертифик"],
        "бизнес": ["бизнес", "доход", "заработ", "партнёр", "партнер", "квалифик"],
        "мотивация": ["мечт", "цел", "успех", "путь", "мотива"],
        "отзыв": ["отзыв", "результат", "до и после", "помог", "рекоменд"],
        "акция": ["акци", "скидк", "промо", "специальн"],
    }

    theme_counts = {}
    all_text = " ".join(p["text"].lower() for p in posts)

    for theme, kws in keywords.items():
        count = sum(all_text.count(kw) for kw in kws)
        if count > 0:
            theme_counts[theme] = count

    # Топ-3 темы
    sorted_themes = sorted(theme_counts.items(), key=lambda x: x[1], reverse=True)
    return [t[0] for t in sorted_themes[:3]]
