"""
Настройка логирования для всего проекта
"""
import sys
from loguru import logger
from pathlib import Path


def setup_logger(bot_name: str, log_level: str = "INFO"):
    """
    Настраивает логгер для конкретного бота

    Args:
        bot_name: Имя бота ('curator' или 'content_manager')
        log_level: Уровень логирования (DEBUG, INFO, WARNING, ERROR)
    """

    # Удаляем стандартный handler
    logger.remove()

    # Создаем директорию для логов
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Консольный вывод с цветами
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        level=log_level,
        colorize=True
    )

    # Файловый вывод
    logger.add(
        log_dir / f"{bot_name}.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}",
        level=log_level,
        rotation="10 MB",  # Ротация при достижении 10MB
        retention="1 week",  # Хранить логи неделю
        compression="zip"  # Сжимать старые логи
    )

    # Отдельный файл для ошибок
    logger.add(
        log_dir / f"{bot_name}_errors.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}",
        level="ERROR",
        rotation="10 MB",
        retention="1 month",
        compression="zip"
    )

    logger.info(f"Logger initialized for {bot_name}")

    return logger


def get_logger(name: str = None):
    """
    Получить логгер для модуля.

    Args:
        name: Имя модуля (обычно __name__)

    Returns:
        logger: Настроенный логгер
    """
    return logger
