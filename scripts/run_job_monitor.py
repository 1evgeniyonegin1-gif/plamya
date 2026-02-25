#!/usr/bin/env python3
"""
Скрипт запуска Telegram Job Monitor.

Usage:
    python scripts/run_job_monitor.py
    
Environment variables:
    TELEGRAM_SESSION_STRING - Telethon session string
    TELEGRAM_API_ID - Telegram API ID
    TELEGRAM_API_HASH - Telegram API Hash
"""

import asyncio
import os
import sys
from pathlib import Path

# Добавляем корень проекта в PYTHONPATH
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger

from freelance_engine.telegram_monitor import JobChannelMonitor


def setup_logging():
    """Настройка логирования."""
    log_dir = project_root / "logs"
    log_dir.mkdir(exist_ok=True)
    
    # Удаляем дефолтный handler
    logger.remove()
    
    # Console output (INFO+)
    logger.add(
        sys.stdout,
        level="INFO",
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    )
    
    # File output (DEBUG+)
    logger.add(
        log_dir / "telegram_monitor.log",
        rotation="10 MB",
        retention="7 days",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    )
    
    logger.info("Logging configured")


async def main():
    """Main entry point."""
    setup_logging()
    
    logger.info("=== Telegram Job Monitor ===")
    
    # Получаем credentials
    session_string = os.getenv("TELEGRAM_SESSION_STRING", "")
    api_id = os.getenv("TELEGRAM_API_ID", "")
    api_hash = os.getenv("TELEGRAM_API_HASH", "")
    
    if not session_string:
        logger.error("TELEGRAM_SESSION_STRING not set")
        logger.info("Get session string from Traffic Engine or generate new one")
        return 1
    
    if not api_id or not api_hash:
        logger.error("TELEGRAM_API_ID or TELEGRAM_API_HASH not set")
        return 1
    
    try:
        api_id = int(api_id)
    except ValueError:
        logger.error("TELEGRAM_API_ID must be integer")
        return 1
    
    # Создаём монитор
    monitor = JobChannelMonitor(
        session_string=session_string,
        api_id=api_id,
        api_hash=api_hash,
        use_ai_analysis=False,  # Пока простой анализ (быстрее)
    )
    
    # Запускаем
    try:
        await monitor.start()
    except KeyboardInterrupt:
        logger.info("Received SIGINT, stopping...")
        await monitor.stop()
        return 0
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()) or 0)
