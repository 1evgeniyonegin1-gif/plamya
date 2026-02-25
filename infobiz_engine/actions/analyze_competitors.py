"""Анализ конкурентов в нише."""

import json
import logging

from infobiz_engine.state.state_manager import StateManager
from infobiz_engine.ai.competitor_analyzer import analyze_competitors
from infobiz_engine.config import LIMITS

logger = logging.getLogger("producer.competitors")


async def run(niche_slug: str):
    """Проанализировать конкурентов в конкретной нише.

    Args:
        niche_slug: Slug ниши из PRODUCER_NICHES.json
    """
    sm = StateManager()

    # Найти нишу
    niche = sm.get_niche_by_slug(niche_slug)
    if not niche:
        print(f"Ниша не найдена: {niche_slug}")
        qualified = sm.get_qualified_niches()
        if qualified:
            print("Доступные ниши:")
            for n in qualified:
                print(f"  [{n.get('score', 0)}] {n.get('slug', '?')} — {n.get('name', '?')}")
        else:
            print("Сначала выполни research_niche для поиска ниш.")
        return

    niche_name = niche.get("name", niche_slug)
    print(f"Анализирую конкурентов в нише: {niche_name}...")
    print()

    try:
        analysis = await analyze_competitors(niche_name=niche_name, niche_slug=niche_slug)
    except Exception as e:
        print(f"Ошибка AI: {e}")
        return

    if not analysis:
        print("AI не вернул анализ. Попробуй ещё раз.")
        return
    
    # Проверяем наличие ошибки в ответе
    if analysis.get("error"):
        print(f"Ошибка при анализе конкурентов: {analysis.get('error')}")
        print("Возвращаю пустой анализ для продолжения работы.")
        # Продолжаем с пустым анализом, чтобы не блокировать пайплайн

    # Показать результаты
    competitors = analysis.get("competitors", [])
    if competitors:
        print(f"--- КОНКУРЕНТЫ ({len(competitors)}) ---")
        for c in competitors:
            price = c.get("price_rub", "?")
            rating = c.get("rating", "?")
            print(f"  {c.get('name', '?')} ({c.get('platform', '?')})")
            print(f"    Цена: {price}₽, Рейтинг: {rating}, Студенты: {c.get('students_estimate', '?')}")
            if c.get("strengths"):
                print(f"    +: {', '.join(c['strengths'][:3])}")
            if c.get("weaknesses"):
                print(f"    -: {', '.join(c['weaknesses'][:3])}")
            print()

    gaps = analysis.get("market_gaps", [])
    if gaps:
        print(f"--- ПРОБЕЛЫ НА РЫНКЕ ---")
        for g in gaps:
            print(f"  • {g}")
        print()

    positioning = analysis.get("recommended_positioning", "")
    if positioning:
        print(f"--- РЕКОМЕНДОВАННОЕ ПОЗИЦИОНИРОВАНИЕ ---")
        print(f"  {positioning}")
        print()

    rec_price = analysis.get("recommended_price_rub", 0)
    if rec_price:
        print(f"Рекомендованная цена: {rec_price}₽")

    usps = analysis.get("unique_selling_points", [])
    if usps:
        print(f"\n--- УТП ---")
        for u in usps:
            print(f"  • {u}")

    # Сохранить анализ в нише
    niches_data = sm.load_niches()
    for n in niches_data["researched_niches"]:
        if n.get("slug") == niche_slug:
            n["competitor_analysis"] = analysis
            n["status"] = "analyzed"
            break
    sm.save_niches(niches_data)

    sm.record_action("analyze_competitors")
    sm.update_status(f"Анализ конкурентов: {niche_name} ({len(competitors)} конкурентов)")
