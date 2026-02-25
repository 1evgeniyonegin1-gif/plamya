"""
Load Runner - главный модуль для запуска нагрузочных тестов

Возможности:
- Параллельное выполнение запросов (asyncio)
- Контроль concurrency (ограничение одновременных запросов)
- Ramp-up (постепенное увеличение нагрузки)
- Сценарии тестирования (curator, content_manager, mixed)
- Real-time мониторинг прогресса
- Экспорт метрик и отчётов
"""

import asyncio
import time
from typing import List, Dict, Optional, Callable, Any
from dataclasses import dataclass
from pathlib import Path
import sys

# Добавляем текущую директорию в PATH для импорта
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from user_simulator import VirtualUser, VirtualAdmin
from fixtures.personas import get_test_personas
from metrics.collector import MetricsCollector
from metrics.reporter import ConsoleReporter, HTMLReporter


@dataclass
class LoadTestConfig:
    """Конфигурация нагрузочного теста"""
    # Основные параметры
    test_name: str
    scenario: str  # "curator" | "content_manager" | "mixed"

    # Пользователи
    total_users: int = 10
    concurrent_users: int = 5  # Одновременных пользователей

    # Ramp-up (постепенное увеличение нагрузки)
    ramp_up_duration_sec: float = 0  # Время выхода на полную нагрузку
    ramp_up_steps: int = 5  # Количество шагов ramp-up

    # Лимиты
    max_messages_per_user: Optional[int] = None  # Максимум сообщений на пользователя
    test_duration_sec: Optional[float] = None  # Максимальная длительность теста

    # Задержки
    delay_between_messages_sec: float = 1.0  # Задержка между сообщениями одного пользователя
    delay_variance_sec: float = 0.5  # Вариативность задержки

    # Отчёты
    export_csv: bool = True
    generate_html_report: bool = True
    output_dir: str = "load_test_results"


