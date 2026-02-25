"""CLI точка входа для Chappie Engine.

Использование:
    python -m chappie_engine.run <action> [args]

Действия:
    get_status                      — Показать текущий статус
    study_products [category]       — Изучить продукты (products/business/faq/stories/all)
    read_channel <username> [limit] — Прочитать канал (макс 20 постов)
    read_group <identifier> [limit] — Прочитать группу/чат (username или ID, макс 20 сообщений)
    interact_bot <username> [--message ...] [--limit ...] [--wait ...] — Взаимодействовать с ботом
    create_channel --title ... --about ... [--username ...] — Создать Telegram канал
    join_chat <invite_link_or_username>  — Вступить в группу/канал (макс 3/день)
    download_media <identifier> [limit] [--types photo,voice,document] [--transcribe] — Скачать медиа + транскрипция
    escalate <type> <description>   — Эскалировать проблему (feature_request/permission/bug/question)
    send_report <message>           — Отправить отчёт Данилу в личку Telegram
    read_messages [limit]           — Прочитать последние сообщения от Данила (по умолчанию 10)
    update_profile [--name ...] [--last_name ...] [--bio ...] [--username ...] [--photo ...] — Обновить профиль
    list_my_chats                       — Показать все мои группы, каналы и чаты
    post_to_channel --channel ... --text ... [--photo ...] — Опубликовать пост в канал
    publish_media <target> <media_path> [--type ...] — Опубликовать медиа (голосовое, кружок, фото)
"""

import asyncio
import io
import sys

# Fix: platform/ directory in project shadows stdlib platform module.
# Remove project dir from sys.path BEFORE importing telethon/aiohttp.
_project_dir = str(__import__("pathlib").Path(__file__).parent.parent)
sys.path = [p for p in sys.path if p != _project_dir]
# Re-add it AFTER stdlib paths so stdlib platform takes priority
sys.path.append(_project_dir)

# Windows encoding fix
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)


