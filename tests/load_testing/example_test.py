"""
Пример использования Load Testing системы

Демонстрирует:
1. Быстрый тест AI-Куратора с mock handler
2. Тест Content Manager с mock generator
3. Стресс-тест с высокой нагрузкой
"""

import asyncio
from unittest.mock import MagicMock, AsyncMock

from load_runner import (
    LoadTestConfig,
    LoadTestRunner,
    quick_curator_test,
    quick_content_manager_test,
    stress_test
)
from mocks.mock_ai_clients import MockAnthropicClient, MockContentGenerator


async def mock_bot_handler(message):
    """
    Mock handler для AI-Куратора

    Эмулирует обработку сообщений через MockAnthropicClient
    """
    mock_client = MockAnthropicClient(latency_ms=500, latency_variance_ms=200)

    # Генерируем ответ
    response = await mock_client.generate_response(
        system_prompt="Ты AI-куратор NL International",
        user_message=message.text,
        temperature=0.7
    )

    # Отправляем ответ пользователю
    await message.answer(response)


async def mock_content_generator(admin_id: int, post_type: str):
    """
    Mock generator для Content Manager

    Эмулирует генерацию постов через MockContentGenerator
    """
    mock_generator = MockContentGenerator(latency_ms=800, latency_variance_ms=300)

    # Генерируем пост
    result = await mock_generator.generate_content(
        post_type=post_type,
        mood={"hook": "Слушай, вот интересная тема..."},
        context={}
    )

    return result


async def example_1_quick_curator_test():
    """
    Пример 1: Быстрый тест AI-Куратора

    10 пользователей, 5 одновременных, по 3 сообщения
    """
    print("\n" + "="*80)
    print("ПРИМЕР 1: Быстрый тест AI-Куратора")
    print("="*80 + "\n")

    collector = await quick_curator_test(
        bot_handler=mock_bot_handler,
        users=10,
        concurrent=5,
        max_messages=3
    )

    print("\nТест завершён!")
    print(f"Результаты сохранены в: load_test_results/")


async def example_2_quick_content_manager_test():
    """
    Пример 2: Быстрый тест Content Manager

    5 админов, 3 одновременных, по 5 постов
    """
    print("\n" + "="*80)
    print("ПРИМЕР 2: Быстрый тест Content Manager")
    print("="*80 + "\n")

    collector = await quick_content_manager_test(
        content_generator=mock_content_generator,
        admins=5,
        concurrent=3,
        posts_per_admin=5
    )

    print("\nТест завершён!")
    print(f"Результаты сохранены в: load_test_results/")


async def example_3_stress_test():
    """
    Пример 3: Стресс-тест с высокой нагрузкой

    50 пользователей, 20 одновременных, ramp-up 10 сек
    """
    print("\n" + "="*80)
    print("ПРИМЕР 3: Стресс-тест")
    print("="*80 + "\n")

    collector = await stress_test(
        bot_handler=mock_bot_handler,
        users=50,
        concurrent=20,
        ramp_up_sec=10.0
    )

    print("\nТест завершён!")
    print(f"Результаты сохранены в: load_test_results/")


async def example_4_custom_test():
    """
    Пример 4: Кастомный тест с полной конфигурацией

    Демонстрирует все возможности LoadTestConfig
    """
    print("\n" + "="*80)
    print("ПРИМЕР 4: Кастомный тест")
    print("="*80 + "\n")

    config = LoadTestConfig(
        test_name="Кастомный тест AI-Куратора",
        scenario="curator",
        total_users=20,
        concurrent_users=10,
        max_messages_per_user=5,
        ramp_up_duration_sec=5.0,
        ramp_up_steps=5,
        delay_between_messages_sec=0.8,
        delay_variance_sec=0.3,
        export_csv=True,
        generate_html_report=True,
        output_dir="custom_test_results"
    )

    runner = LoadTestRunner(config)
    collector = await runner.run(bot_handler=mock_bot_handler)

    print("\nТест завершён!")
    print(f"Результаты сохранены в: {config.output_dir}/")


async def example_5_mixed_scenario():
    """
    Пример 5: Смешанный сценарий (curator + content_manager)

    20 пользователей: 10 curator + 10 content manager
    """
    print("\n" + "="*80)
    print("ПРИМЕР 5: Смешанный сценарий")
    print("="*80 + "\n")

    config = LoadTestConfig(
        test_name="Смешанный тест (Curator + Content Manager)",
        scenario="mixed",
        total_users=20,
        concurrent_users=8,
        max_messages_per_user=5,
        delay_between_messages_sec=1.0,
        export_csv=True,
        generate_html_report=True,
    )

    runner = LoadTestRunner(config)
    collector = await runner.run(
        bot_handler=mock_bot_handler,
        content_generator=mock_content_generator
    )

    print("\nТест завершён!")
    print(f"Результаты сохранены в: load_test_results/")


async def main():
    """Главная функция - запускает все примеры"""
    print("\n" + "="*80)
    print("ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ LOAD TESTING СИСТЕМЫ")
    print("="*80)

    # Можно запустить все примеры или выбрать конкретный
    examples = [
        ("1", "Быстрый тест AI-Куратора", example_1_quick_curator_test),
        ("2", "Быстрый тест Content Manager", example_2_quick_content_manager_test),
        ("3", "Стресс-тест", example_3_stress_test),
        ("4", "Кастомный тест", example_4_custom_test),
        ("5", "Смешанный сценарий", example_5_mixed_scenario),
    ]

    print("\nДоступные примеры:")
    for num, name, _ in examples:
        print(f"  {num}. {name}")

    print("\nЗапускаем Пример 1 (быстрый тест)...")
    print("Для запуска других примеров, раскомментируйте соответствующую строку в main()\n")

    # Запускаем Пример 1 (быстрый тест)
    await example_1_quick_curator_test()

    # Раскомментируйте для запуска других примеров:
    # await example_2_quick_content_manager_test()
    # await example_3_stress_test()
    # await example_4_custom_test()
    # await example_5_mixed_scenario()

    print("\n" + "="*80)
    print("ВСЕ ПРИМЕРЫ ЗАВЕРШЕНЫ")
    print("="*80 + "\n")


if __name__ == "__main__":
    # Запускаем примеры
    asyncio.run(main())
