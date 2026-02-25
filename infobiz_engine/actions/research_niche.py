"""Исследование ниш для инфопродуктов."""

import logging
from datetime import datetime, timezone, timedelta

from infobiz_engine.state.state_manager import StateManager
from infobiz_engine.ai.niche_researcher import research_niches
from infobiz_engine.config import LIMITS, UTC_OFFSET

logger = logging.getLogger("producer.research")

MSK = timezone(timedelta(hours=UTC_OFFSET))


async def run(query: str = ""):
    """Найти и оценить ниши для инфопродуктов.

    Args:
        query: Конкретная тема (или пустая строка для автоматического поиска)
    """
    sm = StateManager()

    # Проверить лимит
    today_count = sm.get_daily_count("research_niche")
    if today_count >= LIMITS["max_niches_per_day"]:
        print(f"Лимит на сегодня исчерпан: {today_count}/{LIMITS['max_niches_per_day']} исследований")
        return

    print(f"Исследую ниши{f' по запросу: {query}' if query else ' (автопоиск)'}...")
    print()

    try:
        niches = await research_niches(query=query, count=5)
    except Exception as e:
        print(f"Ошибка AI: {e}")
        state = sm.load_state()
        state["errors_today"] = state.get("errors_today", 0) + 1
        state["last_error"] = str(e)[:200]
        sm.save_state(state)
        return

    if not niches:
        print("AI не вернул ниш. Попробуй другой запрос.")
        return

    # Сохранить результаты
    now = datetime.now(MSK).strftime("%Y-%m-%d")
    qualified_count = 0

    for niche in niches:
        niche["researched_at"] = now
        niche["status"] = "qualified" if niche.get("score", 0) >= LIMITS["min_niche_score"] else "weak"
        sm.add_niche(niche)

        score = niche.get("score", 0)
        icon = "✅" if score >= LIMITS["min_niche_score"] else "⚪"

        if score >= LIMITS["min_niche_score"]:
            qualified_count += 1

        print(f"{icon} [{score}] {niche.get('name', '?')}")
        print(f"   slug: {niche.get('slug', '?')}")
        print(f"   ЦА: {niche.get('target_audience', '?')}")
        print(f"   Цена: {niche.get('price_range_rub', '?')}₽")
        if niche.get("demand_signals"):
            print(f"   Сигналы: {', '.join(niche['demand_signals'][:3])}")
        if niche.get("risks"):
            print(f"   Риски: {', '.join(niche['risks'][:2])}")
        print()

    # Обновить счётчики
    sm.record_action("research_niche")

    # Обновить пайплайн
    all_niches = sm.load_niches()
    total_researched = len(all_niches.get("researched_niches", []))
    total_qualified = len(sm.get_qualified_niches())
    sm.update_pipeline_stage("research", {
        "status": "active",
        "niches_found": total_researched,
        "niches_qualified": total_qualified,
    })

    print(f"Итого: {len(niches)} ниш, {qualified_count} квалифицировано (score≥{LIMITS['min_niche_score']})")
    print(f"Всего в базе: {total_researched} ниш, {total_qualified} квалифицировано")

    sm.update_status(f"Исследование ниш: +{len(niches)}, квалифицировано {qualified_count}")