def main():
    args = sys.argv[1:]

    if not args:
        print(__doc__)
        return

    action = args[0]

    if action == "get_status":
        from chappie_engine.actions.get_status import run
        asyncio.run(run())

    elif action == "study_products":
        category = args[1] if len(args) > 1 else "all"
        from chappie_engine.actions.study_products import run
        asyncio.run(run(category=category))

    elif action == "read_channel":
        if len(args) < 2:
            print("Использование: read_channel <username> [limit]")
            print("Пример: read_channel siberianhealth_official 10")
            return
        username = args[1]
        limit = int(args[2]) if len(args) > 2 else 10
        from chappie_engine.actions.read_channel import run
        asyncio.run(run(channel_username=username, limit=limit))

    elif action == "read_group":
        if len(args) < 2:
            print("Использование: read_group <identifier> [limit]")
            print("Пример: read_group mygroupchat 10")
            print("Пример: read_group -100123456789 10 (для ID группы)")
            return
        identifier = args[1]
        limit = int(args[2]) if len(args) > 2 else 10
        from chappie_engine.actions.read_group import run
        asyncio.run(run(group_identifier=identifier, limit=limit))

    elif action == "interact_bot":
        if len(args) < 2:
            print("Использование: interact_bot <username> [--message ...] [--limit ...] [--wait ...]")
            print("Пример: interact_bot nl_assistant_bot --message 'Привет' --limit 5 --wait 3")
            return
        
        bot_username = args[1]
        message = None
        limit = 5
        wait_seconds = 3
        
        i = 2
        while i < len(args):
            if args[i] == "--message" and i + 1 < len(args):
                message = args[i + 1]
                i += 2
            elif args[i] == "--limit" and i + 1 < len(args):
                limit = int(args[i + 1])
                i += 2
            elif args[i] == "--wait" and i + 1 < len(args):
                wait_seconds = int(args[i + 1])
                i += 2
            else:
                i += 1
        
        from chappie_engine.actions.interact_bot import run
        asyncio.run(run(bot_username=bot_username, message=message, limit=limit, wait_seconds=wait_seconds))

    elif action == "create_channel":
        # Парсинг аргументов
        title = about = username = ""
        i = 1
        while i < len(args):
            if args[i] == "--title" and i + 1 < len(args):
                title = args[i + 1]
                i += 2
            elif args[i] == "--about" and i + 1 < len(args):
                about = args[i + 1]
                i += 2
            elif args[i] == "--username" and i + 1 < len(args):
                username = args[i + 1]
                i += 2
            else:
                i += 1
        from chappie_engine.actions.create_channel import run
        asyncio.run(run(title=title, about=about, username=username))

    elif action == "join_chat":
        if len(args) < 2:
            print("Использование: join_chat <invite_link_or_username>")
            print("Пример: join_chat nl_community")
            print("Пример: join_chat https://t.me/+AbCdEfGhIjK")
            return
        invite = args[1]
        from chappie_engine.actions.join_chat import run
        asyncio.run(run(invite=invite))

    elif action == "download_media":
        if len(args) < 2:
            print("Использование: download_media <identifier> [limit] [--types photo,voice,document] [--transcribe]")
            print("Пример: download_media nl_community 10 --types photo,voice --transcribe")
            return
        identifier = args[1]
        limit = 10
        media_types = "photo,voice"
        transcribe = False
        i = 2
        while i < len(args):
            if args[i] == "--types" and i + 1 < len(args):
                media_types = args[i + 1]
                i += 2
            elif args[i] == "--transcribe":
                transcribe = True
                i += 1
            else:
                try:
                    limit = int(args[i])
                except ValueError:
                    pass
                i += 1
        from chappie_engine.actions.download_media import run
        asyncio.run(run(group_identifier=identifier, limit=limit, media_types=media_types, transcribe=transcribe))

    elif action == "escalate":
        if len(args) < 3:
            print("Использование: escalate <type> <description> [--why ...] [--research ...] [--priority ...]")
            print("Типы: feature_request, permission, bug, question")
            print('Пример: escalate feature_request "Нужны видео-кружки" --why "Конкуренты используют"')
            return

        esc_type = args[1]
        description = args[2]

        # Парсинг опциональных аргументов
        why = ""
        research = ""
        priority = "medium"
        i = 3
        while i < len(args):
            if args[i] == "--why" and i + 1 < len(args):
                why = args[i + 1]
                i += 2
            elif args[i] == "--research" and i + 1 < len(args):
                research = args[i + 1]
                i += 2
            elif args[i] == "--priority" and i + 1 < len(args):
                priority = args[i + 1]
                i += 2
            else:
                i += 1

        from chappie_engine.actions.escalate import run
        asyncio.run(run(
            escalation_type=esc_type,
            description=description,
            why_needed=why,
            research=research,
            priority=priority,
        ))

    elif action == "send_report":
        if len(args) < 2:
            print("Использование: send_report <message>")
            print('Пример: send_report "Изучил 5 каналов конкурентов, нашёл интересные паттерны"')
            return
        message = args[1]
        from chappie_engine.actions.send_report import run
        asyncio.run(run(message=message))

    elif action == "read_messages":
        limit = int(args[1]) if len(args) > 1 else 10
        from chappie_engine.actions.read_messages import run
        asyncio.run(run(limit=limit))

    elif action == "list_my_chats":
        from chappie_engine.actions.list_my_chats import run
        asyncio.run(run())

    elif action == "post_to_channel":
        # Парсинг аргументов
        channel = text = photo = ""
        i = 1
        while i < len(args):
            if args[i] == "--channel" and i + 1 < len(args):
                channel = args[i + 1]
                i += 2
            elif args[i] == "--text" and i + 1 < len(args):
                text = args[i + 1]
                i += 2
            elif args[i] == "--photo" and i + 1 < len(args):
                photo = args[i + 1]
                i += 2
            else:
                i += 1
        if not channel:
            print("Использование: post_to_channel --channel <username> --text <текст> [--photo <путь>]")
            return
        from chappie_engine.actions.post_to_channel import run
        asyncio.run(run(channel_username=channel, text=text, photo_path=photo))

    elif action == "publish_media":
        if len(args) < 3:
            print("Использование: publish_media <target> <media_path> [--type voice|video_note|photo|video]")
            return
        target = args[1]
        media_path = args[2]
        media_type = "auto"
        i = 3
        while i < len(args):
            if args[i] == "--type" and i + 1 < len(args):
                media_type = args[i + 1]
                i += 2
            else:
                i += 1
        from chappie_engine.actions.publish_media import run
        asyncio.run(run(target=target, media_path=media_path, media_type=media_type))

    elif action == "update_profile":
        # Парсинг аргументов
        name = last_name = bio = username = photo = ""
        i = 1
        while i < len(args):
            if args[i] == "--name" and i + 1 < len(args):
                name = args[i + 1]
                i += 2
            elif args[i] == "--last_name" and i + 1 < len(args):
                last_name = args[i + 1]
                i += 2
            elif args[i] == "--bio" and i + 1 < len(args):
                bio = args[i + 1]
                i += 2
            elif args[i] == "--username" and i + 1 < len(args):
                username = args[i + 1]
                i += 2
            elif args[i] == "--photo" and i + 1 < len(args):
                photo = args[i + 1]
                i += 2
            else:
                i += 1
        from chappie_engine.actions.update_profile import run
        asyncio.run(run(first_name=name, last_name=last_name, bio=bio, username=username, photo=photo))

    else:
        print(f"Неизвестное действие: {action}")
        print(__doc__)


if __name__ == "__main__":
    main()
