"""
Reporters для нагрузочного тестирования

Два типа репортов:
1. ConsoleReporter - красивый вывод в консоль с прогрессом
2. HTMLReporter - HTML отчёт с графиками (matplotlib)
"""

import time
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path
import sys

# Добавляем родительскую директорию в PATH для импорта
parent_dir = Path(__file__).parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from metrics.collector import MetricsCollector, AggregatedMetrics


class ConsoleReporter:
    """
    Вывод метрик в консоль в реальном времени

    Показывает:
    - Прогресс выполнения
    - Текущие метрики (RPS, Response Time, Error Rate)
    - Финальную сводку
    """

    def __init__(self, collector: MetricsCollector):
        self.collector = collector
        self.last_report_time = time.time()
        self.last_metrics_count = 0

    def print_header(self, test_name: str, total_users: int, total_messages: int):
        """
        Выводит заголовок теста

        Args:
            test_name: Название теста
            total_users: Количество пользователей
            total_messages: Ожидаемое количество сообщений
        """
        print("\n" + "=" * 80)
        print(f"НАГРУЗОЧНЫЙ ТЕСТ: {test_name}")
        print("=" * 80)
        print(f"Начало: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Пользователей: {total_users}")
        print(f"Ожидается запросов: {total_messages}")
        print("=" * 80 + "\n")

    def print_progress(
        self,
        current: int,
        total: int,
        elapsed_sec: float,
        show_metrics: bool = True
    ):
        """
        Выводит прогресс выполнения

        Args:
            current: Текущее количество выполненных запросов
            total: Общее количество запросов
            elapsed_sec: Прошедшее время в секундах
            show_metrics: Показывать ли метрики
        """
        # Прогресс-бар
        progress = current / total if total > 0 else 0
        bar_length = 40
        filled = int(bar_length * progress)
        bar = "█" * filled + "░" * (bar_length - filled)

        # Процент и оставшееся время
        percentage = progress * 100
        rate = current / elapsed_sec if elapsed_sec > 0 else 0
        remaining_sec = (total - current) / rate if rate > 0 else 0

        # Форматируем время
        elapsed_str = self._format_duration(elapsed_sec)
        remaining_str = self._format_duration(remaining_sec)

        print(f"\r[{bar}] {percentage:5.1f}% | {current}/{total} | "
              f"Прошло: {elapsed_str} | Осталось: {remaining_str} | "
              f"RPS: {rate:.1f}", end="", flush=True)

        # Выводим метрики раз в 2 секунды
        if show_metrics and time.time() - self.last_report_time >= 2.0:
            print()  # Новая строка
            self._print_current_metrics()
            self.last_report_time = time.time()

    def _print_current_metrics(self):
        """Выводит текущие метрики"""
        # Берём метрики за последние 5 секунд
        current_time = time.time()
        metrics = self.collector.get_aggregated_metrics(
            start_time=current_time - 5.0,
            end_time=current_time
        )

        if metrics.total_requests == 0:
            return

        success_rate = 100 - metrics.error_rate

        print(f"  └─ Метрики (5 сек): "
              f"Успешно: {success_rate:.1f}% | "
              f"Avg RT: {metrics.avg_response_time_ms:.0f}ms | "
              f"P95: {metrics.p95_response_time_ms:.0f}ms")

    def print_summary(self, test_duration_sec: float):
        """
        Выводит финальную сводку теста

        Args:
            test_duration_sec: Длительность теста в секундах
        """
        print("\n\n" + "=" * 80)
        print("ИТОГОВАЯ СВОДКА")
        print("=" * 80)

        metrics = self.collector.get_aggregated_metrics()

        # Основная информация
        print(f"\nДлительность теста: {self._format_duration(test_duration_sec)}")
        print(f"Всего запросов: {metrics.total_requests}")
        print(f"Успешных: {metrics.successful_requests} ({100 - metrics.error_rate:.1f}%)")
        print(f"Ошибок: {metrics.failed_requests} ({metrics.error_rate:.1f}%)")

        # Response Time
        print(f"\nResponse Time:")
        print(f"  Минимальный: {metrics.min_response_time_ms:.2f} ms")
        print(f"  Максимальный: {metrics.max_response_time_ms:.2f} ms")
        print(f"  Средний: {metrics.avg_response_time_ms:.2f} ms")
        print(f"  Медиана (P50): {metrics.median_response_time_ms:.2f} ms")
        print(f"  P95: {metrics.p95_response_time_ms:.2f} ms")
        print(f"  P99: {metrics.p99_response_time_ms:.2f} ms")

        # Throughput
        print(f"\nThroughput:")
        print(f"  Запросов в секунду: {metrics.requests_per_second:.2f} req/sec")

        # Распределение по интентам (если есть)
        if metrics.intent_distribution:
            print(f"\nРаспределение по интентам:")
            for intent, count in sorted(
                metrics.intent_distribution.items(),
                key=lambda x: x[1],
                reverse=True
            ):
                percentage = (count / metrics.total_requests) * 100
                print(f"  {intent:12s}: {count:4d} ({percentage:5.1f}%)")

        # Распределение по сегментам (если есть)
        if metrics.segment_distribution:
            print(f"\nРаспределение по сегментам:")
            for segment, count in sorted(
                metrics.segment_distribution.items(),
                key=lambda x: x[1],
                reverse=True
            ):
                percentage = (count / metrics.total_requests) * 100
                print(f"  Сегмент {segment}: {count:4d} ({percentage:5.1f}%)")

        # Топ ошибок (если есть)
        if metrics.error_distribution:
            print(f"\nТоп ошибок:")
            top_errors = sorted(
                metrics.error_distribution.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]

            for error, count in top_errors:
                percentage = (count / metrics.failed_requests) * 100 if metrics.failed_requests > 0 else 0
                print(f"  {error[:60]:60s}: {count:3d} ({percentage:5.1f}%)")

        print("\n" + "=" * 80 + "\n")

    def _format_duration(self, seconds: float) -> str:
        """Форматирует длительность в человекочитаемый вид"""
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"
        else:
            hours = int(seconds / 3600)
            minutes = int((seconds % 3600) / 60)
            return f"{hours}h {minutes}m"


