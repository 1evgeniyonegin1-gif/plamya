#!/usr/bin/env python3
"""
Импорт экспорта Telegram канала "РАБОЧИЙ КАНАЛ NL" в структуру testimonials.

Скрипт:
1. Парсит result.json и группирует сообщения по топикам
2. Маппит топики на категории (before_after, checks, products, success_stories)
3. Копирует медиафайлы (фото, видео, кружки, голосовые)
4. Создаёт metadata.json для TestimonialsManager

Использование:
    python scripts/import_nl_channel.py

Автор: Claude Code
Дата: 2026-01-27
"""

import json
import shutil
import sys
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict

# Установка кодировки для Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# === ПУТИ ===
EXPORT_PATH = Path(r"C:\Users\mafio\Downloads\Telegram Desktop\экспорт рабочего канала нл с фотками")
PROJECT_ROOT = Path(__file__).parent.parent
TESTIMONIALS_DIR = PROJECT_ROOT / "content" / "testimonials"

# === МАППИНГ ТОПИКОВ НА КАТЕГОРИИ ===
# Ключевые слова в названии топика -> категория testimonials
TOPIC_TO_CATEGORY = {
    # before_after - результаты ДО/ПОСЛЕ
    "до/после": "before_after",
    "до после": "before_after",
    "итоги и отзывы марафонов": "before_after",

    # checks - чеки партнёров
    "чеки партнеров": "checks",
    "чеки партнёров": "checks",

    # success_stories - истории успеха, мотивация
    "истории успеха": "success_stories",
    "возражения": "success_stories",
    "мотивация": "success_stories",
    "про адаптогены": "success_stories",
    "про бады": "success_stories",
    "про детокс": "success_stories",

    # products - карточки продуктов, отзывы о продуктах
    "карточки продуктов": "products",
    "отзывы": "products",
    "прогревы к марафонам": "products",
    "инструкции к продуктам": "products",
    "рецепты": "products",
}

# Подкатегории для before_after (по продуктам)
BEFORE_AFTER_SUBCATEGORIES = {
    "похудение": "weight_loss",
    "похудения": "weight_loss",
    "стройности": "weight_loss",
    "коллаген": "collagen",
    "драйн": "drain_effect",
    "draineffect": "drain_effect",
    "детокс": "detox",
    "волосы": "hair",
    "выпадение волос": "hair",
    "3d slime": "slime_3d",
    "slime": "slime_3d",
    "уход для лица": "skin_care",
    "патчи": "patches",
    "целлюлит": "cellulite",
    "набора массы": "weight_gain",
    "витаминов": "vitamins",
    "бьюти бленд": "beauty_blend",
    "адаптогены": "adaptogens",
    "smartum": "smartum",
}


def extract_text(text_field) -> str:
    """Извлекает текст из поля text (может быть строкой или списком)."""
    if isinstance(text_field, str):
        return text_field.strip()

    if isinstance(text_field, list):
        parts = []
        for item in text_field:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and "text" in item:
                parts.append(item["text"])
        return "".join(parts).strip()

    return ""


def get_category_for_topic(topic_title: str) -> Optional[str]:
    """Определяет категорию по названию топика."""
    title_lower = topic_title.lower()

    for keyword, category in TOPIC_TO_CATEGORY.items():
        if keyword in title_lower:
            return category

    # Если содержит "до/после" или "отзыв" - это before_after или products
    if "до/после" in title_lower or "до после" in title_lower:
        return "before_after"
    if "отзыв" in title_lower:
        return "products"

    return None


def get_subcategory(topic_title: str) -> Optional[str]:
    """Определяет подкатегорию для before_after."""
    title_lower = topic_title.lower()

    for keyword, subcategory in BEFORE_AFTER_SUBCATEGORIES.items():
        if keyword in title_lower:
            return subcategory

    return None


