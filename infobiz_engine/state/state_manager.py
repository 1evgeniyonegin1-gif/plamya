"""Управление JSON состоянием ПРОДЮСЕРА."""

import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

from infobiz_engine.config import (
    STATE_FILE,
    NICHES_FILE,
    PRODUCTS_FILE,
    PIPELINE_FILE,
    INBOX_FILE,
    STATUS_FILE,
    UTC_OFFSET,
)

logger = logging.getLogger("producer.state")

MSK = timezone(timedelta(hours=UTC_OFFSET))


def _now_msk() -> str:
    return datetime.now(MSK).strftime("%Y-%m-%d %H:%M")


def _today() -> str:
    return datetime.now(MSK).strftime("%Y-%m-%d")


class StateManager:
    """Чтение/запись JSON файлов состояния Продюсера."""

    # --- STATE ---

    def load_state(self) -> dict:
        return self._load_json(STATE_FILE, self._default_state())

    def save_state(self, data: dict):
        self._save_json(STATE_FILE, data)

    def _default_state(self) -> dict:
        return {
            "phase": "research",
            "started_at": _today(),
            "daily_actions": {},
            "total_actions": {},
            "revenue_total_rub": 0,
            "revenue_total_usd": 0,
            "errors_today": 0,
            "last_error": None,
        }

    def record_action(self, action_type: str):
        """Записать выполненное действие в счётчики."""
        state = self.load_state()
        today = _today()

        if today not in state["daily_actions"]:
            state["daily_actions"][today] = {}
        daily = state["daily_actions"][today]
        daily[action_type] = daily.get(action_type, 0) + 1

        state["total_actions"][action_type] = (
            state["total_actions"].get(action_type, 0) + 1
        )
        self.save_state(state)

    def get_daily_count(self, action_type: str) -> int:
        """Сколько раз сегодня выполнялось действие."""
        state = self.load_state()
        today = _today()
        return state["daily_actions"].get(today, {}).get(action_type, 0)

    # --- NICHES ---

    def load_niches(self) -> dict:
        return self._load_json(NICHES_FILE, self._default_niches())

    def save_niches(self, data: dict):
        self._save_json(NICHES_FILE, data)

    def _default_niches(self) -> dict:
        return {
            "researched_niches": [],
            "rejected_niches": [],
            "in_progress": None,
        }

    def add_niche(self, niche: dict):
        """Добавить исследованную нишу."""
        data = self.load_niches()
        data["researched_niches"].append(niche)
        self.save_niches(data)
        logger.info(f"Ниша добавлена: {niche.get('name', '?')} (score={niche.get('score', 0)})")

    def get_qualified_niches(self, min_score: int = 70) -> list:
        """Получить ниши со скором >= min_score."""
        data = self.load_niches()
        return [n for n in data["researched_niches"] if n.get("score", 0) >= min_score]

    def get_niche_by_slug(self, slug: str) -> dict | None:
        """Найти нишу по slug."""
        data = self.load_niches()
        for n in data["researched_niches"]:
            if n.get("slug") == slug:
                return n
        return None

    # --- PRODUCTS ---

    def load_products(self) -> dict:
        return self._load_json(PRODUCTS_FILE, self._default_products())

    def save_products(self, data: dict):
        self._save_json(PRODUCTS_FILE, data)

    def _default_products(self) -> dict:
        return {"products": []}

    def add_product(self, product: dict):
        """Добавить новый продукт."""
        data = self.load_products()
        data["products"].append(product)
        self.save_products(data)
        logger.info(f"Продукт создан: {product.get('title', '?')} (id={product.get('id', '?')})")

    def get_product(self, product_id: str) -> dict | None:
        """Найти продукт по ID."""
        data = self.load_products()
        for p in data["products"]:
            if p.get("id") == product_id:
                return p
        return None

    def update_product(self, product_id: str, updates: dict):
        """Обновить поля продукта."""
        data = self.load_products()
        for p in data["products"]:
            if p.get("id") == product_id:
                p.update(updates)
                break
        self.save_products(data)

    def next_product_id(self) -> str:
        """Сгенерировать следующий ID продукта."""
        data = self.load_products()
        num = len(data["products"]) + 1
        return f"prod_{num:03d}"

    # --- PIPELINE ---

    def load_pipeline(self) -> dict:
        return self._load_json(PIPELINE_FILE, self._default_pipeline())

    def save_pipeline(self, data: dict):
        self._save_json(PIPELINE_FILE, data)

    def _default_pipeline(self) -> dict:
        return {
            "current_stage": "research",
            "stages": {
                "research": {"status": "active", "niches_found": 0, "niches_qualified": 0},
                "content": {"status": "pending", "products_in_progress": 0, "products_complete": 0},
                "landing": {"status": "pending", "pages_built": 0},
                "payment": {"status": "pending", "links_created": 0},
                "sales": {"status": "pending", "total_revenue_rub": 0, "total_sales": 0},
            },
            "cycle_count": 0,
            "last_cycle_at": None,
        }

    def update_pipeline_stage(self, stage: str, updates: dict):
        """Обновить метрики конкретного этапа пайплайна."""
        data = self.load_pipeline()
        if stage in data["stages"]:
            data["stages"][stage].update(updates)
        self.save_pipeline(data)

    # --- INBOX ---

    def write_to_inbox(self, header: str, content: str):
        """Добавить сообщение в INBOX.md."""
        timestamp = _now_msk()
        entry = f"\n## [{timestamp}] {header}\n{content}\n\n---\n"

        existing = ""
        if INBOX_FILE.exists():
            existing = INBOX_FILE.read_text(encoding="utf-8")

        if existing.startswith("# "):
            first_newline = existing.index("\n") + 1
            new_content = existing[:first_newline] + entry + existing[first_newline:]
        else:
            new_content = entry + existing

        INBOX_FILE.write_text(new_content, encoding="utf-8")
        logger.info(f"INBOX: {header}")

    # --- STATUS ---

    def update_status(self, task: str):
        """Обновить строку ПРОДЮСЕР в STATUS.md."""
        timestamp = _now_msk()

        if not STATUS_FILE.exists():
            return

        content = STATUS_FILE.read_text(encoding="utf-8")
        lines = content.split("\n")
        new_lines = []
        found = False

        for line in lines:
            if "ПРОДЮСЕР" in line:
                new_lines.append(
                    f"| ПРОДЮСЕР | active | {timestamp} | {task} |"
                )
                found = True
            else:
                new_lines.append(line)

        if not found:
            new_lines.insert(-1, f"| ПРОДЮСЕР | active | {timestamp} | {task} |")

        STATUS_FILE.write_text("\n".join(new_lines), encoding="utf-8")

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
