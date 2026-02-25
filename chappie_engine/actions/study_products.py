"""Изучить продукты NL International — извлечение знаний через LLM.

Чаппи читает .md файлы из базы знаний, отправляет через LLM,
извлекает структурированные данные (цена, PV, состав, для кого)
и записывает в свой "дневник" — CHAPPIE_KNOWLEDGE.json.
"""

import asyncio
import json
import logging
import re
from pathlib import Path

from shared.ai_client_cli import claude_call

from chappie_engine.config import (
    PRODUCTS_DIR, BUSINESS_DIR, FAQ_DIR, SUCCESS_STORIES_DIR,
)
from chappie_engine.state.state_manager import StateManager
from chappie_engine.safety import SafetyGuard

logger = logging.getLogger("chappie.study")

EXTRACTION_PROMPT = """Ты — аналитик продуктов NL International. Из текста ниже извлеки ВСЕ продукты.

Для каждого продукта верни JSON объект:
- name: точное название
- category: категория (питание/витамины/косметика/БАДы/программы/наборы)
- price_rub: цена в рублях (число, null если нет)
- pv: баллы PV (число, null если нет)
- key_ingredients: список ключевых ингредиентов (макс 5)
- target_audience: для кого (например "похудение", "спортсмены", "дети")
- key_benefits: главные преимущества (макс 3)
- flavors: список вкусов (если есть, иначе [])
- kbzhu: {calories, protein, fat, carbs} если есть, иначе null

Верни ТОЛЬКО JSON массив, без markdown, без пояснений. Если продуктов нет — верни [].

ТЕКСТ:
"""


def _read_md_files(directory: Path) -> list[dict]:
    """Прочитать все .md файлы из директории (рекурсивно)."""
    results = []
    if not directory.exists():
        return results

    for f in sorted(directory.rglob("*.md")):
        try:
            content = f.read_text(encoding="utf-8")
            relative_path = f.relative_to(directory)
            results.append({
                "file": str(relative_path),
                "content": content,
                "size": len(content),
            })
        except Exception as e:
            logger.warning(f"Не могу прочитать {f}: {e}")
    return results


async def _call_llm(prompt: str, max_tokens: int = 4000) -> str | None:
    """Вызвать LLM через общий AI-клиент (Claude CLI)."""
    # claude_call — синхронный (subprocess), запускаем в thread pool
    result = await asyncio.to_thread(
        claude_call,
        prompt,
        "chappie",
    )
    return result


