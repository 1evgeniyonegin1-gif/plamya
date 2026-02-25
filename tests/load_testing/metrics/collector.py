"""
Metrics Collector для нагрузочного тестирования

Собирает метрики в реальном времени:
- Response time (мин, макс, средний, p50, p95, p99)
- Throughput (requests/sec)
- Error rate
- Распределение по интентам, сегментам
- Экспорт в CSV
"""

import time
import csv
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path


@dataclass
class RequestMetric:
    """Метрика одного запроса"""
    timestamp: float
    user_id: int
    request_type: str  # "message" | "generate_post"
    success: bool
    response_time_ms: float
    error: Optional[str] = None
    intent: Optional[str] = None
    segment: Optional[str] = None
    post_type: Optional[str] = None


@dataclass
class AggregatedMetrics:
    """Агрегированные метрики за период"""
    # Временной период
    start_time: float
    end_time: float
    duration_sec: float

    # Основные метрики
    total_requests: int
    successful_requests: int
    failed_requests: int
    error_rate: float  # Процент ошибок

    # Response time
    min_response_time_ms: float
    max_response_time_ms: float
    avg_response_time_ms: float
    median_response_time_ms: float
    p95_response_time_ms: float
    p99_response_time_ms: float

    # Throughput
    requests_per_second: float

    # Распределение
    intent_distribution: Dict[str, int] = field(default_factory=dict)
    segment_distribution: Dict[str, int] = field(default_factory=dict)
    error_distribution: Dict[str, int] = field(default_factory=dict)