def get_media_info(msg: Dict) -> Dict[str, Any]:
    """Извлекает информацию о медиа из сообщения."""
    media_info = {
        "has_media": False,
        "has_photo": False,
        "has_video": False,
        "has_voice": False,
        "has_video_message": False,
        "media_types": [],
        "files": []
    }

    # Фото
    if msg.get("photo"):
        media_info["has_media"] = True
        media_info["has_photo"] = True
        media_info["media_types"].append("photo")
        media_info["files"].append({
            "type": "photo",
            "path": msg["photo"],
            "width": msg.get("width"),
            "height": msg.get("height")
        })

    # Видео / кружки / голосовые
    media_type = msg.get("media_type")
    if media_type == "video_file":
        media_info["has_media"] = True
        media_info["has_video"] = True
        media_info["media_types"].append("video")
        media_info["files"].append({
            "type": "video",
            "path": msg.get("file"),
            "duration": msg.get("duration_seconds"),
            "width": msg.get("width"),
            "height": msg.get("height")
        })
    elif media_type == "video_message":
        media_info["has_media"] = True
        media_info["has_video_message"] = True
        media_info["media_types"].append("video_message")
        media_info["files"].append({
            "type": "video_message",
            "path": msg.get("file"),
            "duration": msg.get("duration_seconds")
        })
    elif media_type == "voice_message":
        media_info["has_media"] = True
        media_info["has_voice"] = True
        media_info["media_types"].append("voice")
        media_info["files"].append({
            "type": "voice",
            "path": msg.get("file"),
            "duration": msg.get("duration_seconds")
        })

    return media_info


def copy_media_file(src_path: str, dest_dir: Path, msg_id: int, media_type: str) -> Optional[str]:
    """Копирует медиафайл и возвращает новый путь."""
    if not src_path or src_path.startswith("(File"):
        return None

    src_file = EXPORT_PATH / src_path
    if not src_file.exists():
        return None

    # Создаём имя файла
    extension = src_file.suffix
    dest_filename = f"msg_{msg_id}_{media_type}{extension}"
    dest_file = dest_dir / dest_filename

    # Копируем если не существует
    if not dest_file.exists():
        shutil.copy2(src_file, dest_file)

    return dest_filename