def _parse_llm_json(text: str) -> list[dict]:
    """Извлечь JSON массив из ответа LLM (может быть обёрнут в ```json```)."""
    if not text:
        return []

    # Убрать markdown обёртку
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

    try:
        result = json.loads(text)
        if isinstance(result, list):
            return result
        if isinstance(result, dict):
            return [result]
    except json.JSONDecodeError:
        # Попробовать найти массив в тексте
        match = re.search(r"\[[\s\S]*\]", text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

    logger.warning(f"Не удалось распарсить JSON из LLM: {text[:200]}...")
    return []


def _fallback_extract(content: str, filename: str) -> list[dict]:
    """Базовое извлечение через regex — если LLM недоступен."""
    products = []
    name = filename.replace(".md", "").replace("_", " ").title()

    # Ищем цены
    prices = re.findall(r"(\d[\d\s]*)\s*(?:руб|₽|рублей)", content)
    price = int(prices[0].replace(" ", "")) if prices else None

    # Ищем PV
    pvs = re.findall(r"(\d+)\s*(?:PV|pv|ПВ)", content)
    pv = int(pvs[0]) if pvs else None

    products.append({
        "name": name,
        "category": "unknown",
        "price_rub": price,
        "pv": pv,
        "key_ingredients": [],
        "target_audience": "",
        "key_benefits": [],
        "flavors": [],
        "kbzhu": None,
        "source": "fallback_regex",
    })
    return products


async def run(category: str = "all"):
    """Изучить продукты и бизнес-модель NL International через LLM.

    Args:
        category: 'products', 'business', 'faq', 'stories', 'all'
    """
    sm = StateManager()
    sg = SafetyGuard(sm)

    # Проверим аварийный стоп
    banned, reason = sg.is_banned()
    if banned:
        print(f"Аварийный стоп: {reason}")
        return

    knowledge = sm.load_knowledge()
    studied_count = 0

    categories = {
        "products": (PRODUCTS_DIR, "products_studied"),
        "business": (BUSINESS_DIR, "business_knowledge"),
        "faq": (FAQ_DIR, "faq_knowledge"),
        "stories": (SUCCESS_STORIES_DIR, "success_stories"),
    }

    if category == "all":
        targets = categories
    elif category in categories:
        targets = {category: categories[category]}
    else:
        print(f"Неизвестная категория: {category}")
        print(f"Доступные: {', '.join(categories.keys())}, all")
        return

    all_products_detailed = knowledge.get("products_detailed", [])

    for cat_name, (directory, knowledge_key) in targets.items():
        print(f"\n--- Изучаю: {cat_name} ({directory}) ---")
        files = _read_md_files(directory)

        if not files:
            print(f"  Файлов не найдено в {directory}")
            continue

        print(f"  Найдено {len(files)} файлов")

        if cat_name == "products":
            product_names = []

            for f in files:
                name = f["file"].replace(".md", "").replace("_", " ").title()
                product_names.append(name)
                print(f"\n  Изучаю: {name} ({f['size']} символов)...")

                # Отправить через LLM для извлечения деталей
                # Ограничим содержимое до 6000 символов для LLM
                content_for_llm = f["content"][:6000]
                prompt = EXTRACTION_PROMPT + content_for_llm

                llm_result = await _call_llm(prompt)
                extracted = _parse_llm_json(llm_result)

                if extracted:
                    for prod in extracted:
                        prod["source_file"] = f["file"]
                        prod["source"] = "llm"
                    print(f"    LLM извлёк {len(extracted)} продуктов")
                    for prod in extracted:
                        price_str = f"{prod.get('price_rub', '?')}₽" if prod.get('price_rub') else "цена?"
                        pv_str = f"{prod.get('pv', '?')}PV" if prod.get('pv') else "PV?"
                        print(f"    - {prod['name']}: {price_str}, {pv_str}")
                else:
                    # Fallback
                    extracted = _fallback_extract(f["content"], f["file"])
                    print(f"    LLM недоступен, fallback regex: {len(extracted)} продуктов")

                # Обновить или добавить (не дублировать)
                for new_prod in extracted:
                    # Убрать старую запись из того же файла
                    all_products_detailed = [
                        p for p in all_products_detailed
                        if p.get("source_file") != f["file"]
                        or p.get("name", "").lower() != new_prod.get("name", "").lower()
                    ]
                    all_products_detailed.append(new_prod)

                studied_count += 1

            knowledge["products_studied"] = product_names

        elif cat_name == "business":
            knowledge["business_model_understood"] = True
            for f in files:
                print(f"  - {f['file']} ({f['size']} символов)")
                studied_count += 1

            # Ищем информацию о квалификациях
            for f in files:
                if any(kw in f["content"].lower() for kw in ["квалификац", "m1", "m2", "m3", "менеджер"]):
                    knowledge["qualifications_understood"] = True
                    print(f"  Квалификации найдены в {f['file']}")

        else:
            for f in files:
                print(f"  - {f['file']} ({f['size']} символов)")
                studied_count += 1

    # Сохранить детальные знания о продуктах
    knowledge["products_detailed"] = all_products_detailed
    knowledge["learned_at"] = _today_str()

    sm.save_knowledge(knowledge)

    # Обновить цели
    goals = sm.load_goals()
    if knowledge.get("products_studied"):
        for m in goals.get("milestones", []):
            if m["name"] == "Изучить продукты":
                m["done"] = True
        sm.save_goals(goals)

    # Записать действие
    sg.record_action("read", success=True)

    # Итог
    print(f"\n{'='*50}")
    print(f"Изучено {studied_count} документов")
    print(f"Категорий продуктов: {len(knowledge.get('products_studied', []))}")
    print(f"Детальных продуктов в дневнике: {len(all_products_detailed)}")
    print(f"Бизнес-модель: {'Да' if knowledge.get('business_model_understood') else 'Нет'}")
    print(f"Квалификации: {'Да' if knowledge.get('qualifications_understood') else 'Нет'}")

    # Показать сводку по продуктам
    if all_products_detailed:
        llm_count = sum(1 for p in all_products_detailed if p.get("source") == "llm")
        fallback_count = sum(1 for p in all_products_detailed if p.get("source") == "fallback_regex")
        with_price = sum(1 for p in all_products_detailed if p.get("price_rub"))
        with_pv = sum(1 for p in all_products_detailed if p.get("pv"))
        print(f"\n  Из LLM: {llm_count}, из regex: {fallback_count}")
        print(f"  С ценой: {with_price}, с PV: {with_pv}")

    sm.update_status(
        f"Изучение базы: {studied_count} док, "
        f"{len(all_products_detailed)} продуктов в дневнике"
    )


def _today_str() -> str:
    from datetime import datetime, timezone, timedelta
    msk = timezone(timedelta(hours=3))
    return datetime.now(msk).strftime("%Y-%m-%d")