class MetricsCollector:
    """
    Сборщик метрик для нагрузочного тестирования

    Собирает метрики в реальном времени и позволяет экспортировать в CSV
    """

    def __init__(self):
        self.metrics: List[RequestMetric] = []
        self.start_time = time.time()

    def record_request(
        self,
        user_id: int,
        request_type: str,
        success: bool,
        response_time_ms: float,
        error: Optional[str] = None,
        intent: Optional[str] = None,
        segment: Optional[str] = None,
        post_type: Optional[str] = None,
    ):
        """
        Записывает метрику запроса

        Args:
            user_id: ID пользователя
            request_type: Тип запроса ("message" или "generate_post")
            success: Успешность запроса
            response_time_ms: Время ответа в мс
            error: Текст ошибки (если была)
            intent: Intent пользователя
            segment: Сегмент пользователя
            post_type: Тип поста (для Content Manager)
        """
        metric = RequestMetric(
            timestamp=time.time(),
            user_id=user_id,
            request_type=request_type,
            success=success,
            response_time_ms=response_time_ms,
            error=error,
            intent=intent,
            segment=segment,
            post_type=post_type,
        )
        self.metrics.append(metric)

    def record_message(
        self,
        user_id: int,
        success: bool,
        response_time_ms: float,
        error: Optional[str] = None,
        intent: Optional[str] = None,
        segment: Optional[str] = None,
    ):
        """Записывает метрику отправки сообщения (AI-Куратор)"""
        self.record_request(
            user_id=user_id,
            request_type="message",
            success=success,
            response_time_ms=response_time_ms,
            error=error,
            intent=intent,
            segment=segment,
        )

    def record_post_generation(
        self,
        user_id: int,
        success: bool,
        response_time_ms: float,
        post_type: str,
        error: Optional[str] = None,
    ):
        """Записывает метрику генерации поста (Контент-Менеджер)"""
        self.record_request(
            user_id=user_id,
            request_type="generate_post",
            success=success,
            response_time_ms=response_time_ms,
            error=error,
            post_type=post_type,
        )

    def get_aggregated_metrics(
        self,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None
    ) -> AggregatedMetrics:
        """
        Возвращает агрегированные метрики за период

        Args:
            start_time: Начало периода (timestamp). Если None - с начала теста
            end_time: Конец периода (timestamp). Если None - до текущего момента

        Returns:
            AggregatedMetrics с агрегированными данными
        """
        # Фильтруем метрики по времени
        filtered_metrics = self.metrics

        if start_time:
            filtered_metrics = [m for m in filtered_metrics if m.timestamp >= start_time]

        if end_time:
            filtered_metrics = [m for m in filtered_metrics if m.timestamp <= end_time]

        if not filtered_metrics:
            # Возвращаем пустые метрики
            return AggregatedMetrics(
                start_time=start_time or self.start_time,
                end_time=end_time or time.time(),
                duration_sec=0,
                total_requests=0,
                successful_requests=0,
                failed_requests=0,
                error_rate=0,
                min_response_time_ms=0,
                max_response_time_ms=0,
                avg_response_time_ms=0,
                median_response_time_ms=0,
                p95_response_time_ms=0,
                p99_response_time_ms=0,
                requests_per_second=0,
            )

        # Временной период
        actual_start = start_time or filtered_metrics[0].timestamp
        actual_end = end_time or filtered_metrics[-1].timestamp
        duration = max(actual_end - actual_start, 0.001)  # Избегаем деления на 0

        # Основные метрики
        total = len(filtered_metrics)
        successful = sum(1 for m in filtered_metrics if m.success)
        failed = total - successful
        error_rate = (failed / total * 100) if total > 0 else 0

        # Response times (только успешные запросы)
        response_times = [m.response_time_ms for m in filtered_metrics if m.success]

        if response_times:
            response_times_sorted = sorted(response_times)
            min_rt = min(response_times)
            max_rt = max(response_times)
            avg_rt = sum(response_times) / len(response_times)
            median_rt = self._percentile(response_times_sorted, 50)
            p95_rt = self._percentile(response_times_sorted, 95)
            p99_rt = self._percentile(response_times_sorted, 99)
        else:
            min_rt = max_rt = avg_rt = median_rt = p95_rt = p99_rt = 0

        # Throughput
        rps = total / duration

        # Распределение по интентам
        intent_dist = {}
        for m in filtered_metrics:
            if m.intent:
                intent_dist[m.intent] = intent_dist.get(m.intent, 0) + 1

        # Распределение по сегментам
        segment_dist = {}
        for m in filtered_metrics:
            if m.segment:
                segment_dist[m.segment] = segment_dist.get(m.segment, 0) + 1

        # Распределение ошибок
        error_dist = {}
        for m in filtered_metrics:
            if m.error:
                # Берём первые 50 символов ошибки для группировки
                error_key = m.error[:50]
                error_dist[error_key] = error_dist.get(error_key, 0) + 1

        return AggregatedMetrics(
            start_time=actual_start,
            end_time=actual_end,
            duration_sec=duration,
            total_requests=total,
            successful_requests=successful,
            failed_requests=failed,
            error_rate=error_rate,
            min_response_time_ms=min_rt,
            max_response_time_ms=max_rt,
            avg_response_time_ms=avg_rt,
            median_response_time_ms=median_rt,
            p95_response_time_ms=p95_rt,
            p99_response_time_ms=p99_rt,
            requests_per_second=rps,
            intent_distribution=intent_dist,
            segment_distribution=segment_dist,
            error_distribution=error_dist,
        )

    def get_metrics_by_time_window(
        self,
        window_sec: float = 10.0
    ) -> List[AggregatedMetrics]:
        """
        Возвращает метрики разбитые по временным окнам

        Args:
            window_sec: Размер окна в секундах (по умолчанию 10 сек)

        Returns:
            Список AggregatedMetrics для каждого временного окна
        """
        if not self.metrics:
            return []

        first_metric = self.metrics[0]
        last_metric = self.metrics[-1]

        start = first_metric.timestamp
        end = last_metric.timestamp
        duration = end - start

        # Количество окон
        num_windows = int(duration / window_sec) + 1

        windows = []
        for i in range(num_windows):
            window_start = start + (i * window_sec)
            window_end = window_start + window_sec

            metrics = self.get_aggregated_metrics(
                start_time=window_start,
                end_time=window_end
            )

            if metrics.total_requests > 0:
                windows.append(metrics)

        return windows

    def export_to_csv(self, file_path: str):
        """
        Экспортирует все метрики в CSV файл

        Args:
            file_path: Путь к файлу для экспорта
        """
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            if not self.metrics:
                return

            fieldnames = [
                'timestamp',
                'datetime',
                'user_id',
                'request_type',
                'success',
                'response_time_ms',
                'error',
                'intent',
                'segment',
                'post_type',
            ]

            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for metric in self.metrics:
                row = asdict(metric)
                # Добавляем человекочитаемую дату
                row['datetime'] = datetime.fromtimestamp(metric.timestamp).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                writer.writerow(row)

        print(f"Метрики экспортированы в {file_path}")

    def export_aggregated_to_csv(self, file_path: str, window_sec: float = 10.0):
        """
        Экспортирует агрегированные метрики в CSV (по временным окнам)

        Args:
            file_path: Путь к файлу для экспорта
            window_sec: Размер временного окна в секундах
        """
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)

        windows = self.get_metrics_by_time_window(window_sec=window_sec)

        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            if not windows:
                return

            fieldnames = [
                'window_start',
                'window_end',
                'duration_sec',
                'total_requests',
                'successful_requests',
                'failed_requests',
                'error_rate',
                'min_response_time_ms',
                'max_response_time_ms',
                'avg_response_time_ms',
                'median_response_time_ms',
                'p95_response_time_ms',
                'p99_response_time_ms',
                'requests_per_second',
            ]

            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for window in windows:
                row = {
                    'window_start': datetime.fromtimestamp(window.start_time).strftime('%Y-%m-%d %H:%M:%S'),
                    'window_end': datetime.fromtimestamp(window.end_time).strftime('%Y-%m-%d %H:%M:%S'),
                    'duration_sec': round(window.duration_sec, 2),
                    'total_requests': window.total_requests,
                    'successful_requests': window.successful_requests,
                    'failed_requests': window.failed_requests,
                    'error_rate': round(window.error_rate, 2),
                    'min_response_time_ms': round(window.min_response_time_ms, 2),
                    'max_response_time_ms': round(window.max_response_time_ms, 2),
                    'avg_response_time_ms': round(window.avg_response_time_ms, 2),
                    'median_response_time_ms': round(window.median_response_time_ms, 2),
                    'p95_response_time_ms': round(window.p95_response_time_ms, 2),
                    'p99_response_time_ms': round(window.p99_response_time_ms, 2),
                    'requests_per_second': round(window.requests_per_second, 2),
                }
                writer.writerow(row)

        print(f"Агрегированные метрики экспортированы в {file_path}")

    def reset(self):
        """Сбрасывает все собранные метрики"""
        self.metrics = []
        self.start_time = time.time()

    def _percentile(self, sorted_values: List[float], percentile: int) -> float:
        """
        Вычисляет перцентиль

        Args:
            sorted_values: Отсортированный список значений
            percentile: Перцентиль (0-100)

        Returns:
            Значение перцентиля
        """
        if not sorted_values:
            return 0

        index = int(len(sorted_values) * (percentile / 100))
        index = min(index, len(sorted_values) - 1)

        return sorted_values[index]

    def get_summary(self) -> Dict[str, Any]:
        """
        Возвращает краткую сводку метрик

        Returns:
            Словарь с основными метриками
        """
        metrics = self.get_aggregated_metrics()

        # Подсчитываем уникальных пользователей
        unique_users = len(set(m.user_id for m in self.metrics if m.user_id))

        return {
            "total_users": unique_users,
            "total_requests": metrics.total_requests,
            "successful_requests": metrics.successful_requests,
            "failed_requests": metrics.failed_requests,
            "error_rate": round(metrics.error_rate, 2),  # В процентах (0-100)
            "avg_response_time_ms": round(metrics.avg_response_time_ms, 2),
            "median_response_time_ms": round(metrics.median_response_time_ms, 2),
            "p95_response_time_ms": round(metrics.p95_response_time_ms, 2),
            "p99_response_time_ms": round(metrics.p99_response_time_ms, 2),
            "requests_per_second": round(metrics.requests_per_second, 2),
            "total_duration_sec": round(metrics.duration_sec, 2),
        }


# Пример использования
if __name__ == "__main__":
    collector = MetricsCollector()

    # Симулируем запросы
    import random

    for i in range(100):
        collector.record_message(
            user_id=i % 10,
            success=random.random() > 0.05,  # 95% success rate
            response_time_ms=random.uniform(300, 800),
            intent=random.choice(["business", "product", "curious", "skeptic"]),
            segment=random.choice(["A", "B", "C", "D", "E"]),
            error="API Error" if random.random() < 0.05 else None,
        )

    # Выводим сводку
    print("Сводка:")
    print(collector.get_summary())

    # Агрегированные метрики
    print("\nАгрегированные метрики:")
    metrics = collector.get_aggregated_metrics()
    print(f"  Total Requests: {metrics.total_requests}")
    print(f"  Success Rate: {100 - metrics.error_rate:.1f}%")
    print(f"  Avg Response Time: {metrics.avg_response_time_ms:.2f}ms")
    print(f"  P95 Response Time: {metrics.p95_response_time_ms:.2f}ms")
    print(f"  Throughput: {metrics.requests_per_second:.2f} req/sec")

    # Экспорт в CSV
    collector.export_to_csv("test_metrics.csv")
    collector.export_aggregated_to_csv("test_metrics_aggregated.csv")
