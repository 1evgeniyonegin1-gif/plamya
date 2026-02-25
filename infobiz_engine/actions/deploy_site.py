"""Деплой лендинга на VPS через SCP."""

import logging
import subprocess
from pathlib import Path

from infobiz_engine.state.state_manager import StateManager
from infobiz_engine.config import VPS_HOST, VPS_USER, VPS_COURSES_DIR, LIMITS

logger = logging.getLogger("producer.deploy")


async def run(product_id: str):
    """Задеплоить лендинг продукта на VPS.

    Args:
        product_id: ID продукта
    """
    sm = StateManager()

    # Проверить лимит
    today_count = sm.get_daily_count("deploy")
    if today_count >= LIMITS["max_deploy_per_day"]:
        print(f"Лимит деплоев: {today_count}/{LIMITS['max_deploy_per_day']}")
        return

    product = sm.get_product(product_id)
    if not product:
        print(f"Продукт не найден: {product_id}")
        return

    course_dir = Path(product.get("course_dir", ""))
    landing_dir = course_dir / "landing"
    index_file = landing_dir / "index.html"

    if not index_file.exists():
        print(f"Лендинг не найден: {index_file}")
        print(f"Сначала выполни: build_landing {product_id}")
        return

    niche_slug = product.get("niche_slug", product_id)
    remote_dir = f"{VPS_COURSES_DIR}/{niche_slug}"

    print(f"Деплою лендинг: {niche_slug}")
    print(f"  Файл: {index_file}")
    print(f"  Сервер: {VPS_USER}@{VPS_HOST}:{remote_dir}/")
    print()

    try:
        # Создать директорию на VPS
        subprocess.run(
            ["ssh", f"{VPS_USER}@{VPS_HOST}", f"mkdir -p {remote_dir}"],
            check=True,
            timeout=30,
        )

        # Скопировать файлы
        subprocess.run(
            ["scp", str(index_file), f"{VPS_USER}@{VPS_HOST}:{remote_dir}/index.html"],
            check=True,
            timeout=30,
        )

        landing_url = f"http://{VPS_HOST}/courses/{niche_slug}/"
        print(f"Задеплоено: {landing_url}")

        # Обновить продукт
        sm.update_product(product_id, {
            "status": "live",
            "landing_url": landing_url,
        })
        sm.record_action("deploy")
        sm.update_pipeline_stage("landing", {"status": "active", "pages_built": 1})

        sm.update_status(f"Деплой: {niche_slug} → {landing_url}")

    except subprocess.CalledProcessError as e:
        print(f"Ошибка SSH/SCP: {e}")
        print("Проверь SSH ключи и доступ к VPS.")
        logger.error(f"Deploy error: {e}")
    except subprocess.TimeoutExpired:
        print("Таймаут SSH. VPS недоступен?")
