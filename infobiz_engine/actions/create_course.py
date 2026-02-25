"""Создание полного курса: структура → уроки → ревью."""

import json
import logging
from pathlib import Path

from infobiz_engine.state.state_manager import StateManager
from infobiz_engine.ai.content_writer import (
    design_course_structure,
    write_lesson,
    review_lesson,
)
from infobiz_engine.config import CONTENT_DIR, LIMITS

logger = logging.getLogger("producer.create_course")


async def run(niche_slug: str):
    """Сгенерировать полный курс для ниши.

    Этапы:
    1. Architect: спроектировать структуру
    2. Writer: написать каждый урок
    3. Reviewer: проверить качество

    Args:
        niche_slug: Slug ниши из PRODUCER_NICHES.json
    """
    sm = StateManager()

    # Проверить лимит
    today_count = sm.get_daily_count("create_course")
    if today_count >= LIMITS["max_courses_per_day"]:
        print(f"Лимит курсов на сегодня: {today_count}/{LIMITS['max_courses_per_day']}")
        return

    # Найти нишу
    niche = sm.get_niche_by_slug(niche_slug)
    if not niche:
        print(f"Ниша не найдена: {niche_slug}")
        qualified = sm.get_qualified_niches()
        if qualified:
            print("Доступные ниши:")
            for n in qualified:
                print(f"  [{n.get('score', 0)}] {n.get('slug')} — {n.get('name')}")
        return

    niche_name = niche.get("name", niche_slug)
    target_audience = niche.get("target_audience", "")
    competitor_gaps = niche.get("competitor_analysis", {}).get("market_gaps", [])

    print(f"Создаю курс для ниши: {niche_name}")
    print()

    # Этап 1: Архитектура
    print("📐 Этап 1/3: Проектирование структуры...")
    try:
        structure = await design_course_structure(
            niche_name=niche_name,
            target_audience=target_audience,
            competitor_gaps=competitor_gaps,
        )
    except Exception as e:
        print(f"Ошибка архитектуры: {e}")
        return

    if not structure or not structure.get("modules"):
        print("Не удалось создать структуру курса.")
        return

    course_title = structure.get("title", niche_name)
    modules = structure.get("modules", [])
    total_lessons = sum(len(m.get("lessons", [])) for m in modules)

    print(f"  Курс: {course_title}")
    print(f"  Модулей: {len(modules)}, Уроков: {total_lessons}")
    for m in modules:
        print(f"    M{m.get('module_num', '?')}: {m.get('title', '?')} ({len(m.get('lessons', []))} уроков)")
    print()

    # Создать директорию курса
    course_dir = CONTENT_DIR / niche_slug
    course_dir.mkdir(parents=True, exist_ok=True)

    # Сохранить структуру
    with open(course_dir / "course.json", "w", encoding="utf-8") as f:
        json.dump(structure, f, ensure_ascii=False, indent=2)

    # Этап 2: Написание уроков
    print("✍️ Этап 2/3: Написание уроков...")
    lessons_written = 0
    lessons_approved = 0
    previous_summaries = []

    for module in modules:
        module_num = module.get("module_num", 0)
        module_title = module.get("title", f"Модуль {module_num}")
        module_dir = course_dir / f"module_{module_num:02d}"
        module_dir.mkdir(exist_ok=True)

        for lesson in module.get("lessons", []):
            lesson_num = lesson.get("lesson_num", 0)
            lesson_title = lesson.get("title", f"Урок {lesson_num}")
            lesson_type = lesson.get("type", "theory")
            lesson_topics = lesson.get("key_topics", [])

            # Проверить лимит уроков за цикл
            if lessons_written >= LIMITS["max_lessons_per_cycle"]:
                print(f"\n⏸ Лимит уроков за цикл: {lessons_written}/{LIMITS['max_lessons_per_cycle']}")
                print("Остальные уроки будут написаны в следующем цикле.")
                break

            print(f"  M{module_num} L{lesson_num}: {lesson_title} ({lesson_type})...", end=" ")

            try:
                # Написать урок
                lesson_text = await write_lesson(
                    course_title=course_title,
                    module_title=module_title,
                    lesson_title=lesson_title,
                    lesson_topics=lesson_topics,
                    lesson_type=lesson_type,
                    previous_lessons_summary="; ".join(previous_summaries[-3:]),
                )

                # Сохранить урок
                lesson_file = module_dir / f"lesson_{lesson_num:02d}.md"
                lesson_header = (
                    f"# {lesson_title}\n\n"
                    f"> Модуль {module_num}: {module_title}\n"
                    f"> Тип: {lesson_type}\n\n"
                    f"---\n\n"
                )
                lesson_file.write_text(lesson_header + lesson_text, encoding="utf-8")
                lessons_written += 1

                # Ревью
                review = await review_lesson(lesson_text, lesson_title)
                quality = review.get("quality_score", 0)
                verdict = review.get("verdict", "?")

                if verdict == "approve":
                    lessons_approved += 1
                    print(f"✅ ({quality})")
                elif verdict == "revise":
                    print(f"⚠️ ({quality}) — нужна доработка")
                else:
                    print(f"❌ ({quality})")

                # Сохранить ревью
                review_file = module_dir / f"review_{lesson_num:02d}.json"
                with open(review_file, "w", encoding="utf-8") as f:
                    json.dump(review, f, ensure_ascii=False, indent=2)

                # Добавить в историю
                previous_summaries.append(f"{lesson_title}: {', '.join(lesson_topics[:3])}")

            except Exception as e:
                print(f"ОШИБКА: {e}")
                logger.error(f"Ошибка генерации урока {lesson_title}: {e}")

        else:
            continue
        break  # break outer loop if inner limit hit

    print()

    # Создать продукт
    product_id = sm.next_product_id()
    product = {
        "id": product_id,
        "niche_slug": niche_slug,
        "title": course_title,
        "subtitle": structure.get("subtitle", ""),
        "status": "content_ready" if lessons_written == total_lessons else "draft",
        "price_rub": niche.get("competitor_analysis", {}).get("recommended_price_rub", 4990),
        "lessons_total": total_lessons,
        "lessons_written": lessons_written,
        "lessons_approved": lessons_approved,
        "course_dir": str(course_dir),
        "landing_url": None,
        "payment_url": None,
        "sales_count": 0,
        "revenue_rub": 0,
    }
    sm.add_product(product)

    # Обновить пайплайн
    sm.update_pipeline_stage("content", {
        "status": "active",
        "products_in_progress": 1,
        "products_complete": 1 if lessons_written == total_lessons else 0,
    })

    sm.record_action("create_course")

    # Итог
    print(f"Курс создан: {course_title}")
    print(f"  ID: {product_id}")
    print(f"  Уроков: {lessons_written}/{total_lessons}")
    print(f"  Одобрено ревьюером: {lessons_approved}/{lessons_written}")
    print(f"  Директория: {course_dir}")
    print(f"  Статус: {product['status']}")

    if lessons_written < total_lessons:
        print(f"\n  Для продолжения запусти: create_course {niche_slug}")

    sm.update_status(f"Курс создан: {course_title} ({lessons_written}/{total_lessons} уроков)")
