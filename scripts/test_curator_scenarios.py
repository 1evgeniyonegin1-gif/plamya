#!/usr/bin/env python3
"""
Комплексное тестирование AI-Куратора.

Проверяет:
1. RAG качество — не возвращает ли рецепты и нерелевантный контент
2. MediaResponder — правильно ли определяет триггеры для ED Smart, коллаген и др.
3. BusinessPresenter — есть ли данные для работы
4. Общую логику обработки сообщений

Запуск:
    python scripts/test_curator_scenarios.py
"""

import sys
import asyncio
import re
from pathlib import Path
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass

# Добавляем корень проекта в path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger

# Настройка логирования
logger.remove()
logger.add(sys.stderr, level="INFO", format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")


# ============================================
# КОНФИГУРАЦИЯ ТЕСТОВЫХ СЦЕНАРИЕВ
# ============================================

@dataclass
class RAGTestScenario:
    """Сценарий тестирования RAG"""
    name: str
    query: str
    expected_category: str
    expected_keywords: List[str]  # Должны быть в результатах
    forbidden_patterns: List[str]  # НЕ должны быть в результатах


@dataclass
class MediaResponderTestScenario:
    """Сценарий тестирования MediaResponder"""
    name: str
    query: str
    expected_should_send: bool
    expected_category: str = None
    expected_subcategory: str = None
    expected_media_type: str = None


# RAG тесты — проверяем что НЕ возвращает рецепты и мусор
RAG_TEST_SCENARIOS = [
    RAGTestScenario(
        name="ed_smart_flavor",
        query="какой вкус ED Smart посоветуешь?",
        expected_category="products",
        expected_keywords=["ed", "smart", "вкус"],
        forbidden_patterns=[
            r"рецепт",
            r"яичница",
            r"нарезаем",
            r"обжариваем",
            r"ингредиент",
            r"способ приготовления"
        ]
    ),
    RAGTestScenario(
        name="collagen_benefits",
        query="помогает ли коллаген от морщин?",
        expected_category="products",
        expected_keywords=["коллаген"],
        forbidden_patterns=[
            r"рецепт",
            r"приготовления"
        ]
    ),
    RAGTestScenario(
        name="business_income",
        query="сколько можно заработать в NL?",
        expected_category="business",
        expected_keywords=["заработ", "доход", "m1", "m2", "квалификац"],
        forbidden_patterns=[]
    ),
    RAGTestScenario(
        name="drain_effect",
        query="как работает DrainEffect?",
        expected_category="products",
        expected_keywords=["drain", "драйн", "отёк"],
        forbidden_patterns=[
            r"рецепт"
        ]
    ),
]

# MediaResponder тесты — проверяем триггеры
MEDIA_RESPONDER_SCENARIOS = [
    MediaResponderTestScenario(
        name="weight_loss_results",
        query="покажи результаты похудения",
        expected_should_send=True,
        expected_category="BEFORE_AFTER",
        expected_subcategory="weight_loss",
        expected_media_type="photo"
    ),
    MediaResponderTestScenario(
        name="ed_smart_before_after",
        query="покажи результаты до после ED Smart",
        expected_should_send=True,
        expected_category="BEFORE_AFTER",
        expected_subcategory="weight_loss",  # ED Smart должен мапиться на weight_loss
        expected_media_type="photo"
    ),
    MediaResponderTestScenario(
        name="collagen_photos",
        query="фото результатов коллагена",
        expected_should_send=True,
        expected_category="BEFORE_AFTER",
        expected_subcategory="collagen",
        expected_media_type="photo"
    ),
    MediaResponderTestScenario(
        name="income_proof",
        query="сколько можно заработать, покажи чеки",
        expected_should_send=True,
        expected_category="CHECKS",
        expected_media_type="photo"
    ),
    MediaResponderTestScenario(
        name="drain_effect_results",
        query="помогает ли драйн эффект, есть фото?",
        expected_should_send=True,
        expected_category="BEFORE_AFTER",
        expected_subcategory="drain_effect",
        expected_media_type="photo"
    ),
    MediaResponderTestScenario(
        name="simple_greeting",
        query="Привет, как дела?",
        expected_should_send=False
    ),
]


# ============================================
# ТЕСТОВЫЕ ФУНКЦИИ
# ============================================

class TestResults:
    """Сборщик результатов тестов"""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
        self.warnings = []

    def add_pass(self, name: str, details: str = ""):
        self.passed += 1
        print(f"  [OK] {name}: PASSED {details}")

    def add_fail(self, name: str, reason: str):
        self.failed += 1
        self.errors.append((name, reason))
        print(f"  [FAIL] {name}: FAILED - {reason}")

    def add_warning(self, name: str, message: str):
        self.warnings.append((name, message))
        print(f"  [WARN] {name}: WARNING - {message}")

    def summary(self) -> Tuple[int, int]:
        return self.passed, self.failed


def test_rag_quality() -> TestResults:
    """Тест качества RAG — проверяем фильтрацию рецептов"""
    print("\n" + "="*60)
    print("ТЕСТ 1: RAG КАЧЕСТВО")
    print("="*60)
    print("Проверяем что RAG фильтрует нерелевантный контент (рецепты)")

    results = TestResults()

    try:
        # Проверяем что фильтр рецептов работает
        from shared.rag.rag_engine import RAGEngine, IRRELEVANT_CONTENT_PATTERNS

        # Создаём тестовый движок
        rag = RAGEngine()

        # Тестовые тексты
        test_contents = [
            # Рецепты — должны быть отфильтрованы
            ("Яичница с кабачком. Ингредиенты на порцию: 2 яйца, кабачок. Нарезаем кабачок...", True),
            ("Способ приготовления: обжариваем на сковороде", True),
            # Нормальный контент — НЕ должен быть отфильтрован
            ("ED Smart — это сбалансированный коктейль с высоким содержанием белка", False),
            ("Коллаген помогает улучшить состояние кожи и суставов", False),
            ("M1 квалификация — это первый уровень партнёрства", False),
        ]

        filter_ok = True
        for content, should_filter in test_contents:
            is_filtered = rag._is_irrelevant_content(content)
            if is_filtered != should_filter:
                filter_ok = False
                if should_filter:
                    results.add_fail("rag_filter", f"Не отфильтрован рецепт: {content[:40]}...")
                else:
                    results.add_fail("rag_filter", f"Ошибочно отфильтрован: {content[:40]}...")

        if filter_ok:
            results.add_pass("rag_filter", "(фильтр рецептов работает корректно)")

        # Проверяем наличие паттернов
        if IRRELEVANT_CONTENT_PATTERNS:
            results.add_pass("filter_patterns", f"({len(IRRELEVANT_CONTENT_PATTERNS)} паттернов)")
        else:
            results.add_fail("filter_patterns", "Нет паттернов фильтрации")

        # Проверяем наличие полезного контента в from_telegram
        from_telegram_dir = project_root / "content" / "knowledge_base" / "from_telegram"
        if from_telegram_dir.exists():
            products_files = list(from_telegram_dir.glob("*products*.txt"))
            if products_files:
                results.add_pass("products_docs_exist", f"({len(products_files)} файлов о продуктах)")
            else:
                results.add_fail("products_docs_exist", "Нет файлов о продуктах")
        else:
            results.add_warning("from_telegram", "Папка from_telegram не найдена")

    except Exception as e:
        results.add_fail("rag_test", f"Ошибка: {e}")
        import traceback
        traceback.print_exc()

    return results


def test_media_responder_triggers() -> TestResults:
    """Тест триггеров MediaResponder"""
    print("\n" + "="*60)
    print("ТЕСТ 2: MEDIARESPONDER ТРИГГЕРЫ")
    print("="*60)
    print("Проверяем что MediaResponder правильно определяет когда отправлять медиа")

    results = TestResults()

    try:
        from curator_bot.ai.media_responder import get_media_responder, MediaResponder
        from shared.testimonials import TestimonialCategory

        responder = get_media_responder()

        for scenario in MEDIA_RESPONDER_SCENARIOS:
            config = responder.should_send_media(scenario.query)

            # Проверяем should_send
            if config['should_send'] != scenario.expected_should_send:
                results.add_fail(
                    scenario.name,
                    f"should_send={config['should_send']}, ожидалось {scenario.expected_should_send}"
                )
                continue

            if not scenario.expected_should_send:
                results.add_pass(scenario.name, "(не требуется медиа)")
                continue

            # Проверяем категорию
            actual_category = config['category'].value if config['category'] else None
            if scenario.expected_category and actual_category != scenario.expected_category.lower():
                results.add_fail(
                    scenario.name,
                    f"category={actual_category}, ожидалось {scenario.expected_category.lower()}"
                )
                continue

            # Проверяем подкатегорию
            actual_subcategory = config.get('subcategory')
            if scenario.expected_subcategory and actual_subcategory != scenario.expected_subcategory:
                results.add_warning(
                    scenario.name,
                    f"subcategory={actual_subcategory}, ожидалось {scenario.expected_subcategory}"
                )

            # Проверяем тип медиа
            if scenario.expected_media_type and config['media_type'] != scenario.expected_media_type:
                results.add_warning(
                    scenario.name,
                    f"media_type={config['media_type']}, ожидалось {scenario.expected_media_type}"
                )

            # Проверяем что файлы реально находятся
            files = responder.get_media_for_response(config, count=1)
            if files:
                file_path = Path(files[0]['path'])
                if file_path.exists():
                    results.add_pass(scenario.name, f"(файл найден: {file_path.name})")
                else:
                    results.add_fail(scenario.name, f"Файл не существует: {file_path}")
            else:
                results.add_fail(scenario.name, "Файлы не найдены в testimonials")

    except Exception as e:
        results.add_fail("media_responder_test", f"Ошибка: {e}")
        import traceback
        traceback.print_exc()

    return results


def test_business_presenter() -> TestResults:
    """Тест BusinessPresenter — проверяем наличие данных"""
    print("\n" + "="*60)
    print("ТЕСТ 3: BUSINESS PRESENTER")
    print("="*60)
    print("Проверяем что BusinessPresenter имеет данные для работы")

    results = TestResults()

    try:
        from curator_bot.ai.business_presenter import get_business_presenter

        presenter = get_business_presenter()

        # Проверяем наличие историй успеха
        if presenter.success_stories:
            results.add_pass(
                "success_stories_loaded",
                f"({len(presenter.success_stories)} историй)"
            )

            # Проверяем качество первой истории
            story = presenter.get_success_story()
            if story and len(story) > 50:
                results.add_pass("success_story_quality", f"(длина {len(story)} символов)")
            else:
                results.add_warning("success_story_quality", "История слишком короткая")
        else:
            results.add_fail(
                "success_stories_loaded",
                "Нет историй успеха (папка telegram_knowledge не существует?)"
            )

        # Проверяем наличие бизнес-постов
        if presenter.business_posts:
            results.add_pass(
                "business_posts_loaded",
                f"({len(presenter.business_posts)} постов)"
            )
        else:
            results.add_fail(
                "business_posts_loaded",
                "Нет бизнес-постов"
            )

        # Проверяем триггеры
        test_triggers = [
            ("расскажи про результаты партнёров", "success_story"),
            ("сколько можно заработать?", "income_proof"),
            ("как работает бизнес?", "business_proof"),
        ]

        for message, expected_type in test_triggers:
            media_type = presenter.should_send_business_media(message, "Короткий ответ")
            if media_type == expected_type:
                results.add_pass(f"trigger_{expected_type}", f"('{message[:30]}...')")
            else:
                results.add_warning(
                    f"trigger_{expected_type}",
                    f"Ожидалось {expected_type}, получили {media_type}"
                )

    except Exception as e:
        results.add_fail("business_presenter_test", f"Ошибка: {e}")
        import traceback
        traceback.print_exc()

    return results


def test_testimonials_data() -> TestResults:
    """Тест данных testimonials"""
    print("\n" + "="*60)
    print("ТЕСТ 4: TESTIMONIALS ДАННЫЕ")
    print("="*60)
    print("Проверяем наличие и качество testimonials")

    results = TestResults()

    try:
        from shared.testimonials import get_testimonials_manager, TestimonialCategory

        manager = get_testimonials_manager()

        # Проверяем base_dir
        if manager.base_dir.exists():
            results.add_pass("base_dir_exists", f"({manager.base_dir})")
        else:
            results.add_fail("base_dir_exists", f"Папка не найдена: {manager.base_dir}")
            return results

        # Проверяем категории
        categories_to_check = [
            (TestimonialCategory.BEFORE_AFTER, "before_after", ["weight_loss", "collagen", "drain_effect"]),
            (TestimonialCategory.CHECKS, "checks", []),
            (TestimonialCategory.SUCCESS_STORIES, "success_stories", []),
        ]

        for category, name, subcategories in categories_to_check:
            items = manager.get_random(category, count=10, with_photos_only=True)

            if items:
                results.add_pass(f"category_{name}", f"({len(items)} с фото)")

                # Проверяем что файлы существуют
                files_exist = 0
                files_missing = 0
                for item in items[:5]:
                    media_files = manager.get_media_files(item)
                    for mf in media_files:
                        if mf['exists']:
                            files_exist += 1
                        else:
                            files_missing += 1

                if files_missing > 0:
                    results.add_warning(f"{name}_files", f"{files_missing} файлов не найдено")
                else:
                    results.add_pass(f"{name}_files", f"(все {files_exist} файлов на месте)")
            else:
                results.add_fail(f"category_{name}", "Нет данных с фото")

            # Проверяем подкатегории
            for subcat in subcategories:
                subcat_items = manager.get_by_subcategory(category, subcat, count=5, with_photos_only=True)
                if subcat_items:
                    results.add_pass(f"subcategory_{subcat}", f"({len(subcat_items)} записей)")
                else:
                    results.add_warning(f"subcategory_{subcat}", "Нет данных")

    except Exception as e:
        results.add_fail("testimonials_test", f"Ошибка: {e}")
        import traceback
        traceback.print_exc()

    return results


def test_product_reference() -> TestResults:
    """Тест ProductReferenceManager — поиск фото продуктов"""
    print("\n" + "="*60)
    print("ТЕСТ 5: PRODUCT REFERENCE MANAGER")
    print("="*60)
    print("Проверяем поиск фото продуктов")

    results = TestResults()

    try:
        from content_manager_bot.utils.product_reference import ProductReferenceManager

        manager = ProductReferenceManager()

        # Тестовые запросы
        test_queries = [
            ("ED Smart — отличный продукт для похудения", "ed smart"),
            ("Коллаген помогает от морщин", "коллаген"),
            ("DrainEffect выводит лишнюю воду", "draineffect"),
            ("Greenflash витамины для здоровья", "greenflash"),
        ]

        for query, expected_keyword in test_queries:
            result = manager.extract_product_from_content(query)

            if result:
                keyword, folder_path, photo_path = result
                if photo_path and photo_path.exists():
                    results.add_pass(
                        f"product_{expected_keyword}",
                        f"(найден: {photo_path.name})"
                    )
                else:
                    results.add_warning(
                        f"product_{expected_keyword}",
                        f"Ключевое слово '{keyword}' найдено, но фото нет"
                    )
            else:
                results.add_fail(
                    f"product_{expected_keyword}",
                    f"Продукт не найден в '{query[:40]}...'"
                )

    except Exception as e:
        results.add_fail("product_reference_test", f"Ошибка: {e}")
        import traceback
        traceback.print_exc()

    return results


# ============================================
# ГЛАВНАЯ ФУНКЦИЯ
# ============================================

def main():
    """Запуск всех тестов"""
    print("="*60)
    print("ТЕСТИРОВАНИЕ AI-КУРАТОРА")
    print("="*60)
    print(f"Проект: {project_root}")
    print()

    all_results: Dict[str, TestResults] = {}

    # Тест 1: RAG качество
    all_results['rag_quality'] = test_rag_quality()

    # Тест 2: MediaResponder триггеры
    all_results['media_responder'] = test_media_responder_triggers()

    # Тест 3: BusinessPresenter
    all_results['business_presenter'] = test_business_presenter()

    # Тест 4: Testimonials данные
    all_results['testimonials'] = test_testimonials_data()

    # Тест 5: ProductReference
    all_results['product_reference'] = test_product_reference()

    # Итоги
    print("\n" + "="*60)
    print("ИТОГИ ТЕСТИРОВАНИЯ")
    print("="*60)

    total_passed = 0
    total_failed = 0

    for name, results in all_results.items():
        passed, failed = results.summary()
        total_passed += passed
        total_failed += failed

        status = "[OK]" if failed == 0 else "[FAIL]"
        print(f"  {status} {name}: {passed} passed, {failed} failed")

        # Показываем критические ошибки
        for error_name, error_msg in results.errors[:3]:
            print(f"      -> {error_name}: {error_msg}")

    print()
    print(f"ВСЕГО: {total_passed} passed, {total_failed} failed")
    print()

    if total_failed > 0:
        print("[!] ЕСТЬ ПРОБЛЕМЫ, ТРЕБУЮЩИЕ ИСПРАВЛЕНИЯ:")
        print()

        # Группируем рекомендации
        recommendations = []

        if all_results['rag_quality'].failed > 0:
            recommendations.append(
                "1. RAG: Удалить рецепты из content/knowledge_base/from_telegram/"
            )

        if all_results['media_responder'].failed > 0:
            recommendations.append(
                "2. MediaResponder: Добавить ED Smart в subcategory_map (media_responder.py:141)"
            )

        if all_results['business_presenter'].failed > 0:
            recommendations.append(
                "3. BusinessPresenter: Создать content/telegram_knowledge/ или переключить на testimonials"
            )

        if all_results['testimonials'].failed > 0:
            recommendations.append(
                "4. Testimonials: Проверить наличие файлов в content/testimonials/"
            )

        if all_results['product_reference'].failed > 0:
            recommendations.append(
                "5. ProductReference: Проверить unified_products/full_products_mapping.json"
            )

        for rec in recommendations:
            print(f"  {rec}")

        print()
        return 1
    else:
        print("[SUCCESS] Все тесты пройдены!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