class HTMLReporter:
    """
    Генерация HTML отчёта с графиками

    Использует matplotlib для построения графиков:
    - Response Time over Time
    - Throughput over Time
    - Error Rate over Time
    - Response Time Distribution (histogram)
    - Intent/Segment Distribution
    """

    def __init__(self, collector: MetricsCollector):
        self.collector = collector

    def generate_report(
        self,
        output_path: str,
        test_name: str,
        test_config: Optional[Dict] = None
    ):
        """
        Генерирует HTML отчёт с графиками

        Args:
            output_path: Путь к HTML файлу
            test_name: Название теста
            test_config: Конфигурация теста (опционально)
        """
        try:
            import matplotlib
            matplotlib.use('Agg')  # Не показывать GUI
            import matplotlib.pyplot as plt
        except ImportError:
            print("ОШИБКА: matplotlib не установлен. Установите: pip install matplotlib")
            return

        # Создаём директорию для графиков
        output_dir = Path(output_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)

        charts_dir = output_dir / "charts"
        charts_dir.mkdir(exist_ok=True)

        # Генерируем графики
        print("Генерация графиков...")

        chart_files = {}

        try:
            chart_files['response_time'] = self._generate_response_time_chart(charts_dir)
            chart_files['throughput'] = self._generate_throughput_chart(charts_dir)
            chart_files['error_rate'] = self._generate_error_rate_chart(charts_dir)
            chart_files['rt_distribution'] = self._generate_rt_distribution_chart(charts_dir)
            chart_files['intent_distribution'] = self._generate_intent_distribution_chart(charts_dir)
        except Exception as e:
            print(f"Ошибка при генерации графиков: {e}")

        # Генерируем HTML
        print(f"Создание HTML отчёта: {output_path}")
        html = self._generate_html(
            test_name=test_name,
            test_config=test_config,
            chart_files=chart_files
        )

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)

        print(f"HTML отчёт создан: {output_path}")

    def _generate_response_time_chart(self, output_dir: Path) -> str:
        """Генерирует график Response Time over Time"""
        import matplotlib.pyplot as plt

        windows = self.collector.get_metrics_by_time_window(window_sec=5.0)

        if not windows:
            return None

        times = [datetime.fromtimestamp(w.start_time) for w in windows]
        avg_rt = [w.avg_response_time_ms for w in windows]
        p95_rt = [w.p95_response_time_ms for w in windows]
        p99_rt = [w.p99_response_time_ms for w in windows]

        plt.figure(figsize=(12, 6))
        plt.plot(times, avg_rt, label='Avg Response Time', linewidth=2)
        plt.plot(times, p95_rt, label='P95', linewidth=2, linestyle='--')
        plt.plot(times, p99_rt, label='P99', linewidth=2, linestyle=':')
        plt.xlabel('Время')
        plt.ylabel('Response Time (ms)')
        plt.title('Response Time во времени')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        plt.tight_layout()

        file_path = output_dir / "response_time.png"
        plt.savefig(file_path, dpi=100)
        plt.close()

        return file_path.name

    def _generate_throughput_chart(self, output_dir: Path) -> str:
        """Генерирует график Throughput over Time"""
        import matplotlib.pyplot as plt

        windows = self.collector.get_metrics_by_time_window(window_sec=5.0)

        if not windows:
            return None

        times = [datetime.fromtimestamp(w.start_time) for w in windows]
        rps = [w.requests_per_second for w in windows]

        plt.figure(figsize=(12, 6))
        plt.plot(times, rps, label='Requests per Second', linewidth=2, color='green')
        plt.xlabel('Время')
        plt.ylabel('Requests per Second')
        plt.title('Throughput во времени')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        plt.tight_layout()

        file_path = output_dir / "throughput.png"
        plt.savefig(file_path, dpi=100)
        plt.close()

        return file_path.name

    def _generate_error_rate_chart(self, output_dir: Path) -> str:
        """Генерирует график Error Rate over Time"""
        import matplotlib.pyplot as plt

        windows = self.collector.get_metrics_by_time_window(window_sec=5.0)

        if not windows:
            return None

        times = [datetime.fromtimestamp(w.start_time) for w in windows]
        error_rates = [w.error_rate for w in windows]

        plt.figure(figsize=(12, 6))
        plt.plot(times, error_rates, label='Error Rate (%)', linewidth=2, color='red')
        plt.xlabel('Время')
        plt.ylabel('Error Rate (%)')
        plt.title('Error Rate во времени')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        plt.tight_layout()

        file_path = output_dir / "error_rate.png"
        plt.savefig(file_path, dpi=100)
        plt.close()

        return file_path.name

    def _generate_rt_distribution_chart(self, output_dir: Path) -> str:
        """Генерирует гистограмму распределения Response Time"""
        import matplotlib.pyplot as plt

        response_times = [
            m.response_time_ms for m in self.collector.metrics if m.success
        ]

        if not response_times:
            return None

        plt.figure(figsize=(12, 6))
        plt.hist(response_times, bins=50, edgecolor='black', alpha=0.7)
        plt.xlabel('Response Time (ms)')
        plt.ylabel('Количество запросов')
        plt.title('Распределение Response Time')
        plt.grid(True, alpha=0.3, axis='y')
        plt.tight_layout()

        file_path = output_dir / "rt_distribution.png"
        plt.savefig(file_path, dpi=100)
        plt.close()

        return file_path.name

    def _generate_intent_distribution_chart(self, output_dir: Path) -> str:
        """Генерирует круговую диаграмму распределения интентов"""
        import matplotlib.pyplot as plt

        metrics = self.collector.get_aggregated_metrics()

        if not metrics.intent_distribution:
            return None

        labels = list(metrics.intent_distribution.keys())
        sizes = list(metrics.intent_distribution.values())

        plt.figure(figsize=(10, 8))
        plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
        plt.title('Распределение по интентам')
        plt.axis('equal')
        plt.tight_layout()

        file_path = output_dir / "intent_distribution.png"
        plt.savefig(file_path, dpi=100)
        plt.close()

        return file_path.name

    def _generate_html(
        self,
        test_name: str,
        test_config: Optional[Dict],
        chart_files: Dict[str, str]
    ) -> str:
        """Генерирует HTML разметку отчёта"""
        metrics = self.collector.get_aggregated_metrics()

        html = f"""
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Отчёт: {test_name}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f5;
            color: #333;
            line-height: 1.6;
            padding: 20px;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            padding: 40px;
            border-radius: 12px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 15px;
            margin-bottom: 30px;
        }}
        h2 {{
            color: #34495e;
            margin-top: 40px;
            margin-bottom: 20px;
            border-left: 4px solid #3498db;
            padding-left: 15px;
        }}
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }}
        .metric-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .metric-card.success {{
            background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        }}
        .metric-card.error {{
            background: linear-gradient(135deg, #eb3349 0%, #f45c43 100%);
        }}
        .metric-card.performance {{
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        }}
        .metric-label {{
            font-size: 14px;
            opacity: 0.9;
            margin-bottom: 5px;
        }}
        .metric-value {{
            font-size: 32px;
            font-weight: bold;
        }}
        .chart {{
            margin: 30px 0;
            text-align: center;
        }}
        .chart img {{
            max-width: 100%;
            height: auto;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #e0e0e0;
        }}
        th {{
            background: #f8f9fa;
            font-weight: 600;
            color: #495057;
        }}
        tr:hover {{
            background: #f8f9fa;
        }}
        .config {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
        }}
        .timestamp {{
            color: #6c757d;
            font-size: 14px;
            margin-bottom: 20px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{test_name}</h1>
        <div class="timestamp">
            Сгенерировано: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </div>

        <h2>Основные метрики</h2>
        <div class="summary-grid">
            <div class="metric-card">
                <div class="metric-label">Всего запросов</div>
                <div class="metric-value">{metrics.total_requests}</div>
            </div>
            <div class="metric-card success">
                <div class="metric-label">Успешных</div>
                <div class="metric-value">{metrics.successful_requests} ({100 - metrics.error_rate:.1f}%)</div>
            </div>
            <div class="metric-card error">
                <div class="metric-label">Ошибок</div>
                <div class="metric-value">{metrics.failed_requests} ({metrics.error_rate:.1f}%)</div>
            </div>
            <div class="metric-card performance">
                <div class="metric-label">Avg Response Time</div>
                <div class="metric-value">{metrics.avg_response_time_ms:.0f} ms</div>
            </div>
            <div class="metric-card performance">
                <div class="metric-label">P95 Response Time</div>
                <div class="metric-value">{metrics.p95_response_time_ms:.0f} ms</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Throughput</div>
                <div class="metric-value">{metrics.requests_per_second:.1f} req/s</div>
            </div>
        </div>

        {self._render_config(test_config) if test_config else ''}

        <h2>Response Time</h2>
        <table>
            <tr>
                <th>Метрика</th>
                <th>Значение</th>
            </tr>
            <tr>
                <td>Минимальный</td>
                <td>{metrics.min_response_time_ms:.2f} ms</td>
            </tr>
            <tr>
                <td>Максимальный</td>
                <td>{metrics.max_response_time_ms:.2f} ms</td>
            </tr>
            <tr>
                <td>Средний</td>
                <td>{metrics.avg_response_time_ms:.2f} ms</td>
            </tr>
            <tr>
                <td>Медиана (P50)</td>
                <td>{metrics.median_response_time_ms:.2f} ms</td>
            </tr>
            <tr>
                <td>P95</td>
                <td>{metrics.p95_response_time_ms:.2f} ms</td>
            </tr>
            <tr>
                <td>P99</td>
                <td>{metrics.p99_response_time_ms:.2f} ms</td>
            </tr>
        </table>

        <h2>Графики</h2>

        {self._render_chart(chart_files.get('response_time'), 'Response Time во времени')}
        {self._render_chart(chart_files.get('throughput'), 'Throughput во времени')}
        {self._render_chart(chart_files.get('error_rate'), 'Error Rate во времени')}
        {self._render_chart(chart_files.get('rt_distribution'), 'Распределение Response Time')}
        {self._render_chart(chart_files.get('intent_distribution'), 'Распределение по интентам')}

    </div>
</body>
</html>
"""
        return html

    def _render_config(self, config: Dict) -> str:
        """Рендерит конфигурацию теста"""
        html = '<h2>Конфигурация теста</h2><div class="config">'
        for key, value in config.items():
            html += f"<strong>{key}:</strong> {value}<br>"
        html += '</div>'
        return html

    def _render_chart(self, chart_file: Optional[str], title: str) -> str:
        """Рендерит график"""
        if not chart_file:
            return ""

        return f"""
        <div class="chart">
            <h3>{title}</h3>
            <img src="charts/{chart_file}" alt="{title}">
        </div>
        """


# Пример использования
if __name__ == "__main__":
    from .collector import MetricsCollector
    import random

    # Создаём collector с тестовыми данными
    collector = MetricsCollector()

    for i in range(200):
        collector.record_message(
            user_id=i % 20,
            success=random.random() > 0.05,
            response_time_ms=random.uniform(300, 1200),
            intent=random.choice(["business", "product", "curious", "skeptic"]),
            segment=random.choice(["A", "B", "C", "D", "E"]),
            error="API Timeout" if random.random() < 0.05 else None,
        )
        time.sleep(0.01)  # Эмуляция задержки

    # Console Reporter
    console_reporter = ConsoleReporter(collector)
    console_reporter.print_header("Тест AI-Куратора", total_users=20, total_messages=200)
    console_reporter.print_summary(test_duration_sec=10.0)

    # HTML Reporter
    html_reporter = HTMLReporter(collector)
    html_reporter.generate_report(
        output_path="test_report.html",
        test_name="Тест AI-Куратора",
        test_config={
            "Пользователей": 20,
            "Сообщений": 200,
            "Длительность": "10 сек",
        }
    )
