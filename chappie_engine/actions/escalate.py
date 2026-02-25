"""Эскалация проблем — отправить задачу Кодеру или запрос Альтрону."""

import logging

from chappie_engine.state.state_manager import StateManager

logger = logging.getLogger("chappie.escalate")


async def run(
    escalation_type: str,
    description: str,
    why_needed: str = "",
    research: str = "",
    priority: str = "medium",
):
    """Эскалировать проблему.

    Args:
        escalation_type: 'feature_request' (Кодеру) или 'permission' (Альтрону/Данилу)
        description: Описание проблемы
        why_needed: Зачем это нужно
        research: Что уже исследовал (API, документация)
        priority: 'low', 'medium', 'high'
    """
    sm = StateManager()

    if escalation_type not in ("feature_request", "permission", "bug", "question"):
        print(f"Неизвестный тип эскалации: {escalation_type}")
        print("Доступные: feature_request, permission, bug, question")
        return

    # Записать в журнал проблем
    problem_id = sm.add_problem(description, why_needed, research)

    # Обновить статус проблемы
    problems = sm.load_problems()
    for p in problems["problems"]:
        if p["id"] == problem_id:
            p["status"] = f"escalated_to_{'coder' if escalation_type == 'feature_request' else 'altron'}"
            p["escalated_at"] = problems.get("problems", [{}])[-1].get("discovered_at", "")
            break
    sm.save_problems(problems)

    # Отправить в INBOX
    if escalation_type == "feature_request":
        header = "ЧАППИ -> КОДЕР"
        content = (
            f"**Запрос на фичу** (приоритет: {priority})\n\n"
            f"**Что:** {description}\n"
            f"**Зачем:** {why_needed}\n"
        )
        if research:
            content += f"**Исследование:** {research}\n"
        content += f"\n**Проблема #{problem_id}** в CHAPPIE_PROBLEMS.json"

    elif escalation_type == "permission":
        header = "ЧАППИ -> АЛЬТРОН"
        content = (
            f"**Запрос разрешения** (приоритет: {priority})\n\n"
            f"**Что хочу сделать:** {description}\n"
            f"**Зачем:** {why_needed}\n"
            f"\nЖду одобрения от Данила."
        )

    elif escalation_type == "bug":
        header = "ЧАППИ -> КОДЕР"
        content = (
            f"**Баг** (приоритет: {priority})\n\n"
            f"**Описание:** {description}\n"
            f"**Что ожидалось:** {why_needed}\n"
        )
        if research:
            content += f"**Детали:** {research}\n"

    else:  # question
        header = "ЧАППИ -> АЛЬТРОН"
        content = (
            f"**Вопрос**\n\n"
            f"{description}\n"
        )
        if why_needed:
            content += f"\nКонтекст: {why_needed}\n"

    sm.write_to_inbox(header, content)

    print(f"Эскалация #{problem_id} отправлена!")
    print(f"Тип: {escalation_type}")
    print(f"Кому: {'Кодеру' if 'КОДЕР' in header else 'Альтрону'}")
    print(f"Описание: {description}")
    if why_needed:
        print(f"Зачем: {why_needed}")
    if research:
        print(f"Исследование: {research}")

    # Обновить STATUS
    sm.update_status(f"Эскалация #{problem_id}: {description[:50]}...")
