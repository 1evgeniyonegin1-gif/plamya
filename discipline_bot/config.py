"""
Discipline Bot — константы, сообщения эскалации, расписание.
"""

from datetime import timedelta

# ═══════════ ADMIN ═══════════
ADMIN_TELEGRAM_ID = 756877849

# ═══════════ ЭСКАЛАЦИЯ ═══════════
# Задержки между уровнями эскалации
ESCALATION_DELAYS = [
    timedelta(minutes=5),   # Level 0: прямое
    timedelta(minutes=10),  # Level 1: давление
    timedelta(minutes=20),  # Level 2: констатация провала
]

MAX_ESCALATION_LEVEL = 2

# ═══════════ УТРЕННИЙ ПРОТОКОЛ ═══════════
MORNING_PING = "Подъём. Ответь «встал»."

MORNING_ESCALATION = [
    "Ты ещё лежишь. Каждая минута — слабость.",
    "Ты вчера сам это выбрал. Сам решил быть дисциплинированным. А сейчас лежишь.",
    "Всё. День провален. Даже не начавшись.",
]

MORNING_CONFIRMED = (
    "{response_time} минут. {verdict}\n\n"
    "Чеклист:\n{checklist}\n\n"
    "Ответь номером когда сделал."
)

MORNING_VERDICTS = {
    "fast": "Норма.",       # < 3 min
    "ok": "Принято.",       # 3-10 min
    "slow": "Медленно.",    # 10-20 min
    "bad": "Позор.",        # 20-30 min
}

# ═══════════ ПРИВЫЧКИ ═══════════
HABIT_DONE = "{emoji} {name} — принято. Streak: {streak}. Дальше."
HABIT_DONE_RECORD = "{emoji} {name} — принято. Streak: {streak} (рекорд). Дальше."
HABIT_ALL_DONE = "Все привычки закрыты. Норма."

HABIT_WINDOW_REMINDER = (
    "{emoji} {name} — {minutes_left} минут осталось. "
    "Streak {streak} дней. Ты правда хочешь его потерять?"
)

HABIT_WINDOW_EXPIRED = (
    "{emoji} {name} — окно закрыто. Streak обнулён. "
    "Был {old_streak}. Теперь 0."
)

# Алиасы для текстовых команд
HABIT_ALIASES = {
    "медитация": "Медитация",
    "меда": "Медитация",
    "душ": "Холодный душ",
    "холодный": "Холодный душ",
    "планёрка": "Планёрка",
    "планерка": "Планёрка",
    "тренировка": "Тренировка",
    "трен": "Тренировка",
    "спорт": "Тренировка",
}

# ═══════════ РАБОЧИЙ ПЛАН ═══════════
PLAN_EMPTY = "План на сегодня — пусто. Напиши задачи, каждая с новой строки."
PLAN_SHOW = "План на сегодня:\n{tasks}\n\nОтветь «з1», «з2» и т.д. когда закроешь."
PLAN_ACCEPTED = "План принят:\n{tasks}\n\nОтветь «з1», «з2» и т.д. когда закроешь."
PLAN_TASK_DONE = "Задача {number} закрыта. {done}/{total}."
PLAN_ALL_DONE = "Все задачи закрыты. Норма."
PLAN_REMINDER = (
    "{time}. {done} из {total} задач закрыта. "
    "Это не норма. Закрывай."
)

# ═══════════ ВЕЧЕРНИЙ РАЗБОР ═══════════
EVENING_START = (
    "Разбор дня.\n\n"
    "Привычки: {habits_done}/{habits_total}\n"
    "Задачи: {tasks_done}/{tasks_total}\n"
    "{missed_line}"
    "Score: {score}%\n\n"
    "Что скажешь? Напиши."
)

EVENING_TOMORROW_PLAN = "План на завтра. Напиши 3-5 задач."
EVENING_DONE = "Принято. Отбой. Завтра в {morning_time}."
EVENING_SKIPPED = "Без рефлексии. Принято.\n\nПлан на завтра. Напиши 3-5 задач."

# ═══════════ СТАТИСТИКА ═══════════
STATS_TEMPLATE = (
    "Статистика:\n\n"
    "{habits_stats}\n"
    "Задачи сегодня: {tasks_done}/{tasks_total}\n"
    "Средний score за неделю: {week_avg}%"
)

# ═══════════ КОМАНДЫ-СТОП ═══════════
UNKNOWN_COMMAND = "Не понял. Доступно: номер привычки, «план», «стат», «привычки», «неделя»."