def import_channel():
    """Основная функция импорта."""
    print("=" * 80)
    print("ИМПОРТ КАНАЛА 'РАБОЧИЙ КАНАЛ NL' В TESTIMONIALS")
    print("=" * 80)

    # Загружаем экспорт
    result_json = EXPORT_PATH / "result.json"
    if not result_json.exists():
        print(f"❌ Файл не найден: {result_json}")
        return

    print(f"\n📂 Загружаю: {result_json}")
    with open(result_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    messages = data.get("messages", [])
    print(f"📝 Всего сообщений: {len(messages)}")

    # === ШАГ 1: Собираем топики ===
    print("\n📋 Анализирую топики...")
    topics = {}  # id -> {title, messages: [...]}

    for msg in messages:
        if msg.get("action") == "topic_created":
            topics[msg["id"]] = {
                "title": msg["title"],
                "category": get_category_for_topic(msg["title"]),
                "subcategory": get_subcategory(msg["title"]),
                "messages": []
            }

    print(f"   Найдено топиков: {len(topics)}")

    # === ШАГ 2: Распределяем сообщения по топикам ===
    print("\n📨 Распределяю сообщения по топикам...")

    # В Telegram экспорте сообщения связаны через reply_to_message_id
    # Но также они могут быть в thread (поле "reply_in_chat")
    current_topic = None

    for msg in messages:
        if msg.get("type") != "message":
            continue

        # Пытаемся определить топик
        reply_to = msg.get("reply_to_message_id")
        if reply_to and reply_to in topics:
            current_topic = reply_to

        # Если топик определён - добавляем сообщение
        if current_topic and current_topic in topics:
            text = extract_text(msg.get("text", ""))
            media_info = get_media_info(msg)

            # Добавляем только если есть контент
            if text or media_info["has_media"]:
                topics[current_topic]["messages"].append({
                    "id": msg.get("id"),
                    "date": msg.get("date"),
                    "from": msg.get("from", "Unknown"),
                    "from_id": msg.get("from_id"),
                    "text": text,
                    "full_text": text,
                    **media_info
                })

    # === ШАГ 3: Группируем по категориям ===
    print("\n📁 Группирую по категориям...")

    categories = defaultdict(lambda: {"messages": [], "topics": []})

    for topic_id, topic_data in topics.items():
        category = topic_data["category"]
        if not category:
            continue

        categories[category]["topics"].append(topic_data["title"])

        # Добавляем подкатегорию к сообщениям
        for msg in topic_data["messages"]:
            msg["topic"] = topic_data["title"]
            msg["subcategory"] = topic_data["subcategory"]
            msg["categories"] = {
                category: [topic_data["subcategory"]] if topic_data["subcategory"] else []
            }
            categories[category]["messages"].append(msg)

    # Статистика
    print("\n📊 Статистика по категориям:")
    for cat_name, cat_data in categories.items():
        msg_count = len(cat_data["messages"])
        with_photo = sum(1 for m in cat_data["messages"] if m.get("has_photo"))
        with_video = sum(1 for m in cat_data["messages"] if m.get("has_video"))
        with_voice = sum(1 for m in cat_data["messages"] if m.get("has_voice"))
        with_circles = sum(1 for m in cat_data["messages"] if m.get("has_video_message"))
        print(f"   {cat_name}: {msg_count} сообщений | photo: {with_photo} | video: {with_video} | voice: {with_voice} | circles: {with_circles}")

    # === ШАГ 4: Сохраняем и копируем медиа ===
    print("\n💾 Сохраняю данные и копирую медиа...")

    stats = {
        "photos_copied": 0,
        "videos_copied": 0,
        "voices_copied": 0,
        "circles_copied": 0,
        "errors": 0
    }

    for cat_name, cat_data in categories.items():
        cat_dir = TESTIMONIALS_DIR / cat_name
        cat_dir.mkdir(parents=True, exist_ok=True)

        media_dir = cat_dir / "media"
        media_dir.mkdir(exist_ok=True)

        # Копируем медиафайлы
        for msg in cat_data["messages"]:
            new_files = []
            for file_info in msg.get("files", []):
                try:
                    new_path = copy_media_file(
                        file_info["path"],
                        media_dir,
                        msg["id"],
                        file_info["type"]
                    )
                    if new_path:
                        file_info["local_path"] = f"content/testimonials/{cat_name}/media/{new_path}"
                        new_files.append(file_info)

                        # Статистика
                        if file_info["type"] == "photo":
                            stats["photos_copied"] += 1
                        elif file_info["type"] == "video":
                            stats["videos_copied"] += 1
                        elif file_info["type"] == "voice":
                            stats["voices_copied"] += 1
                        elif file_info["type"] == "video_message":
                            stats["circles_copied"] += 1
                except Exception as e:
                    print(f"   ⚠️ Ошибка копирования {file_info['path']}: {e}")
                    stats["errors"] += 1

            msg["files"] = new_files

        # Сохраняем metadata.json
        metadata = {
            "category": cat_name,
            "topics": cat_data["topics"],
            "total_messages": len(cat_data["messages"]),
            "messages": cat_data["messages"]
        }

        metadata_path = cat_dir / "metadata.json"
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        print(f"   ✅ {cat_name}: сохранено {len(cat_data['messages'])} сообщений")

    # === ШАГ 5: Обновляем summary.json ===
    print("\n📋 Обновляю summary.json...")

    summary = {
        "source": "РАБОЧИЙ КАНАЛ NL",
        "export_date": data.get("messages", [{}])[0].get("date", ""),
        "import_date": str(Path(__file__).stat().st_mtime),
        "stats": {
            "total_messages": sum(len(c["messages"]) for c in categories.values()),
            "photos": stats["photos_copied"],
            "videos": stats["videos_copied"],
            "voices": stats["voices_copied"],
            "video_messages": stats["circles_copied"]
        },
        "categories": {}
    }

    for cat_name, cat_data in categories.items():
        summary["categories"][cat_name] = {
            "total": len(cat_data["messages"]),
            "topics": cat_data["topics"],
            "with_photo": sum(1 for m in cat_data["messages"] if m.get("has_photo")),
            "with_video": sum(1 for m in cat_data["messages"] if m.get("has_video")),
            "with_voice": sum(1 for m in cat_data["messages"] if m.get("has_voice")),
            "with_video_message": sum(1 for m in cat_data["messages"] if m.get("has_video_message"))
        }

    summary_path = TESTIMONIALS_DIR / "summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    # === ИТОГО ===
    print("\n" + "=" * 80)
    print("✅ ИМПОРТ ЗАВЕРШЁН!")
    print("=" * 80)
    print(f"\n📊 Скопировано медиафайлов:")
    print(f"   📸 Фото: {stats['photos_copied']}")
    print(f"   🎬 Видео: {stats['videos_copied']}")
    print(f"   🎤 Голосовые: {stats['voices_copied']}")
    print(f"   ⭕ Кружочки: {stats['circles_copied']}")
    if stats["errors"] > 0:
        print(f"   ⚠️ Ошибок: {stats['errors']}")

    print(f"\n📁 Данные сохранены в: {TESTIMONIALS_DIR}")
    print("\n💡 Теперь TestimonialsManager может использовать эти данные!")


if __name__ == "__main__":
    import_channel()
