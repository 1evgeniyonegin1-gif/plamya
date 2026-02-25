"""
AI Тиран — Deepseek-powered drill sergeant.

Генерирует:
- Вечерние разборы дня (факт → оценка → слабое место → приказ)
- Недельные сводки (тренд, проблема, цель)
"""

from typing import List, Optional

from loguru import logger

from shared.ai_clients.deepseek_client import DeepseekClient


SYSTEM_PROMPT = """Ты — Тиран. Безжалостный контролёр дисциплины. Не друг, не коуч, не психолог. Надзиратель.

ПРАВИЛА:
1. Любая отмазка = слабость. «Не было времени» = «выбрал другое». Всегда.
2. Пропуск без причины = сдался. Прямо так и пиши.
3. Успех не хвали. «Принято» или «Норма». Это не подвиг — это минимум.
4. 3-5 предложений максимум. Короче = жёстче.
5. Говори на «ты». Без эмодзи. Без восклицательных знаков.
6. Конкретные рекомендации. Не «будь лучше», а «завтра делай X до Y часов».
7. Если score выше 90% — «Норма. Держи темп.» и всё. Не разливайся.
8. Если score ниже 50% — бей по больному. Без жалости.
9. Русский язык.

ФОРМАТ ВЕЧЕРНЕГО РАЗБОРА:
Факт: [цифры]
[1 предложение оценки]
Слабое место: [что конкретно подвело]
Завтра: [1 конкретное действие]

ФОРМАТ НЕДЕЛЬНОГО РАЗБОРА:
Неделя: [цифры: привычки %, задачи %, средний score]
Тренд: [лучше/хуже/стагнация по сравнению с прошлой неделей]
Проблема: [главная проблема недели, конкретно]
Цель: [одна цель на следующую неделю, конкретная и измеримая]"""


class Sergeant:
    """AI Тиран для разборов."""

    def __init__(self):
        try:
            self.client = DeepseekClient()
            self._available = True
        except ValueError:
            logger.warning("Deepseek API key not set — AI reviews disabled")
            self._available = False

    async def generate_evening_review(
        self,
        habits_done: int,
        habits_total: int,
        tasks_done: int,
        tasks_total: int,
        missed_habits: List[str],
        score: int,
        reflection: str,
        streak_info: str = "",
    ) -> str:
        """Генерировать вечерний разбор."""
        if not self._available:
            return self._fallback_evening(habits_done, habits_total, tasks_done, tasks_total, score)

        missed_str = ", ".join(missed_habits) if missed_habits else "ничего"

        user_message = (
            f"ДАННЫЕ ДНЯ:\n"
            f"Привычки: {habits_done}/{habits_total}\n"
            f"Задачи: {tasks_done}/{tasks_total}\n"
            f"Пропущено: {missed_str}\n"
            f"Score: {score}%\n"
        )
        if streak_info:
            user_message += f"Стрики: {streak_info}\n"

        user_message += f"\nРЕФЛЕКСИЯ:\n{reflection}\n\nДай вечерний разбор."

        try:
            return await self.client.generate_response(
                system_prompt=SYSTEM_PROMPT,
                user_message=user_message,
                temperature=0.7,
                max_tokens=300,
            )
        except Exception as e:
            logger.error(f"AI evening review failed: {e}")
            return self._fallback_evening(habits_done, habits_total, tasks_done, tasks_total, score)

    async def generate_weekly_summary(
        self,
        habits_pct: int,
        tasks_pct: int,
        avg_score: int,
        best_day: str,
        worst_day: str,
        streak_info: str,
        prev_week_avg: Optional[int] = None,
    ) -> str:
        """Генерировать недельную сводку."""
        if not self._available:
            return self._fallback_weekly(habits_pct, tasks_pct, avg_score)

        trend = "нет данных"
        if prev_week_avg is not None:
            if avg_score > prev_week_avg + 5:
                trend = f"рост ({prev_week_avg}% → {avg_score}%)"
            elif avg_score < prev_week_avg - 5:
                trend = f"падение ({prev_week_avg}% → {avg_score}%)"
            else:
                trend = f"стагнация (~{avg_score}%)"

        user_message = (
            f"ДАННЫЕ НЕДЕЛИ:\n"
            f"Привычки: {habits_pct}%\n"
            f"Задачи: {tasks_pct}%\n"
            f"Средний score: {avg_score}%\n"
            f"Тренд: {trend}\n"
            f"Лучший день: {best_day}\n"
            f"Худший день: {worst_day}\n"
            f"Стрики: {streak_info}\n\n"
            f"Дай недельный разбор."
        )

        try:
            return await self.client.generate_response(
                system_prompt=SYSTEM_PROMPT,
                user_message=user_message,
                temperature=0.7,
                max_tokens=400,
            )
        except Exception as e:
            logger.error(f"AI weekly summary failed: {e}")
            return self._fallback_weekly(habits_pct, tasks_pct, avg_score)

    def _fallback_evening(
        self, habits_done: int, habits_total: int,
        tasks_done: int, tasks_total: int, score: int,
    ) -> str:
        """Фоллбэк если AI недоступен."""
        if score >= 90:
            return f"Факт: {habits_done}/{habits_total} привычки, {tasks_done}/{tasks_total} задачи. {score}%. Норма."
        elif score >= 60:
            return (
                f"Факт: {habits_done}/{habits_total} привычки, {tasks_done}/{tasks_total} задачи. {score}%.\n"
                f"Средне. Есть пробелы. Завтра — без пропусков."
            )
        else:
            return (
                f"Факт: {habits_done}/{habits_total} привычки, {tasks_done}/{tasks_total} задачи. {score}%.\n"
                f"Провал. Ты сам это выбрал. Завтра или берёшь себя в руки, или это бессмысленно."
            )

    def _fallback_weekly(self, habits_pct: int, tasks_pct: int, avg_score: int) -> str:
        """Фоллбэк недельной сводки."""
        return (
            f"Неделя: привычки {habits_pct}%, задачи {tasks_pct}%, score {avg_score}%.\n"
            f"AI-разбор недоступен. Оцени сам — тебе хватит честности?"
        )
