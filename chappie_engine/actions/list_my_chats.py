"""Показать все группы, каналы и чаты аккаунта Чаппи."""

import json
import logging

from chappie_engine.client import PersonalAccountClient
from chappie_engine.state.state_manager import StateManager
from chappie_engine.safety import SafetyGuard

logger = logging.getLogger("chappie.list_my_chats")


async def run():
    """Получить список всех диалогов (групп, каналов, чатов).

    Сохраняет в CHAPPIE_KNOWLEDGE.json → my_chats.
    """
    sm = StateManager()
    sg = SafetyGuard(sm)

    banned, reason = sg.is_banned()
    if banned:
        print(f"Аварийный стоп: {reason}")
        return

    print("Получаю список чатов...")

    try:
        async with PersonalAccountClient() as pac:
            client = pac.client

            dialogs = await client.get_dialogs()

            groups = []
            channels = []
            users = []

            for dialog in dialogs:
                entity = dialog.entity
                entity_type = type(entity).__name__

                info = {
                    "id": dialog.id,
                    "name": dialog.name or "Без названия",
                    "unread": dialog.unread_count,
                }

                if hasattr(entity, "username") and entity.username:
                    info["username"] = f"@{entity.username}"

                if hasattr(entity, "participants_count"):
                    info["members"] = entity.participants_count

                if "Chat" in entity_type or "Channel" in entity_type:
                    is_channel = getattr(entity, "broadcast", False)
                    if is_channel:
                        info["type"] = "channel"
                        channels.append(info)
                    else:
                        info["type"] = "group"
                        groups.append(info)
                else:
                    info["type"] = "user"
                    users.append(info)

            # Вывод
            print(f"\n=== МОИ ГРУППЫ ({len(groups)}) ===")
            for g in groups:
                username = g.get("username", "")
                members = g.get("members", "?")
                unread = f" [{g['unread']} непрочитанных]" if g["unread"] else ""
                print(f"  {g['name']} {username} | {members} участников{unread}")

            print(f"\n=== МОИ КАНАЛЫ ({len(channels)}) ===")
            for c in channels:
                username = c.get("username", "")
                members = c.get("members", "?")
                unread = f" [{c['unread']} непрочитанных]" if c["unread"] else ""
                print(f"  {c['name']} {username} | {members} подписчиков{unread}")

            print(f"\n=== ЛИЧНЫЕ ЧАТЫ ({len(users)}) ===")
            for u in users[:10]:  # Первые 10
                username = u.get("username", "")
                unread = f" [{u['unread']} непрочитанных]" if u["unread"] else ""
                print(f"  {u['name']} {username}{unread}")
            if len(users) > 10:
                print(f"  ... и ещё {len(users) - 10}")

            # Сохранить в knowledge
            knowledge = sm.load_knowledge()
            knowledge["my_chats"] = {
                "groups": groups,
                "channels": channels,
                "users_count": len(users),
                "scanned_at": sm._today() if hasattr(sm, "_today") else None,
            }
            sm.save_knowledge(knowledge)

            sg.record_action("read", success=True)

            sm.update_status(
                f"Список чатов: {len(groups)} групп, {len(channels)} каналов, {len(users)} ЛС"
            )

            # JSON для AI
            print(f"\n--- JSON ---")
            print(json.dumps({
                "groups": groups,
                "channels": channels,
                "users_count": len(users),
            }, ensure_ascii=False, indent=2))

    except Exception as e:
        logger.error(f"Ошибка: {e}")
        sg.record_action("read", success=False)
        print(f"Ошибка: {e}")
