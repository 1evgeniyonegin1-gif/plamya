"""
Helper функции для работы с изображениями
"""
import base64
import io
from typing import Optional, Tuple
from pathlib import Path
from aiogram.types import BufferedInputFile
from loguru import logger

try:
    from PIL import Image, ImageDraw, ImageFont
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False
    logger.warning("Pillow not installed - image compositing features disabled")


def base64_to_buffered_file(base64_string: str, filename: str = "image.jpg") -> Optional[BufferedInputFile]:
    """
    Конвертирует base64 строку в BufferedInputFile для отправки в Telegram

    Args:
        base64_string: Base64-encoded изображение
        filename: Имя файла

    Returns:
        BufferedInputFile или None при ошибке
    """
    try:
        image_bytes = base64.b64decode(base64_string)
        return BufferedInputFile(image_bytes, filename=filename)
    except Exception as e:
        logger.error(f"Error converting base64 to BufferedInputFile: {e}")
        return None


def is_valid_base64_image(base64_string: str) -> bool:
    """
    Проверяет, является ли строка валидным base64-encoded изображением

    Args:
        base64_string: Строка для проверки

    Returns:
        True если валидная, False иначе
    """
    try:
        # Пытаемся декодировать
        image_bytes = base64.b64decode(base64_string)

        # Проверяем минимальный размер
        if len(image_bytes) < 100:
            return False

        # Проверяем сигнатуры популярных форматов
        # JPEG: FF D8 FF
        # PNG: 89 50 4E 47
        # GIF: 47 49 46 38
        signatures = [
            b'\xff\xd8\xff',  # JPEG
            b'\x89\x50\x4e\x47',  # PNG
            b'\x47\x49\x46\x38',  # GIF
        ]

        return any(image_bytes.startswith(sig) for sig in signatures)

    except Exception:
        return False


def get_image_size_kb(base64_string: str) -> Optional[float]:
    """
    Возвращает размер изображения в килобайтах

    Args:
        base64_string: Base64-encoded изображение

    Returns:
        Размер в KB или None при ошибке
    """
    try:
        image_bytes = base64.b64decode(base64_string)
        return len(image_bytes) / 1024
    except Exception as e:
        logger.error(f"Error getting image size: {e}")
        return None


# === Функции композитинга (требуют Pillow) ===

