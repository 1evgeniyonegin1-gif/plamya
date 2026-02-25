"""
Запуск тестов качества для NL International ботов.

Использование:
    python -m tests.quality.run --all
    python -m tests.quality.run --curator --limit 10
    python -m tests.quality.run --content --category series
    python -m tests.quality.run --all --report html

Дата: 03.02.2026
"""
import argparse
import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Добавляем корень проекта в path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def parse_args():
    """Парсинг аргументов командной строки"""
    parser = argparse.ArgumentParser(
        description="Testy kachestva NL International botov",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Primery:
  python -m tests.quality.run --limit 5              # Pervye 5 testov
  python -m tests.quality.run --curator --limit 10   # 10 testov kuratora
  python -m tests.quality.run --content --category series  # Tolko serii
  python -m tests.quality.run --all --report html    # Vse testy + HTML
        """
    )

    # Выбор бота
    parser.add_argument("--all", action="store_true", help="Run all tests (both bots)")
    parser.add_argument("--curator", action="store_true", help="Only AI-Curator")
    parser.add_argument("--content", action="store_true", help="Only Content-Manager")

    # Фильтры
    parser.add_argument("--limit", type=int, default=100, help="Max tests (default: 100)")
    parser.add_argument("--category", type=str, help="Category (objection, motivation, series, etc.)")

    # Вывод
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--report", choices=["text", "html"], default="text", help="Report format")
    parser.add_argument("--output", "-o", type=str, help="Output file")

    return parser.parse_args()


async def main():
    from loguru import logger
    from tests.quality.runners.quality_runner import QualityTestRunner, TestConfig
    from tests.quality.reports.dialog_report import DialogReportGenerator

    args = parse_args()

    # Настройка логирования
    logger.remove()
    if args.verbose:
        logger.add(sys.stderr, level="DEBUG")
    else:
        logger.add(sys.stderr, level="INFO", format="{message}")

    # Если ничего не выбрано — показать справку
    if not (args.all or args.curator or args.content):
        print("Usage: python -m tests.quality.run --all")
        print("       python -m tests.quality.run --curator --limit 10")
        print("       python -m tests.quality.run --content --category series")
        print("\nQuick start: python -m tests.quality.run --limit 5")
        return

    # Конфиг
    config = TestConfig(
        limit=args.limit,
        category=args.category,
        verbose=args.verbose
    )

    # Runner
    runner = QualityTestRunner()
    reporter = DialogReportGenerator()

    logger.info("=" * 60)
    logger.info("TESTY KACHESTVA NL INTERNATIONAL BOTOV")
    logger.info(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    logger.info("=" * 60)

    # Запуск тестов
    curator_results = []
    content_results = []

    if args.all or args.curator:
        logger.info("\nAI-CURATOR")
        logger.info("-" * 60)
        curator_results = await runner.run_curator_tests(config)

    if args.all or args.content:
        logger.info("\nCONTENT-MANAGER")
        logger.info("-" * 60)
        content_results = await runner.run_content_tests(config)

    # Генерация отчёта
    logger.info("\n" + "=" * 60)
    logger.info("GENERATING REPORT...")
    logger.info("=" * 60)

    report_parts = []

    if curator_results:
        report_parts.append(reporter.generate_curator_report(curator_results, verbose=args.verbose))

    if content_results:
        report_parts.append(reporter.generate_content_report(content_results, verbose=args.verbose))

    # Общий итог
    if curator_results or content_results:
        report_parts.append(reporter.generate_combined_report(curator_results, content_results))

    full_report = "\n".join(report_parts)

    # Сохранение в файл (всегда сохраняем)
    output_file = args.output or f"quality_test_results/report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if args.report == "html" or output_file.endswith('.html'):
        # HTML обёртка
        html_report = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Quality Report - NL International bots</title>
    <style>
        body {{ font-family: 'Consolas', monospace; background: #1e1e1e; color: #d4d4d4; padding: 20px; }}
        pre {{ white-space: pre-wrap; }}
    </style>
</head>
<body>
<pre>{full_report}</pre>
</body>
</html>"""
        output_path.write_text(html_report, encoding="utf-8")
    else:
        output_path.write_text(full_report, encoding="utf-8")

    logger.info(f"\nReport saved to: {output_path}")

    # Итоговая статистика
    total = len(curator_results) + len(content_results)
    passed = sum(1 for r in runner.all_results if r.verdict == "PASS")

    logger.info(f"\nDone: {total} tests, {passed} passed ({int(passed/total*100) if total else 0}%)")


if __name__ == "__main__":
    asyncio.run(main())
