"""Управление JSON состоянием Чаппи."""

import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

from chappie_engine.config import (
    STATE_FILE,
    KNOWLEDGE_FILE,
    GOALS_FILE,
    PROBLEMS_FILE,
    INBOX_FILE,
    STATUS_FILE,
    UTC_OFFSET,
)

logger = logging.getLogger("chappie.state")

MSK = timezone(timedelta(hours=UTC_OFFSET))


def _now_msk() -> str:
    return datetime.now(MSK).strftime("%Y-%m-%d %H:%M")


def _today() -> str:
    return datetime.now(MSK).strftime("%Y-%m-%d")


class StateManager:
    """Чтение/запись JSON файлов состояния Чаппи."""

    # --- STATE ---

    def load_state(self) -> dict:
        return self._load_json(STATE_FILE, self._default_state())

    def save_state(self, data: dict):
        self._save_json(STATE_FILE, data)

    def _default_state(self) -> dict:
        return {
            "phase": "learning",
            "day": 1,
            "started_at": _today(),
            "channels": {},
            "daily_actions": {},
            "total_actions": {},
            "prospects": [],
            "content_memory": [],
            "errors_today": 0,
            "banned_until": None,
        }

    # --- KNOWLEDGE ---

    def load_knowledge(self) -> dict:
        return self._load_json(KNOWLEDGE_FILE, self._default_knowledge())

    def save_knowledge(self, data: dict):
        self._save_json(KNOWLEDGE_FILE, data)

    def _default_knowledge(self) -> dict:
        return {
            "products_studied": [],
            "business_model_understood": False,
            "qualifications_understood": False,
            "competitor_insights": [],
            "learned_at": None,
        }

    # --- GOALS ---

    def load_goals(self) -> dict:
        return self._load_json(GOALS_FILE, self._default_goals())

    def save_goals(self, data: dict):
        self._save_json(GOALS_FILE, data)

    def _default_goals(self) -> dict:
        return {
            "current_goal": "Изучить продукты и бизнес-модель NL",
            "qualification_target": "M1",
            "milestones": [
                {"name": "Изучить продукты", "done": False},
                {"name": "Создать первый канал", "done": False},
                {"name": "Опубликовать 10 постов", "done": False},
                {"name": "Написать первый DM", "done": False},
                {"name": "Получить первый ответ на DM", "done": False},
            ],
        }

    # --- PROBLEMS ---

    def load_problems(self) -> dict:
        return self._load_json(PROBLEMS_FILE, {"problems": []})

    def save_problems(self, data: dict):
        self._save_json(PROBLEMS_FILE, data)

    def add_problem(self, description: str, why_needed: str, research: str = "") -> int:
        """Добавить проблему в журнал. Возвращает ID проблемы."""
        data = self.load_problems()
        problem_id = len(data["problems"]) + 1
        data["problems"].append({
            "id": problem_id,
            "discovered_at": _today(),
            "description": description,
            "why_needed": why_needed,
            "research": research,
            "status": "new",
            "escalated_at": None,
            "resolved": False,
        })
        self.save_problems(data)
        logger.info(f"Проблема #{problem_id}: {description}")
        return problem_id

    # --- INBOX ---

    def write_to_inbox(self, header: str, content: str):
        """Добавить сообщение в INBOX.md."""
        timestamp = _now_msk()
        entry = f"\n## [{timestamp}] {header}\n{content}\n\n---\n"

        inbox_path = INBOX_FILE
        existing = ""
        if inbox_path.exists():
            existing = inbox_path.read_text(encoding="utf-8")

        # Вставляем в начало (после заголовка если есть)
        if existing.startswith("# "):
            first_newline = existing.index("\n") + 1
            new_content = existing[:first_newline] + entry + existing[first_newline:]
        else:
            new_content = entry + existing

        inbox_path.write_text(new_content, encoding="utf-8")
        logger.info(f"INBOX: {header}")

    # --- STATUS ---

    def update_status(self, task: str):
        """Обновить строку ЧАППИ в STATUS.md."""
        timestamp = _now_msk()
        status_path = STATUS_FILE

        if not status_path.exists():
            return

        content = status_path.read_text(encoding="utf-8")
        lines = content.split("\n")
        new_lines = []
        found = False

        for line in lines:
            if "ЧАППИ" in line:
                new_lines.append(
                    f"| ЧАППИ | active | {timestamp} | {task} |"
                )
                found = True
            else:
                new_lines.append(line)

        if not found:
            # Добавить строку перед последним пустым
            new_lines.insert(-1, f"| ЧАППИ | active | {timestamp} | {task} |")

        status_path.write_text("\n".join(new_lines), encoding="utf-8")

    # --- JSON helpers ---

    def _load_json(self, path: Path, default: dict) -> dict:
        if not path.exists():
            self._save_json(path, default)
            return default.copy()
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, ValueError):
            logger.warning(f"Повреждён {path.name}, создаю заново")
            self._save_json(path, default)
            return default.copy()

    def _save_json(self, path: Path, data: dict):
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
