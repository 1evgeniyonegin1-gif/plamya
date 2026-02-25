"""PLAMYA Heartbeat — автономная работа агентов по расписанию.

Замена OpenClaw cron/gateway. Работает локально через asyncio,
без сетевых сервисов и без gateway.

Использование:
    from shared.heartbeat import Heartbeat

    hb = Heartbeat()
    hb.register("chappie", "check_messages", interval_minutes=30)
    hb.register("chappie", "analyze_channels", interval_minutes=120)
    hb.register("producer", "research_niche", interval_minutes=1440)
    await hb.run_forever()
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Awaitable, Optional

logger = logging.getLogger(__name__)

# PLAMYA home для записи статуса
PLAMYA_HOME = Path.home() / ".plamya"


@dataclass
class ScheduledTask:
    """Задача в расписании."""
    agent: str
    action: str
    interval_seconds: int
    callback: Optional[Callable[[], Awaitable[None]]] = None
    last_run: float = 0.0
    run_count: int = 0
    error_count: int = 0
    last_error: str = ""
    enabled: bool = True


class Heartbeat:
    """Scheduler для автономных агентов."""

    def __init__(self):
        self._tasks: list[ScheduledTask] = []
        self._running = False
        self._callbacks: dict[str, Callable[[], Awaitable[None]]] = {}

    def register(
        self,
        agent: str,
        action: str,
        interval_minutes: int,
        callback: Optional[Callable[[], Awaitable[None]]] = None,
    ) -> None:
        """Зарегистрировать задачу в расписании.

        Args:
            agent: имя агента (chappie, producer, etc)
            action: название действия
            interval_minutes: интервал выполнения в минутах
            callback: async функция для вызова
        """
        task = ScheduledTask(
            agent=agent,
            action=action,
            interval_seconds=interval_minutes * 60,
            callback=callback,
        )
        self._tasks.append(task)
        logger.info(
            f"[Heartbeat] Registered: {agent}/{action} "
            f"every {interval_minutes} min"
        )

    def set_callback(self, agent: str, action: str, callback: Callable[[], Awaitable[None]]) -> None:
        """Установить callback для задачи (можно после register)."""
        for task in self._tasks:
            if task.agent == agent and task.action == action:
                task.callback = callback
                return
        logger.warning(f"[Heartbeat] Task {agent}/{action} not found")

    async def run_forever(self, check_interval: int = 30) -> None:
        """Запустить бесконечный цикл проверки расписания.

        Args:
            check_interval: как часто проверять задачи (секунды)
        """
        self._running = True
        logger.info(f"[Heartbeat] Started with {len(self._tasks)} tasks")
        self._write_status()

        while self._running:
            now = time.time()

            for task in self._tasks:
                if not task.enabled:
                    continue
                if not task.callback:
                    continue
                if now - task.last_run < task.interval_seconds:
                    continue

                # Время выполнять
                await self._execute_task(task)

            self._write_status()
            await asyncio.sleep(check_interval)

    async def _execute_task(self, task: ScheduledTask) -> None:
        """Выполнить задачу с обработкой ошибок."""
        task.last_run = time.time()
        task.run_count += 1

        logger.info(
            f"[Heartbeat] Executing: {task.agent}/{task.action} "
            f"(run #{task.run_count})"
        )

        try:
            await task.callback()
            logger.info(
                f"[Heartbeat] Done: {task.agent}/{task.action}"
            )
        except Exception as e:
            task.error_count += 1
            task.last_error = str(e)[:200]
            logger.error(
                f"[Heartbeat] Error in {task.agent}/{task.action}: {e}"
            )

            # Если слишком много ошибок подряд — отключить
            if task.error_count >= 5:
                task.enabled = False
                logger.warning(
                    f"[Heartbeat] Disabled {task.agent}/{task.action} "
                    f"after {task.error_count} errors"
                )

    def stop(self) -> None:
        """Остановить heartbeat."""
        self._running = False
        logger.info("[Heartbeat] Stopped")

    def get_status(self) -> list[dict]:
        """Получить статус всех задач."""
        return [
            {
                "agent": t.agent,
                "action": t.action,
                "interval_min": t.interval_seconds // 60,
                "enabled": t.enabled,
                "run_count": t.run_count,
                "error_count": t.error_count,
                "last_run": datetime.fromtimestamp(t.last_run).isoformat() if t.last_run else None,
                "last_error": t.last_error or None,
            }
            for t in self._tasks
        ]

    def _write_status(self) -> None:
        """Записать статус в ~/.plamya/shared/STATUS.md."""
        status_dir = PLAMYA_HOME / "shared"
        status_dir.mkdir(parents=True, exist_ok=True)
        status_file = status_dir / "STATUS.md"

        lines = ["# PLAMYA Agent Status", ""]
        lines.append(f"Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S MSK')}")
        lines.append("")
        lines.append("| Agent | Action | Interval | Runs | Errors | Last Run | Status |")
        lines.append("|-------|--------|----------|------|--------|----------|--------|")

        for t in self._tasks:
            last = datetime.fromtimestamp(t.last_run).strftime("%H:%M") if t.last_run else "-"
            status = "active" if t.enabled else "disabled"
            if t.error_count > 0 and t.enabled:
                status = f"warn ({t.error_count} err)"
            lines.append(
                f"| {t.agent} | {t.action} | {t.interval_seconds // 60}m | "
                f"{t.run_count} | {t.error_count} | {last} | {status} |"
            )

        lines.append("")
        status_file.write_text("\n".join(lines), encoding="utf-8")
