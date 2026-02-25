"""Показать текущий статус Чаппи."""

import json
from chappie_engine.state.state_manager import StateManager
from chappie_engine.safety import SafetyGuard


async def run():
    """Вывести полный статус: состояние, лимиты, знания, цели, проблемы."""
    sm = StateManager()
    sg = SafetyGuard(sm)

    state = sm.load_state()
    knowledge = sm.load_knowledge()
    goals = sm.load_goals()
    problems = sm.load_problems()

    print("=" * 50)
    print("ЧАППИ — Статус")
    print("=" * 50)

    # Безопасность
    print("\n--- БЕЗОПАСНОСТЬ ---")
    print(sg.get_status_report())

    # Состояние
    print(f"\n--- СОСТОЯНИЕ ---")
    print(f"Фаза: {state.get('phase', 'unknown')}")
    print(f"Начало работы: {state.get('started_at', 'не указано')}")
    print(f"Каналы: {json.dumps(state.get('channels', {}), ensure_ascii=False)}")

    # Итого действий
    total = state.get("total_actions", {})
    if total:
        print(f"\n--- ВСЕГО ДЕЙСТВИЙ ---")
        for key, val in total.items():
            print(f"  {key}: {val}")

    # Знания
    print(f"\n--- ЗНАНИЯ ---")
    products = knowledge.get("products_studied", [])
    print(f"Продуктов изучено: {len(products)}")
    if products:
        for p in products[:5]:
            print(f"  - {p}")
        if len(products) > 5:
            print(f"  ... и ещё {len(products) - 5}")
    print(f"Бизнес-модель: {'Да' if knowledge.get('business_model_understood') else 'Нет'}")
    print(f"Квалификации: {'Да' if knowledge.get('qualifications_understood') else 'Нет'}")
    insights = knowledge.get("competitor_insights", [])
    print(f"Инсайтов от конкурентов: {len(insights)}")

    # Цели
    print(f"\n--- ЦЕЛИ ---")
    print(f"Текущая цель: {goals.get('current_goal', 'нет')}")
    print(f"Целевая квалификация: {goals.get('qualification_target', 'нет')}")
    milestones = goals.get("milestones", [])
    for m in milestones:
        status = "done" if m.get("done") else "pending"
        print(f"  [{'x' if m.get('done') else ' '}] {m['name']}")

    # Проблемы
    open_problems = [p for p in problems.get("problems", []) if not p.get("resolved")]
    if open_problems:
        print(f"\n--- ПРОБЛЕМЫ ({len(open_problems)} открытых) ---")
        for p in open_problems:
            print(f"  #{p['id']} [{p.get('status', 'new')}] {p['description']}")

    # Доступные действия
    print(f"\n--- ДОСТУПНЫЕ ДЕЙСТВИЯ ---")
    actions = [
        ("study_products", "Изучить продукты NL из базы знаний"),
        ("read_channel <username>", "Прочитать и проанализировать канал"),
        ("get_status", "Показать этот статус"),
        ("escalate", "Сообщить о проблеме Кодеру/Альтрону"),
    ]
    for cmd, desc in actions:
        can, reason = sg.can_perform("read")  # read for study/read actions
        print(f"  {cmd} — {desc}")

    print("\n" + "=" * 50)