def add_watermark(
    base64_image: str,
    watermark_text: str = "NL International",
    position: str = "bottom_right",
    opacity: int = 128
) -> Optional[str]:
    """
    Добавляет текстовый водяной знак на изображение

    Args:
        base64_image: Base64-encoded изображение
        watermark_text: Текст водяного знака
        position: Позиция ("bottom_right", "bottom_left", "top_right", "top_left", "center")
        opacity: Прозрачность (0-255, где 255 = непрозрачный)

    Returns:
        Base64-encoded изображение с водяным знаком или None при ошибке
    """
    if not PILLOW_AVAILABLE:
        logger.warning("Pillow not available - watermark not added")
        return base64_image

    try:
        # Декодируем изображение
        image_bytes = base64.b64decode(base64_image)
        image = Image.open(io.BytesIO(image_bytes)).convert("RGBA")

        # Создаем слой для водяного знака
        watermark_layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(watermark_layer)

        # Определяем размер шрифта (2% от высоты изображения)
        font_size = max(int(image.height * 0.02), 12)
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            font = ImageFont.load_default()

        # Получаем размеры текста
        bbox = draw.textbbox((0, 0), watermark_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        # Вычисляем позицию
        padding = 20
        positions = {
            "bottom_right": (image.width - text_width - padding, image.height - text_height - padding),
            "bottom_left": (padding, image.height - text_height - padding),
            "top_right": (image.width - text_width - padding, padding),
            "top_left": (padding, padding),
            "center": ((image.width - text_width) // 2, (image.height - text_height) // 2)
        }

        x, y = positions.get(position, positions["bottom_right"])

        # Рисуем водяной знак
        draw.text((x, y), watermark_text, font=font, fill=(255, 255, 255, opacity))

        # Накладываем водяной знак на изображение
        result = Image.alpha_composite(image, watermark_layer)

        # Конвертируем обратно в RGB для JPEG
        result_rgb = result.convert("RGB")

        # Сохраняем в base64
        output_buffer = io.BytesIO()
        result_rgb.save(output_buffer, format="JPEG", quality=95)
        output_base64 = base64.b64encode(output_buffer.getvalue()).decode('utf-8')

        logger.info(f"Watermark '{watermark_text}' added at {position}")
        return output_base64

    except Exception as e:
        logger.error(f"Error adding watermark: {e}")
        return None


def add_logo_overlay(
    base64_image: str,
    logo_path: str,
    position: str = "bottom_right",
    logo_size_percent: int = 10,
    opacity: int = 230
) -> Optional[str]:
    """
    Накладывает логотип на изображение

    Args:
        base64_image: Base64-encoded изображение
        logo_path: Путь к файлу логотипа (PNG с прозрачностью)
        position: Позиция ("bottom_right", "bottom_left", "top_right", "top_left")
        logo_size_percent: Размер логотипа в % от ширины изображения (5-20)
        opacity: Прозрачность логотипа (0-255)

    Returns:
        Base64-encoded изображение с логотипом или None при ошибке
    """
    if not PILLOW_AVAILABLE:
        logger.warning("Pillow not available - logo not added")
        return base64_image

    try:
        # Проверяем существование файла логотипа
        logo_file = Path(logo_path)
        if not logo_file.exists():
            logger.warning(f"Logo file not found: {logo_path}")
            return base64_image

        # Декодируем изображение
        image_bytes = base64.b64decode(base64_image)
        image = Image.open(io.BytesIO(image_bytes)).convert("RGBA")

        # Загружаем логотип
        logo = Image.open(logo_file).convert("RGBA")

        # Изменяем размер логотипа
        logo_width = int(image.width * (logo_size_percent / 100))
        logo_aspect = logo.height / logo.width
        logo_height = int(logo_width * logo_aspect)
        logo = logo.resize((logo_width, logo_height), Image.Resampling.LANCZOS)

        # Применяем прозрачность
        if opacity < 255:
            alpha = logo.split()[3]
            alpha = alpha.point(lambda p: int(p * (opacity / 255)))
            logo.putalpha(alpha)

        # Вычисляем позицию
        padding = 20
        positions = {
            "bottom_right": (image.width - logo_width - padding, image.height - logo_height - padding),
            "bottom_left": (padding, image.height - logo_height - padding),
            "top_right": (image.width - logo_width - padding, padding),
            "top_left": (padding, padding)
        }

        x, y = positions.get(position, positions["bottom_right"])

        # Накладываем логотип
        image.paste(logo, (x, y), logo)

        # Конвертируем обратно в RGB для JPEG
        result_rgb = image.convert("RGB")

        # Сохраняем в base64
        output_buffer = io.BytesIO()
        result_rgb.save(output_buffer, format="JPEG", quality=95)
        output_base64 = base64.b64encode(output_buffer.getvalue()).decode('utf-8')

        logger.info(f"Logo overlay added at {position} (size: {logo_size_percent}%)")
        return output_base64

    except Exception as e:
        logger.error(f"Error adding logo overlay: {e}")
        return None


def resize_image(
    base64_image: str,
    max_width: int = 1920,
    max_height: int = 1920,
    quality: int = 90
) -> Optional[str]:
    """
    Изменяет размер изображения с сохранением пропорций

    Args:
        base64_image: Base64-encoded изображение
        max_width: Максимальная ширина
        max_height: Максимальная высота
        quality: Качество JPEG (1-100)

    Returns:
        Base64-encoded изображение или None при ошибке
    """
    if not PILLOW_AVAILABLE:
        logger.warning("Pillow not available - image not resized")
        return base64_image

    try:
        # Декодируем изображение
        image_bytes = base64.b64decode(base64_image)
        image = Image.open(io.BytesIO(image_bytes))

        # Проверяем, нужно ли изменять размер
        if image.width <= max_width and image.height <= max_height:
            logger.info("Image already within size limits")
            return base64_image

        # Вычисляем новые размеры с сохранением пропорций
        ratio = min(max_width / image.width, max_height / image.height)
        new_size = (int(image.width * ratio), int(image.height * ratio))

        # Изменяем размер
        resized = image.resize(new_size, Image.Resampling.LANCZOS)

        # Конвертируем в RGB если нужно
        if resized.mode in ("RGBA", "LA", "P"):
            resized = resized.convert("RGB")

        # Сохраняем в base64
        output_buffer = io.BytesIO()
        resized.save(output_buffer, format="JPEG", quality=quality)
        output_base64 = base64.b64encode(output_buffer.getvalue()).decode('utf-8')

        logger.info(f"Image resized from {image.size} to {new_size}")
        return output_base64

    except Exception as e:
        logger.error(f"Error resizing image: {e}")
        return None