class LoadTestRunner:
    """
    Главный класс для запуска нагрузочных тестов

    Управляет:
    - Выполнением сценариев
    - Параллелизмом (concurrency)
    - Сбором метрик
    - Генерацией отчётов
    """

    def __init__(self, config: LoadTestConfig):
        self.config = config
        self.collector = MetricsCollector()
        self.console_reporter = ConsoleReporter(self.collector)

        # Счётчики
        self.total_requests = 0
        self.completed_requests = 0
        self.start_time = None

        # Семафор для контроля concurrency
        self.semaphore = asyncio.Semaphore(config.concurrent_users)

    async def run(
        self,
        bot_handler: Optional[Callable] = None,
        content_generator: Optional[Callable] = None,
    ) -> MetricsCollector:
        """
        Запускает нагрузочный тест

        Args:
            bot_handler: Handler для AI-Куратора (обработка сообщений)
            content_generator: Generator для Content Manager (генерация постов)

        Returns:
            MetricsCollector с собранными метриками
        """
        self.start_time = time.time()

        # Заголовок теста
        self._print_test_header()

        # Выбираем сценарий
        if self.config.scenario == "curator":
            await self._run_curator_scenario(bot_handler)
        elif self.config.scenario == "content_manager":
            await self._run_content_manager_scenario(content_generator)
        elif self.config.scenario == "mixed":
            await self._run_mixed_scenario(bot_handler, content_generator)
        else:
            raise ValueError(f"Неизвестный сценарий: {self.config.scenario}")

        # Финальная сводка
        test_duration = time.time() - self.start_time
        self.console_reporter.print_summary(test_duration)

        # Экспорт результатов
        self._export_results()

        return self.collector

    async def _run_curator_scenario(self, bot_handler: Callable):
        """
        Сценарий тестирования AI-Куратора

        Args:
            bot_handler: Handler для обработки сообщений
        """
        if not bot_handler:
            raise ValueError("bot_handler обязателен для curator сценария")

        # Получаем персоны
        all_personas = get_test_personas()
        personas = all_personas[:self.config.total_users]

        # Считаем общее количество сообщений
        self.total_requests = sum(len(p.test_messages) for p in personas)

        if self.config.max_messages_per_user:
            self.total_requests = min(
                self.total_requests,
                self.config.total_users * self.config.max_messages_per_user
            )

        print(f"Пользователей: {len(personas)}")
        print(f"Ожидается сообщений: {self.total_requests}\n")

        # Запускаем отправку сообщений
        tasks = []
        for persona in personas:
            task = self._send_user_messages(persona, bot_handler)
            tasks.append(task)

        # Выполняем параллельно с ramp-up
        if self.config.ramp_up_duration_sec > 0:
            await self._execute_with_rampup(tasks)
        else:
            await asyncio.gather(*tasks)

    async def _run_content_manager_scenario(self, content_generator: Callable):
        """
        Сценарий тестирования Content Manager

        Args:
            content_generator: Generator для создания постов
        """
        if not content_generator:
            raise ValueError("content_generator обязателен для content_manager сценария")

        # Создаём виртуальных админов
        admin_count = min(self.config.total_users, 10)  # Не больше 10 админов
        admins = [
            VirtualAdmin(
                admin_id=i,
                telegram_id=500000 + i,
                name=f"Admin_{i}",
                post_types=["product", "motivation", "tips", "success_story", "news", "promo"]
            )
            for i in range(admin_count)
        ]

        # Количество постов на админа
        posts_per_admin = self.config.max_messages_per_user or 10
        self.total_requests = admin_count * posts_per_admin

        print(f"Админов: {admin_count}")
        print(f"Постов на админа: {posts_per_admin}")
        print(f"Ожидается постов: {self.total_requests}\n")

        # Запускаем генерацию постов
        tasks = []
        for admin in admins:
            task = self._generate_admin_posts(admin, content_generator, posts_per_admin)
            tasks.append(task)

        # Выполняем параллельно
        if self.config.ramp_up_duration_sec > 0:
            await self._execute_with_rampup(tasks)
        else:
            await asyncio.gather(*tasks)

    async def _run_mixed_scenario(
        self,
        bot_handler: Callable,
        content_generator: Callable
    ):
        """
        Смешанный сценарий (curator + content_manager)

        Args:
            bot_handler: Handler для AI-Куратора
            content_generator: Generator для Content Manager
        """
        if not bot_handler or not content_generator:
            raise ValueError("Оба handler'а обязательны для mixed сценария")

        # Половина пользователей - curator, половина - content manager
        curator_users = self.config.total_users // 2
        content_users = self.config.total_users - curator_users

        all_personas = get_test_personas()
        curator_personas = all_personas[:curator_users]

        # Админы для content manager
        admins = [
            VirtualAdmin(
                admin_id=i,
                telegram_id=500000 + i,
                name=f"Admin_{i}",
                post_types=["product", "motivation", "tips", "success_story"]
            )
            for i in range(content_users)
        ]

        # Считаем общее количество запросов
        curator_messages = sum(len(p.test_messages) for p in curator_personas)
        content_posts = content_users * (self.config.max_messages_per_user or 10)
        self.total_requests = curator_messages + content_posts

        print(f"Curator пользователей: {curator_users}")
        print(f"Content Manager админов: {content_users}")
        print(f"Ожидается запросов: {self.total_requests}\n")

        # Запускаем обе группы параллельно
        tasks = []

        # Curator tasks
        for persona in curator_personas:
            task = self._send_user_messages(persona, bot_handler)
            tasks.append(task)

        # Content Manager tasks
        for admin in admins:
            posts_count = self.config.max_messages_per_user or 10
            task = self._generate_admin_posts(admin, content_generator, posts_count)
            tasks.append(task)

        # Выполняем параллельно
        if self.config.ramp_up_duration_sec > 0:
            await self._execute_with_rampup(tasks)
        else:
            await asyncio.gather(*tasks)

    async def _send_user_messages(
        self,
        persona: VirtualUser,
        bot_handler: Callable
    ):
        """
        Отправляет сообщения от одного пользователя

        Args:
            persona: Виртуальный пользователь
            bot_handler: Handler для обработки
        """
        messages = persona.test_messages

        if self.config.max_messages_per_user:
            messages = messages[:self.config.max_messages_per_user]

        for i, message in enumerate(messages):
            # Контролируем concurrency через семафор
            async with self.semaphore:
                # Задержка между сообщениями
                if i > 0:
                    delay = self._get_random_delay()
                    await asyncio.sleep(delay)

                # Отправляем сообщение
                result = await persona.send_message_to_bot(
                    bot_handler=bot_handler,
                    message_text=message
                )

                # Записываем метрику
                self.collector.record_message(
                    user_id=persona.user_id,
                    success=result["success"],
                    response_time_ms=result["response_time_ms"],
                    error=result.get("error"),
                    intent=persona.intent,
                    segment=persona.segment,
                )

                # Обновляем прогресс
                self.completed_requests += 1
                self._update_progress()

    async def _generate_admin_posts(
        self,
        admin: VirtualAdmin,
        content_generator: Callable,
        posts_count: int
    ):
        """
        Генерирует посты от одного админа

        Args:
            admin: Виртуальный админ
            content_generator: Generator для создания постов
            posts_count: Количество постов
        """
        import random

        for i in range(posts_count):
            # Контролируем concurrency
            async with self.semaphore:
                # Задержка между постами
                if i > 0:
                    delay = self._get_random_delay()
                    await asyncio.sleep(delay)

                # Выбираем случайный тип поста
                post_type = random.choice(admin.post_types)

                # Генерируем пост
                result = await admin.generate_post(
                    post_type=post_type,
                    generate_callback=content_generator
                )

                # Записываем метрику
                self.collector.record_post_generation(
                    user_id=admin.admin_id,
                    success=result["success"],
                    response_time_ms=result["generation_time_ms"],
                    post_type=post_type,
                    error=result.get("error"),
                )

                # Обновляем прогресс
                self.completed_requests += 1
                self._update_progress()

    async def _execute_with_rampup(self, tasks: List[asyncio.Task]):
        """
        Выполняет задачи с постепенным увеличением нагрузки (ramp-up)

        Args:
            tasks: Список задач для выполнения
        """
        total_tasks = len(tasks)
        step_size = total_tasks // self.config.ramp_up_steps
        step_duration = self.config.ramp_up_duration_sec / self.config.ramp_up_steps

        print(f"Ramp-up: {self.config.ramp_up_steps} шагов по {step_duration:.1f} сек\n")

        for step in range(self.config.ramp_up_steps):
            # Количество задач для этого шага
            start_idx = step * step_size
            end_idx = start_idx + step_size if step < self.config.ramp_up_steps - 1 else total_tasks

            step_tasks = tasks[start_idx:end_idx]

            print(f"Ramp-up шаг {step + 1}/{self.config.ramp_up_steps}: "
                  f"запуск {len(step_tasks)} задач")

            # Запускаем задачи этого шага
            for task in step_tasks:
                asyncio.create_task(task)

            # Ждём до следующего шага
            if step < self.config.ramp_up_steps - 1:
                await asyncio.sleep(step_duration)

        # Ждём завершения всех задач
        await asyncio.gather(*tasks)

    def _get_random_delay(self) -> float:
        """Возвращает случайную задержку с вариативностью"""
        import random
        variance = random.uniform(
            -self.config.delay_variance_sec,
            self.config.delay_variance_sec
        )
        delay = self.config.delay_between_messages_sec + variance
        return max(0.1, delay)  # Минимум 0.1 сек

    def _update_progress(self):
        """Обновляет прогресс в консоли"""
        elapsed = time.time() - self.start_time

        self.console_reporter.print_progress(
            current=self.completed_requests,
            total=self.total_requests,
            elapsed_sec=elapsed,
            show_metrics=True
        )

    def _print_test_header(self):
        """Выводит заголовок теста"""
        self.console_reporter.print_header(
            test_name=self.config.test_name,
            total_users=self.config.total_users,
            total_messages=0  # Будет обновлено в сценарии
        )

        print("Конфигурация:")
        print(f"  Сценарий: {self.config.scenario}")
        print(f"  Пользователей: {self.config.total_users}")
        print(f"  Одновременных: {self.config.concurrent_users}")
        if self.config.ramp_up_duration_sec > 0:
            print(f"  Ramp-up: {self.config.ramp_up_duration_sec:.0f} сек "
                  f"({self.config.ramp_up_steps} шагов)")
        print(f"  Задержка между запросами: {self.config.delay_between_messages_sec:.1f} сек")
        print()

    def _export_results(self):
        """Экспортирует результаты теста"""
        output_dir = Path(self.config.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Генерируем уникальное имя на основе timestamp
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        test_slug = self.config.test_name.lower().replace(" ", "_")

        # Экспорт в CSV
        if self.config.export_csv:
            csv_path = output_dir / f"{test_slug}_{timestamp}.csv"
            self.collector.export_to_csv(str(csv_path))

            csv_agg_path = output_dir / f"{test_slug}_{timestamp}_aggregated.csv"
            self.collector.export_aggregated_to_csv(str(csv_agg_path))

        # Генерация HTML отчёта
        if self.config.generate_html_report:
            html_path = output_dir / f"{test_slug}_{timestamp}.html"

            html_reporter = HTMLReporter(self.collector)
            html_reporter.generate_report(
                output_path=str(html_path),
                test_name=self.config.test_name,
                test_config={
                    "Сценарий": self.config.scenario,
                    "Пользователей": self.config.total_users,
                    "Одновременных": self.config.concurrent_users,
                    "Задержка между запросами": f"{self.config.delay_between_messages_sec} сек",
                }
            )


# Вспомогательные функции для быстрого запуска тестов

async def quick_curator_test(
    bot_handler: Callable,
    users: int = 10,
    concurrent: int = 5,
    max_messages: int = 5
) -> Dict[str, Any]:
    """
    Быстрый тест AI-Куратора

    Args:
        bot_handler: Handler для обработки сообщений
        users: Количество пользователей
        concurrent: Одновременных пользователей
        max_messages: Максимум сообщений на пользователя

    Returns:
        Dict с метриками (summary, aggregated, user_metrics)
    """
    config = LoadTestConfig(
        test_name="Quick Curator Test",
        scenario="curator",
        total_users=users,
        concurrent_users=concurrent,
        max_messages_per_user=max_messages,
        delay_between_messages_sec=0.5,
        export_csv=True,
        generate_html_report=True,
    )

    runner = LoadTestRunner(config)
    collector = await runner.run(bot_handler=bot_handler)

    # Возвращаем словарь с метриками
    return {
        "summary": collector.get_summary(),
        "aggregated": collector.get_aggregated_metrics(),
        "user_metrics": collector.get_user_metrics() if hasattr(collector, 'get_user_metrics') else [],
    }


async def quick_content_manager_test(
    content_generator: Callable,
    admins: int = 5,
    concurrent: int = 3,
    posts_per_admin: int = 10
) -> Dict[str, Any]:
    """
    Быстрый тест Content Manager

    Args:
        content_generator: Generator для создания постов
        admins: Количество админов
        concurrent: Одновременных админов
        posts_per_admin: Постов на админа

    Returns:
        Dict с метриками (summary, aggregated, user_metrics)
    """
    config = LoadTestConfig(
        test_name="Quick Content Manager Test",
        scenario="content_manager",
        total_users=admins,
        concurrent_users=concurrent,
        max_messages_per_user=posts_per_admin,
        delay_between_messages_sec=1.0,
        export_csv=True,
        generate_html_report=True,
    )

    runner = LoadTestRunner(config)
    collector = await runner.run(content_generator=content_generator)

    return {
        "summary": collector.get_summary(),
        "aggregated": collector.get_aggregated_metrics(),
        "user_metrics": collector.get_user_metrics() if hasattr(collector, 'get_user_metrics') else [],
    }


async def stress_test(
    bot_handler: Callable,
    users: int = 50,
    concurrent: int = 20,
    max_messages: int = 5,
    ramp_up_sec: float = 10.0
) -> Dict[str, Any]:
    """
    Стресс-тест с высокой нагрузкой

    Args:
        bot_handler: Handler для обработки сообщений
        users: Количество пользователей
        concurrent: Одновременных пользователей
        max_messages: Максимум сообщений на пользователя
        ramp_up_sec: Время выхода на полную нагрузку

    Returns:
        Dict с метриками (summary, aggregated, user_metrics)
    """
    config = LoadTestConfig(
        test_name="Stress Test",
        scenario="curator",
        total_users=users,
        concurrent_users=concurrent,
        max_messages_per_user=max_messages,
        ramp_up_duration_sec=ramp_up_sec,
        ramp_up_steps=5,
        delay_between_messages_sec=0.3,
        delay_variance_sec=0.2,
        export_csv=True,
        generate_html_report=True,
    )

    runner = LoadTestRunner(config)
    collector = await runner.run(bot_handler=bot_handler)

    return {
        "summary": collector.get_summary(),
        "aggregated": collector.get_aggregated_metrics(),
        "user_metrics": collector.get_user_metrics() if hasattr(collector, 'get_user_metrics') else [],
    }


# Пример использования
if __name__ == "__main__":
    # Для примера создаём простой mock handler
    async def mock_bot_handler(message):
        """Mock handler для тестирования"""
        await asyncio.sleep(0.5)  # Эмуляция обработки
        await message.answer(f"Получил: {message.text}")

    # Запускаем быстрый тест
    print("Запуск быстрого теста...\n")
    asyncio.run(quick_curator_test(
        bot_handler=mock_bot_handler,
        users=5,
        concurrent=3,
        max_messages=3
    ))
