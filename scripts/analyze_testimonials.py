"""
Скрипт для анализа testimonials базы и качества классификации фото.

Находит:
- Фото без текста (сложно классифицировать)
- Распределение по подкатегориям
- Проблемные сообщения (без категории)
- Предлагает улучшения ключевых слов

Запуск:
    python scripts/analyze_testimonials.py
"""
import json
import os
import sys
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime

# Добавляем корень проекта в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

# Пути к данным
TESTIMONIALS_BASE = Path(__file__).parent.parent / "content" / "testimonials"
CATEGORIES = ["before_after", "checks", "products", "success_stories"]


def load_metadata(category: str) -> list:
    """Загрузить метаданные категории."""
    metadata_path = TESTIMONIALS_BASE / category / "metadata.json"
    if not metadata_path.exists():
        print(f"[WARNING] {metadata_path} not found")
        return []

    with open(metadata_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Метаданные могут быть dict с ключом 'messages' или просто списком
    if isinstance(data, dict):
        return data.get("messages", [])
    return data


def analyze_category(category: str, messages: list) -> dict:
    """Анализировать одну категорию."""
    stats = {
        "total": len(messages),
        "with_photo": 0,
        "with_video": 0,
        "with_voice": 0,
        "with_text": 0,
        "without_text": 0,
        "subcategories": Counter(),
        "no_subcategory": 0,
        "problems": [],
    }

    for msg in messages:
        # Медиа статистика
        if msg.get("has_photo"):
            stats["with_photo"] += 1
        if msg.get("has_video"):
            stats["with_video"] += 1
        if msg.get("has_voice"):
            stats["with_voice"] += 1

        # Текст
        text = msg.get("full_text") or msg.get("text") or ""
        if text.strip():
            stats["with_text"] += 1
        else:
            stats["without_text"] += 1
            # Фото без текста — потенциальная проблема
            if msg.get("has_photo"):
                stats["problems"].append({
                    "id": msg.get("id"),
                    "issue": "photo_without_text",
                    "topic": msg.get("topic"),
                    "subcategory": msg.get("subcategory"),
                })

        # Подкатегории
        subcategory = msg.get("subcategory")
        if subcategory:
            stats["subcategories"][subcategory] += 1
        else:
            stats["no_subcategory"] += 1
            if msg.get("has_photo"):
                stats["problems"].append({
                    "id": msg.get("id"),
                    "issue": "no_subcategory",
                    "topic": msg.get("topic"),
                    "text_preview": (text[:50] + "...") if len(text) > 50 else text,
                })

    return stats


def suggest_keyword_improvements(messages: list) -> dict:
    """Предложить улучшения ключевых слов на основе текстов."""
    # Собираем слова из сообщений без подкатегории
    uncategorized_words = Counter()

    for msg in messages:
        if not msg.get("subcategory"):
            text = (msg.get("full_text") or msg.get("text") or "").lower()
            # Простая токенизация
            words = text.replace(",", " ").replace(".", " ").replace("!", " ").split()
            for word in words:
                if len(word) > 3:  # Игнорируем короткие слова
                    uncategorized_words[word] += 1

    return dict(uncategorized_words.most_common(20))


def main():
    """Основная функция анализа."""
    # Фиксим кодировку для Windows
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')

    print(f"\n{'='*70}")
    print(f"[ANALYSIS] TESTIMONIALS DATABASE ANALYSIS")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Base path: {TESTIMONIALS_BASE}")
    print(f"{'='*70}\n")

    all_stats = {}
    total_messages = 0
    total_photos = 0
    total_no_text = 0
    total_problems = 0

    for category in CATEGORIES:
        print(f"\n{'-'*70}")
        print(f"[CATEGORY] {category.upper()}")
        print(f"{'-'*70}")

        messages = load_metadata(category)
        if not messages:
            print(f"  [SKIP] No data")
            continue

        stats = analyze_category(category, messages)
        all_stats[category] = stats

        total_messages += stats["total"]
        total_photos += stats["with_photo"]
        total_no_text += stats["without_text"]
        total_problems += len(stats["problems"])

        print(f"\n  [STATS]")
        print(f"  Total messages: {stats['total']}")
        print(f"  With photo: {stats['with_photo']}")
        print(f"  With video: {stats['with_video']}")
        print(f"  With voice: {stats['with_voice']}")
        print(f"  With text: {stats['with_text']} ({stats['with_text']/stats['total']*100:.1f}%)")
        print(f"  Without text: {stats['without_text']} ({stats['without_text']/stats['total']*100:.1f}%)")
        print(f"  No subcategory: {stats['no_subcategory']}")

        if stats["subcategories"]:
            print(f"\n  [SUBCATEGORIES]")
            for subcat, count in stats["subcategories"].most_common(10):
                pct = count / stats["total"] * 100
                print(f"    {subcat}: {count} ({pct:.1f}%)")

        # Показываем проблемные сообщения (только первые 5)
        if stats["problems"]:
            print(f"\n  [PROBLEMS] ({len(stats['problems'])} total)")
            for problem in stats["problems"][:5]:
                print(f"    - ID {problem['id']}: {problem['issue']}")
                if problem.get("topic"):
                    print(f"      Topic: {problem['topic']}")

    # Итоговая статистика
    print(f"\n{'='*70}")
    print(f"[SUMMARY]")
    print(f"{'='*70}")
    print(f"\nTotal messages: {total_messages}")
    print(f"Total with photo: {total_photos}")
    print(f"Total without text: {total_no_text} ({total_no_text/total_messages*100:.1f}%)")
    print(f"Total problems: {total_problems}")

    # Предложения по улучшению
    if "before_after" in all_stats:
        print(f"\n{'='*70}")
        print(f"[SUGGESTIONS] Keyword improvements for before_after")
        print(f"{'='*70}")

        messages = load_metadata("before_after")
        suggestions = suggest_keyword_improvements(messages)

        if suggestions:
            print("\nTop words in uncategorized messages:")
            for word, count in suggestions.items():
                print(f"  {word}: {count}")
        else:
            print("\n[OK] All messages have subcategories!")

    # Качество классификации
    print(f"\n{'='*70}")
    print(f"[QUALITY ASSESSMENT]")
    print(f"{'='*70}")

    if total_photos > 0:
        photos_with_issues = sum(
            1 for cat_stats in all_stats.values()
            for p in cat_stats.get("problems", [])
            if p.get("issue") == "photo_without_text"
        )
        quality_score = (total_photos - photos_with_issues) / total_photos * 100
        print(f"\nPhoto classification quality: {quality_score:.1f}%")
        print(f"Photos with text: {total_photos - photos_with_issues}")
        print(f"Photos without text: {photos_with_issues}")

        if photos_with_issues > 100:
            print("\n[WARNING] Many photos without text description.")
            print("These rely on topic-based classification only.")
            print("Consider using Vision AI for better accuracy.")

    return all_stats


if __name__ == "__main__":
    main()
