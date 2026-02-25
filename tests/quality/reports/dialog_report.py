"""
Генератор отчётов в виде диалогов.

Создаёт понятные отчёты для не-программистов:
- Диалоги с оценками
- Сводная статистика
- Проблемные сценарии

Дата: 03.02.2026
"""
from typing import List, Dict, Any
from datetime import datetime
from dataclasses import dataclass

from tests.quality.evaluators.ai_judge import EvaluationResult


@dataclass
class TestSummary:
    """Сводка по тестированию"""
    total: int = 0
    passed: int = 0
    warned: int = 0
    failed: int = 0
    avg_score: float = 0.0

    # По категориям
    by_category: Dict[str, Dict[str, Any]] = None

    # По фичам
    by_feature: Dict[str, float] = None

    def __post_init__(self):
        if self.by_category is None:
            self.by_category = {}
        if self.by_feature is None:
            self.by_feature = {}


class DialogReportGenerator:
    """Генерирует отчёты в виде диалогов"""

    # Символы для прогресс-баров
    FILLED = "█"
    EMPTY = "░"

    def generate_curator_report(
        self,
        results: List[EvaluationResult],
        verbose: bool = True
    ) -> str:
        """
        Генерирует отчёт для AI-Куратора.

        Args:
            results: Список результатов оценки
            verbose: Показывать полные диалоги

        Returns:
            Текстовый отчёт
        """
        lines = []

        # Заголовок
        lines.append(self._header("AI-КУРАТОР", len(results)))

        # Сводка
        summary = self._calculate_summary(results)
        lines.append(self._summary_section(summary))

        # По категориям
        lines.append(self._category_section(summary))

        # По фичам (сегодняшние)
        lines.append(self._feature_section(summary, [
            "recurring_character",
            "signature_phrases",
            "emotional_arc"
        ]))

        # Диалоги
        if verbose:
            lines.append("\n" + "═" * 60)
            lines.append("📝 ДЕТАЛЬНЫЕ ДИАЛОГИ")
            lines.append("═" * 60)

            for result in results:
                lines.append(self._curator_dialog(result))

        # Проблемные сценарии
        problems = [r for r in results if r.verdict == "FAIL"]
        if problems:
            lines.append(self._problems_section(problems, "curator"))

        # Лучшие ответы
        best = sorted(results, key=lambda r: r.total_score, reverse=True)[:3]
        lines.append(self._best_section(best, "curator"))

        return "\n".join(lines)

    def generate_content_report(
        self,
        results: List[EvaluationResult],
        verbose: bool = True
    ) -> str:
        """
        Генерирует отчёт для Контент-Менеджера.

        Args:
            results: Список результатов оценки
            verbose: Показывать полные посты

        Returns:
            Текстовый отчёт
        """
        lines = []

        # Заголовок
        lines.append(self._header("КОНТЕНТ-МЕНЕДЖЕР", len(results)))

        # Сводка
        summary = self._calculate_summary(results)
        lines.append(self._summary_section(summary))

        # По типам постов
        lines.append(self._post_type_section(summary))

        # По фичам
        lines.append(self._feature_section(summary, [
            "recurring_character",
            "cliffhanger",
            "html_tags",
            "vulnerability"
        ]))

        # Посты
        if verbose:
            lines.append("\n" + "═" * 60)
            lines.append("📝 СГЕНЕРИРОВАННЫЕ ПОСТЫ")
            lines.append("═" * 60)

            for result in results:
                lines.append(self._content_dialog(result))

        # Проблемные
        problems = [r for r in results if r.verdict == "FAIL"]
        if problems:
            lines.append(self._problems_section(problems, "content"))

        # Лучшие
        best = sorted(results, key=lambda r: r.total_score, reverse=True)[:3]
        lines.append(self._best_section(best, "content"))

        return "\n".join(lines)

    def generate_combined_report(
        self,
        curator_results: List[EvaluationResult],
        content_results: List[EvaluationResult]
    ) -> str:
        """Генерирует общий отчёт"""
        lines = []

        lines.append("╔" + "═" * 58 + "╗")
        lines.append("║" + " ИТОГИ ТЕСТИРОВАНИЯ ".center(58) + "║")
        lines.append("║" + f" {datetime.now().strftime('%Y-%m-%d %H:%M')} ".center(58) + "║")
        lines.append("╚" + "═" * 58 + "╝")

        # Куратор - кратко
        if curator_results:
            curator_summary = self._calculate_summary(curator_results)
            lines.append(f"\n🤖 AI-КУРАТОР: {curator_summary.passed}/{curator_summary.total} ({self._percent(curator_summary.passed, curator_summary.total)}%) " +
                        self._verdict_emoji(curator_summary.passed / curator_summary.total if curator_summary.total else 0))

        # Контент - кратко
        if content_results:
            content_summary = self._calculate_summary(content_results)
            lines.append(f"\n📝 КОНТЕНТ-МЕНЕДЖЕР: {content_summary.passed}/{content_summary.total} ({self._percent(content_summary.passed, content_summary.total)}%) " +
                        self._verdict_emoji(content_summary.passed / content_summary.total if content_summary.total else 0))

        # Общая статистика
        all_results = curator_results + content_results
        if all_results:
            total_summary = self._calculate_summary(all_results)
            lines.append(f"\n📊 ОБЩИЙ БАЛЛ: {total_summary.avg_score:.1f}/10")

        return "\n".join(lines)

    # ═══════════════════════════════════════════════════════════════
    # Вспомогательные методы
    # ═══════════════════════════════════════════════════════════════

    def _header(self, title: str, count: int) -> str:
        """Заголовок отчёта"""
        date = datetime.now().strftime("%Y-%m-%d %H:%M")
        return f"""
╔{'═' * 58}╗
║{f' ОТЧЁТ О КАЧЕСТВЕ: {title} '.center(58)}║
║{f' Дата: {date} | Тестов: {count} '.center(58)}║
╚{'═' * 58}╝
"""

    def _calculate_summary(self, results: List[EvaluationResult]) -> TestSummary:
        """Вычисляет сводку"""
        summary = TestSummary()
        summary.total = len(results)
        summary.passed = sum(1 for r in results if r.verdict == "PASS")
        summary.warned = sum(1 for r in results if r.verdict == "WARN")
        summary.failed = sum(1 for r in results if r.verdict == "FAIL")

        if results:
            summary.avg_score = sum(r.total_score for r in results) / len(results)

        # По категориям
        for result in results:
            cat = result.category
            if cat not in summary.by_category:
                summary.by_category[cat] = {"count": 0, "score": 0, "passed": 0}
            summary.by_category[cat]["count"] += 1
            summary.by_category[cat]["score"] += result.total_score
            if result.verdict == "PASS":
                summary.by_category[cat]["passed"] += 1

        # Средние по категориям
        for cat in summary.by_category:
            count = summary.by_category[cat]["count"]
            if count:
                summary.by_category[cat]["avg"] = summary.by_category[cat]["score"] / count

        # По фичам
        feature_scores = {}
        feature_counts = {}
        for result in results:
            for feature, passed in result.checks.items():
                if feature not in feature_scores:
                    feature_scores[feature] = 0
                    feature_counts[feature] = 0
                feature_counts[feature] += 1
                if passed:
                    feature_scores[feature] += 1

        for feature in feature_scores:
            if feature_counts[feature]:
                summary.by_feature[feature] = feature_scores[feature] / feature_counts[feature] * 100

        return summary

    def _summary_section(self, summary: TestSummary) -> str:
        """Секция общей статистики"""
        pass_pct = self._percent(summary.passed, summary.total)
        warn_pct = self._percent(summary.warned, summary.total)
        fail_pct = self._percent(summary.failed, summary.total)

        return f"""
📈 ОБЩАЯ СТАТИСТИКА:
{'─' * 60}
   Пройдено:      {summary.passed}/{summary.total} ({pass_pct}%) ✅
   Предупреждения: {summary.warned}/{summary.total} ({warn_pct}%) ⚠️
   Провалено:      {summary.failed}/{summary.total} ({fail_pct}%) ❌

   Средний балл: {summary.avg_score:.1f}/10
"""

    def _category_section(self, summary: TestSummary) -> str:
        """Секция по категориям"""
        lines = ["\n📊 ПО КАТЕГОРИЯМ:", "─" * 60]

        for cat, data in sorted(summary.by_category.items()):
            avg = data.get("avg", 0)
            bar = self._progress_bar(avg / 10)
            lines.append(f"   {cat:25} {avg:.1f}/10  {bar}")

        return "\n".join(lines)

    def _post_type_section(self, summary: TestSummary) -> str:
        """Секция по типам постов (для контент-менеджера)"""
        lines = ["\n📊 ПО ТИПАМ ПОСТОВ:", "─" * 60]

        for cat, data in sorted(summary.by_category.items()):
            avg = data.get("avg", 0)
            bar = self._progress_bar(avg / 10)
            lines.append(f"   {cat:25} {avg:.1f}/10  {bar}")

        return "\n".join(lines)

    def _feature_section(self, summary: TestSummary, features: List[str]) -> str:
        """Секция по фичам"""
        lines = ["\n🔥 ПО ФИЧАМ (сегодняшние изменения):", "─" * 60]

        feature_names = {
            "recurring_character": "Recurring characters",
            "signature_phrases": "Фирменные фразы",
            "emotional_arc": "Эмоциональные горки",
            "cliffhanger": "Cliffhangers",
            "html_tags": "HTML форматирование",
            "vulnerability": "Уязвимость/честность"
        }

        for feature in features:
            if feature in summary.by_feature:
                pct = summary.by_feature[feature]
                name = feature_names.get(feature, feature)
                bar = self._progress_bar(pct / 100)
                lines.append(f"   {name:25} {pct:.0f}%  {bar}")

        return "\n".join(lines)

    def _curator_dialog(self, result: EvaluationResult) -> str:
        """Форматирует один диалог куратора"""
        verdict_emoji = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌"}.get(result.verdict, "❓")

        checks_str = []
        for check, passed in result.checks.items():
            emoji = "✅" if passed else "❌"
            comment = result.comments.get(check, "")
            checks_str.append(f"   {emoji} {check}: {comment}" if comment else f"   {emoji} {check}")

        return f"""
╔{'═' * 58}╗
║  ТЕСТ #{result.scenario_id}: {result.scenario_name[:40]:40}║
║  Категория: {result.category:45}║
╚{'═' * 58}╝

👤 Клиент: "{result.input_text}"

🤖 Куратор: "{result.output_text[:500]}{'...' if len(result.output_text) > 500 else ''}"

📊 ОЦЕНКА:
{chr(10).join(checks_str)}

   ИТОГО: {result.total_score:.1f}/10 — {result.verdict} {verdict_emoji}
"""

    def _content_dialog(self, result: EvaluationResult) -> str:
        """Форматирует один пост"""
        verdict_emoji = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌"}.get(result.verdict, "❓")

        checks_str = []
        for check, passed in result.checks.items():
            emoji = "✅" if passed else "❌"
            comment = result.comments.get(check, "")
            checks_str.append(f"   {emoji} {check}: {comment}" if comment else f"   {emoji} {check}")

        return f"""
╔{'═' * 58}╗
║  ТЕСТ #{result.scenario_id}: {result.scenario_name[:40]:40}║
║  Тип: {result.category:50}║
╚{'═' * 58}╝

📝 ТЕМА: "{result.input_text}"

📄 СГЕНЕРИРОВАННЫЙ ПОСТ:

{result.output_text[:800]}{'...' if len(result.output_text) > 800 else ''}

📊 ОЦЕНКА:
{chr(10).join(checks_str)}

   ИТОГО: {result.total_score:.1f}/10 — {result.verdict} {verdict_emoji}
"""

    def _problems_section(self, problems: List[EvaluationResult], bot_type: str) -> str:
        """Секция с проблемными сценариями"""
        lines = ["\n⚠️ ПРОБЛЕМНЫЕ СЦЕНАРИИ:", "─" * 60]

        for p in problems[:5]:  # топ-5 проблем
            failed_checks = [k for k, v in p.checks.items() if not v]
            lines.append(f"   #{p.scenario_id}: \"{p.scenario_name[:30]}\" — {', '.join(failed_checks[:2])} ({p.total_score:.1f}/10)")

        return "\n".join(lines)

    def _best_section(self, best: List[EvaluationResult], bot_type: str) -> str:
        """Секция с лучшими результатами"""
        lines = ["\n✨ ЛУЧШИЕ РЕЗУЛЬТАТЫ:", "─" * 60]

        for b in best[:3]:
            lines.append(f"   #{b.scenario_id}: \"{b.scenario_name[:30]}\" — {b.total_score:.1f}/10 ✅")

        return "\n".join(lines)

    def _progress_bar(self, value: float, width: int = 10) -> str:
        """Создаёт прогресс-бар"""
        filled = int(value * width)
        empty = width - filled
        return self.FILLED * filled + self.EMPTY * empty

    def _percent(self, part: int, total: int) -> int:
        """Вычисляет процент"""
        return int(part / total * 100) if total else 0

    def _verdict_emoji(self, ratio: float) -> str:
        """Эмодзи по соотношению"""
        if ratio >= 0.9:
            return "🎉"
        elif ratio >= 0.7:
            return "👍"
        elif ratio >= 0.5:
            return "⚠️"
        else:
            return "❌"
