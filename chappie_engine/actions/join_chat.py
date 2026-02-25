"""Вступить в группу или канал Telegram."""

import logging
import re

from chappie_engine.client import PersonalAccountClient
from chappie_engine.state.state_manager import StateManager
from chappie_engine.safety import SafetyGuard

logger = logging.getLogger("chappie.join_chat")


async def run(invite: str):
    """Вступить в группу/канал по username или invite link.

    Args:
        invite: Username (без @) или invite link (https://t.me/+xxx или https://t.me/joinchat/xxx)
    """
    sm = StateManager()
    sg = SafetyGuard(sm)

    # Проверить лимиты (channel_join)
    can, reason = sg.can_perform("channel_join")
    if not can:
        print(f"Нельзя: {reason}")
        return

    invite = invite.strip().lstrip("@")

    # Определить тип: invite link или public username
    invite_hash = None
    # https://t.me/+HASH or https://t.me/joinchat/HASH
    m = re.match(r"(?:https?://)?t\.me/(?:\+|joinchat/)(.+)", invite)
    if m:
        invite_hash = m.group(1)

    print(f"Вступаю в {'приватный чат' if invite_hash else invite}...")

    try:
        async with PersonalAccountClient() as pac:
            client = pac.client

            if invite_hash:
                from telethon.tl.functions.messages import ImportChatInviteRequest
                result = await client(ImportChatInviteRequest(invite_hash))
                title = getattr(result.chats[0], 'title', 'Unknown') if result.chats else invite_hash
            else:
                from telethon.tl.functions.channels import JoinChannelRequest
                entity = await client.get_entity(invite)
                result = await client(JoinChannelRequest(entity))
                title = getattr(entity, 'title', invite)

            sg.record_action("channel_join", success=True)
            sm.update_status(f"Вступил в {title}")
            print(f"✅ Успешно вступил в: {title}")

    except Exception as e:
        logger.error(f"Ошибка при вступлении в {invite}: {e}")
        sg.record_action("channel_join", success=False)

        error_msg = str(e).lower()
        if "flood" in error_msg:
            match = re.search(r"(\d+)", str(e))
            if match:
                sg.handle_flood_wait(int(match.group(1)))
        elif "ban" in error_msg or "forbidden" in error_msg:
            sg.handle_ban_error(str(e))
        elif "invite" in error_msg and "expired" in error_msg:
            print(f"Invite link истёк или недействителен.")
        elif "already" in error_msg:
            print(f"Уже состою в этом чате/канале.")
        else:
            print(f"Ошибка: {e}")
