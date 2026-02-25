"""Эскалация проблем — отправить задачу Кодеру или запрос Альтрону."""

import logging

from infobiz_engine.state.state_manager import StateManager

logger = logging.getLogger("producer.escalate")

VALID_TYPES = ("feature_request", "permission", "bug", "question")


async def run(
    escalation_type: str,
    description: str,
    why_needed: str = "",
    priority: str = "medium",
):
    """Эскалировать проблему другим агентам через INBOX.

    Args:
        escalation_type: 'feature_request' (Кодеру), 'permission' (Альтрону),
                        'bug' (Кодеру), 'question' (Альтрону)
        description: Описание проблемы
        why_needed: Зачем это нужно
        priority: 'low', 'medium', 'high'
    """
    sm = StateManager()

    if escalation_type not in VALID_TYPES:
        print(f"Неизвестный тип эскалации: {escalation_type}")
        print(f"Доступные: {', '.join(VALID_TYPES)}")
        return

    target = "КОДЕР" if escalation_type in ("feature_request", "bug") else "АЛЬТРОН"
    header = f"ПРОДЮСЕР -> {target}"

    if escalation_type == "feature_request":
        content = (
            f"**Запрос на фичу** (приоритет: {priority})\n\n"
            f"**Что:** {description}\n"
        )
        if why_needed:
            content += f"**Зачем:** {why_needed}\n"

    elif escalation_type == "bug":
        content = (
            f"**Баг** (приоритет: {priority})\n\n"
            f"**Описание:** {description}\n"
        )
        if why_needed:
            content += f"**Что ожидалось:** {why_needed}\n"

    elif escalation_type == "permission":
        content = (
            f"**Запрос разрешения** (приоритет: {priority})\n\n"
            f"**Что хочу сделать:** {description}\n"
        )
        if why_needed:
            content += f"**Зачем:** {why_needed}\n"
        content += "\nЖду одобрения от Данила."

    else:  # question
        content = f"**Вопрос**\n\n{description}\n"
        if why_needed:
            content += f"\nКонтекст: {why_needed}\n"

    sm.write_to_inbox(header, content)
    sm.record_action("escalate")

    print(f"Эскалация отправлена!")
    print(f"Тип: {escalation_type}")
    print(f"Кому: {target}")
    print(f"Описание: {description}")

    sm.update_status(f"Эскалация -> {target}: {description[:50]}...")
