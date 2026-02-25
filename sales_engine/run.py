"""
Главный скрипт Sales Engine — запускается по cron от агента Чаппи.

Выполняет:
1. Генерирует контент-план (4 поста для 4 сегментов)
2. Генерирует 1 пост-ответ на возражение
3. Записывает всё в INBOX для Альтрона
4. Обновляет STATUS
"""

import asyncio
import random
import sys
import io
from datetime import datetime
from pathlib import Path

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from .content_planner import generate_post
from .objection_handler import generate_objection_post, OBJECTIONS_DB
from .config import SEGMENTS, SEGMENT_NAMES, CONTENT_TYPES, INBOX_PATH, STATUS_PATH, NL_CONTENT_PATH


def update_status(task: str):
    """Обновляет STATUS.md."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    content = STATUS_PATH.read_text(encoding="utf-8")

    # Обновляем строку ЧАППИ
    lines = content.split("\n")
    updated = False
    for i, line in enumerate(lines):
        if "ЧАППИ" in line:
            lines[i] = f"| ЧАППИ | 🟢 active | {now} | {task} |"
            updated = True
            break

    if not updated:
        # Добавляем строку
        for i, line in enumerate(lines):
            if "СКАНЕР" in line:
                lines.insert(i + 1, f"| ЧАППИ | 🟢 active | {now} | {task} |")
                updated = True
                break

    if updated:
        STATUS_PATH.write_text("\n".join(lines), encoding="utf-8")


def write_to_inbox(content: str):
    """Добавляет сообщение в INBOX."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    header = f"\n\n## [{now}] ЧАППИ → АЛЬТРОН\n"
    current = INBOX_PATH.read_text(encoding="utf-8")
    INBOX_PATH.write_text(current + header + content + "\n", encoding="utf-8")


def save_content(posts: list[dict]):
    """Сохраняет контент в NL_CONTENT.md."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    content = f"\n\n---\n\n## Контент-план ({now})\n\n"
    for post in posts:
        content += f"### {SEGMENT_NAMES.get(post['segment'], post['segment'])}"
        if post.get("product"):
            content += f" — {post['product']}"
        content += f" [{post['type']}]\n\n"
        content += f"{post['text']}\n\n"

    # Append to file
    if NL_CONTENT_PATH.exists():
        current = NL_CONTENT_PATH.read_text(encoding="utf-8")
    else:
        current = "# NL Content — Готовый контент от Чаппи\n"
    NL_CONTENT_PATH.write_text(current + content, encoding="utf-8")


async def run_cycle():
    """Основной цикл работы."""
    print(f"[{datetime.now()}] Sales Engine — начинаю цикл")

    # 1. Генерируем по 1 посту для 2 случайных сегментов (чтобы не спамить)
    selected_segments = random.sample(SEGMENTS, 2)
    posts = []

    for segment in selected_segments:
        content_type = random.choice(CONTENT_TYPES)
        print(f"  Генерирую {content_type} для {segment}...")
        post = await generate_post(segment=segment, content_type=content_type)
        posts.append(post)
        print(f"  ✅ {segment}: {len(post['text'])} символов")

    # 2. Генерируем 1 ответ на случайное возражение
    objection_key = random.choice(list(OBJECTIONS_DB.keys()))
    objection_segment = random.choice(["business", "student"])
    print(f"  Генерирую ответ на возражение '{objection_key}' для {objection_segment}...")
    objection_post = await generate_objection_post(objection_key, objection_segment)
    print(f"  ✅ Возражение: {len(objection_post)} символов")

    # 3. Сохраняем контент
    save_content(posts)

    # 4. Записываем в INBOX
    inbox_text = f"**Контент-план готов** ({len(posts)} постов + 1 ответ на возражение)\n\n"

    for post in posts:
        seg_name = SEGMENT_NAMES.get(post["segment"], post["segment"])
        inbox_text += f"### {seg_name} [{post['type']}]\n"
        inbox_text += f"{post['text'][:300]}{'...' if len(post['text']) > 300 else ''}\n\n"

    inbox_text += f"### Ответ на возражение: «{objection_key.replace('_', ' ')}»\n"
    inbox_text += f"{objection_post[:300]}{'...' if len(objection_post) > 300 else ''}\n\n"
    inbox_text += f"📝 Полный контент: `~/.plamya/shared/NL_CONTENT.md`\n"

    write_to_inbox(inbox_text)

    # 5. Обновляем статус
    update_status(f"Сгенерировано {len(posts)} постов + ответ на '{objection_key}'")

    print(f"\n[{datetime.now()}] Sales Engine — цикл завершён")
    print(f"  Постов: {len(posts)}")
    print(f"  Возражение: {objection_key}")
    print(f"  INBOX обновлён ✅")
    print(f"  STATUS обновлён ✅")


def main():
    asyncio.run(run_cycle())


if __name__ == "__main__":
    main()
