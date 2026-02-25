"""Показать текущий статус ПРОДЮСЕРА."""

from infobiz_engine.state.state_manager import StateManager
from infobiz_engine.config import LIMITS, CONTENT_DIR


async def run():
    """Вывести полный статус: пайплайн, ниши, продукты, лимиты."""
    sm = StateManager()

    state = sm.load_state()
    niches = sm.load_niches()
    products = sm.load_products()
    pipeline = sm.load_pipeline()

    print("=" * 55)
    print("ПРОДЮСЕР — Статус инфобизнес-фабрики")
    print("=" * 55)

    # Пайплайн
    print(f"\n--- ПАЙПЛАЙН ---")
    print(f"Текущий этап: {pipeline.get('current_stage', 'research')}")
    print(f"Циклов выполнено: {pipeline.get('cycle_count', 0)}")
    for stage_name, stage_data in pipeline.get("stages", {}).items():
        status = stage_data.get("status", "pending")
        icon = "▶" if status == "active" else ("✅" if status == "done" else "⏸")
        metrics = {k: v for k, v in stage_data.items() if k != "status"}
        metrics_str = ", ".join(f"{k}={v}" for k, v in metrics.items()) if metrics else ""
        print(f"  {icon} {stage_name}: {status} {metrics_str}")

    # Ниши
    print(f"\n--- НИШИ ---")
    researched = niches.get("researched_niches", [])
    qualified = [n for n in researched if n.get("score", 0) >= LIMITS["min_niche_score"]]
    print(f"Исследовано: {len(researched)}")
    print(f"Квалифицировано (score≥{LIMITS['min_niche_score']}): {len(qualified)}")
    for n in qualified[:5]:
        print(f"  [{n.get('score', 0)}] {n.get('name', '?')} ({n.get('slug', '?')})")

    # Продукты
    print(f"\n--- ПРОДУКТЫ ---")
    product_list = products.get("products", [])
    if product_list:
        for p in product_list:
            status = p.get("status", "draft")
            revenue = p.get("revenue_rub", 0)
            sales = p.get("sales_count", 0)
            print(f"  {p.get('id', '?')} | {status} | {p.get('title', '?')}")
            if sales > 0:
                print(f"    Продажи: {sales}, Выручка: {revenue}₽")
    else:
        print("  Продуктов пока нет")

    # Контент на диске
    if CONTENT_DIR.exists():
        course_dirs = [d for d in CONTENT_DIR.iterdir() if d.is_dir()]
        if course_dirs:
            print(f"\n--- КОНТЕНТ НА ДИСКЕ ---")
            for d in course_dirs:
                md_files = list(d.rglob("*.md"))
                print(f"  {d.name}/: {len(md_files)} уроков (.md)")

    # Выручка
    print(f"\n--- ВЫРУЧКА ---")
    print(f"Всего RUB: {state.get('revenue_total_rub', 0)}₽")
    print(f"Всего USD: ${state.get('revenue_total_usd', 0)}")

    # Лимиты на сегодня
    print(f"\n--- ЛИМИТЫ СЕГОДНЯ ---")
    for limit_name, limit_val in LIMITS.items():
        if limit_name.startswith("max_"):
            action = limit_name.replace("max_", "").replace("_per_day", "")
            used = sm.get_daily_count(action)
            if limit_name.endswith("_per_day"):
                print(f"  {action}: {used}/{limit_val}")

    # Ошибки
    if state.get("errors_today", 0) > 0:
        print(f"\n--- ОШИБКИ ---")
        print(f"Сегодня: {state['errors_today']}")
        if state.get("last_error"):
            print(f"Последняя: {state['last_error']}")

    # Доступные действия
    print(f"\n--- ДОСТУПНЫЕ ДЕЙСТВИЯ ---")
    actions = [
        ("research_niche [query]", "Найти и оценить ниши"),
        ("analyze_competitors <slug>", "Анализ конкурентов в нише"),
        ("create_course <slug>", "Сгенерировать курс"),
        ("build_landing <id>", "Создать лендинг"),
        ("deploy_site <id>", "Задеплоить на VPS"),
        ("setup_payment <id> <price>", "Настроить оплату"),
        ("check_sales", "Проверить продажи"),
        ("publish_promo <id>", "Создать промо"),
        ("escalate <type> <desc>", "Эскалировать проблему"),
    ]
    for cmd, desc in actions:
        print(f"  {cmd} — {desc}")

    print("\n" + "=" * 55)
