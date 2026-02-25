#!/usr/bin/env python3
"""
Скрипт для создания нового партнёра в системе.

Использование:
    python scripts/create_partner.py --interactive
    python scripts/create_partner.py --config partner_data.yaml

Примеры:
    # Интерактивный режим (с вопросами)
    python scripts/create_partner.py --interactive

    # Из файла конфигурации
    python scripts/create_partner.py --config partners/anna/config.yaml
"""

import argparse
import os
import sys
import yaml
import json
import shutil
from pathlib import Path
from datetime import datetime

# Добавляем корневую директорию проекта в path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def create_partner_directory(partner_id: str) -> Path:
    """Создаёт директорию для партнёра."""
    partners_dir = PROJECT_ROOT / "partners"
    partners_dir.mkdir(exist_ok=True)

    partner_dir = partners_dir / partner_id
    if partner_dir.exists():
        print(f"ВНИМАНИЕ: Директория {partner_dir} уже существует!")
        response = input("Перезаписать? (y/n): ")
        if response.lower() != 'y':
            print("Отменено.")
            sys.exit(0)
        shutil.rmtree(partner_dir)

    partner_dir.mkdir()
    return partner_dir


def create_env_file(partner_dir: Path, data: dict) -> None:
    """Создаёт .env файл для партнёра."""
    env_content = f"""# Конфигурация бота партнёра
# Создано: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# Партнёр: {data['name']}

# === TELEGRAM ===
CURATOR_BOT_TOKEN={data['bot_token']}
GROUP_ID={data['group_id']}
ADMIN_TELEGRAM_IDS={data.get('admin_telegram_id', '')}

# === YANDEX CLOUD ===
YANDEX_FOLDER_ID={data['yandex_folder_id']}
YANDEX_SERVICE_ACCOUNT_ID={data['yandex_service_account_id']}
YANDEX_KEY_ID={data['yandex_key_id']}
YANDEX_PRIVATE_KEY={data['yandex_private_key']}
YANDEX_MODEL=yandexgpt-lite
YANDEX_ART_ENABLED=true

# === NL INTERNATIONAL ===
NL_PARTNER_ID={data['nl_partner_id']}
NL_SHOP_LINK={data['nl_shop_link']}
NL_REGISTRATION_LINK={data['nl_registration_link']}

# === ПРОФИЛЬ БОТА ===
BOT_DISPLAY_NAME={data['name']}
BOT_CONTACT={data['contact']}
BOT_SPECIALIZATION={data.get('specialization', 'all')}

# === БАЗА ДАННЫХ ===
# Используется общая БД, но с привязкой к partner_id
PARTNER_ID={data['partner_id']}
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/nl_international

# === ТОПИКИ ГРУППЫ (если есть) ===
TOPIC_PRODUCTS={data.get('topic_products', '0')}
TOPIC_BUSINESS={data.get('topic_business', '0')}
TOPIC_SUCCESS={data.get('topic_success', '0')}
TOPIC_NEWS={data.get('topic_news', '0')}
"""

    env_path = partner_dir / ".env"
    with open(env_path, 'w', encoding='utf-8') as f:
        f.write(env_content)

    print(f"Создан: {env_path}")


def create_config_file(partner_dir: Path, data: dict) -> None:
    """Создаёт config.yaml файл для партнёра."""
    config = {
        'partner': {
            'id': data['partner_id'],
            'name': data['name'],
            'contact': data['contact'],
            'telegram_id': data.get('admin_telegram_id'),
            'created_at': datetime.now().isoformat(),
        },
        'profile': {
            'specialization': data.get('specialization', 'all'),
            'story': data.get('story', ''),
            'communication_style': data.get('style', 'friendly'),
        },
        'links': {
            'nl_partner_id': data['nl_partner_id'],
            'shop': data['nl_shop_link'],
            'registration': data['nl_registration_link'],
        },
        'telegram': {
            'bot_username': data.get('bot_username', ''),
            'group_id': data['group_id'],
            'group_name': data.get('group_name', ''),
        },
        'settings': {
            'funnel_enabled': True,
            'auto_reminders': True,
            'lead_notifications': True,
        }
    }

    config_path = partner_dir / "config.yaml"
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False)

    print(f"Создан: {config_path}")


def create_systemd_service(partner_id: str, data: dict) -> str:
    """Генерирует содержимое systemd service файла."""
    service_content = f"""[Unit]
Description=NL Bot - {data['name']}
After=network.target postgresql.service

[Service]
Type=simple
User=root
WorkingDirectory=/root/nl-bots
Environment=PARTNER_CONFIG=/root/nl-bots/partners/{partner_id}/.env
ExecStart=/root/nl-bots/venv/bin/python -m curator_bot.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""
    return service_content


def interactive_mode() -> dict:
    """Интерактивный сбор данных от пользователя."""
    print("\n" + "="*60)
    print("    СОЗДАНИЕ НОВОГО ПАРТНЁРА")
    print("="*60 + "\n")

    data = {}

    # Основное
    print("--- ОСНОВНОЕ ---")
    data['name'] = input("Имя партнёра (как бот представляется): ").strip()
    data['partner_id'] = input("ID партнёра (латиницей, например 'anna'): ").strip().lower()
    data['contact'] = input("Контакт для клиентов (@username или телефон): ").strip()
    data['admin_telegram_id'] = input("Telegram ID партнёра (числовой): ").strip()

    # Telegram бот
    print("\n--- TELEGRAM БОТ ---")
    data['bot_token'] = input("Токен бота (из @BotFather): ").strip()
    data['bot_username'] = input("Username бота (@...): ").strip()
    data['group_id'] = input("ID группы (начинается с -100...): ").strip()
    data['group_name'] = input("Название группы: ").strip()

    # Yandex Cloud
    print("\n--- YANDEX CLOUD ---")
    data['yandex_folder_id'] = input("Folder ID: ").strip()
    data['yandex_service_account_id'] = input("Service Account ID: ").strip()
    data['yandex_key_id'] = input("Key ID: ").strip()

    print("\nPrivate Key (вставь весь ключ, затем нажми Enter дважды):")
    print("(Или введи путь к JSON-файлу с ключом)")

    key_input = input().strip()
    if key_input.endswith('.json') and os.path.exists(key_input):
        # Читаем из файла
        with open(key_input, 'r') as f:
            key_data = json.load(f)
            data['yandex_private_key'] = key_data.get('private_key', '').replace('\n', '\\n')
    else:
        # Прямой ввод
        lines = [key_input]
        while True:
            line = input()
            if not line:
                break
            lines.append(line)
        data['yandex_private_key'] = '\\n'.join(lines)

    # NL International
    print("\n--- NL INTERNATIONAL ---")
    data['nl_partner_id'] = input("ID партнёра NL: ").strip()
    data['nl_shop_link'] = input("Ссылка на магазин: ").strip()
    data['nl_registration_link'] = input("Ссылка на регистрацию: ").strip()

    # Профиль
    print("\n--- ПРОФИЛЬ БОТА ---")
    print("Специализация:")
    print("  1. weight - Похудение")
    print("  2. energy - Энергия/витамины")
    print("  3. business - Бизнес")
    print("  4. beauty - Красота")
    print("  5. all - Всё понемногу")
    spec_choice = input("Выбери (1-5): ").strip()
    spec_map = {'1': 'weight', '2': 'energy', '3': 'business', '4': 'beauty', '5': 'all'}
    data['specialization'] = spec_map.get(spec_choice, 'all')

    print("\nИстория партнёра (2-3 предложения, Enter для завершения):")
    story_lines = []
    while True:
        line = input()
        if not line:
            break
        story_lines.append(line)
    data['story'] = ' '.join(story_lines)

    print("\nСтиль общения:")
    print("  1. friendly - Дружелюбный, на 'ты'")
    print("  2. formal - Формальный, на 'вы'")
    style_choice = input("Выбери (1-2): ").strip()
    data['style'] = 'formal' if style_choice == '2' else 'friendly'

    return data


def from_config_file(config_path: str) -> dict:
    """Загружает данные из файла конфигурации."""
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def main():
    parser = argparse.ArgumentParser(description='Создание нового партнёра')
    parser.add_argument('--interactive', '-i', action='store_true',
                        help='Интерактивный режим')
    parser.add_argument('--config', '-c', type=str,
                        help='Путь к файлу конфигурации (YAML)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Только показать, что будет создано')

    args = parser.parse_args()

    if args.interactive:
        data = interactive_mode()
    elif args.config:
        data = from_config_file(args.config)
    else:
        parser.print_help()
        print("\nИспользуй --interactive для интерактивного режима")
        sys.exit(1)

    # Валидация
    required_fields = [
        'name', 'partner_id', 'bot_token', 'group_id',
        'yandex_folder_id', 'yandex_service_account_id', 'yandex_key_id',
        'nl_partner_id', 'nl_shop_link', 'nl_registration_link', 'contact'
    ]

    missing = [f for f in required_fields if not data.get(f)]
    if missing:
        print(f"\nОШИБКА: Не заполнены обязательные поля: {', '.join(missing)}")
        sys.exit(1)

    # Показываем сводку
    print("\n" + "="*60)
    print("    СВОДКА")
    print("="*60)
    print(f"Партнёр: {data['name']} ({data['partner_id']})")
    print(f"Бот: {data.get('bot_username', 'не указан')}")
    print(f"Группа: {data['group_id']}")
    print(f"NL ID: {data['nl_partner_id']}")
    print(f"Специализация: {data.get('specialization', 'all')}")
    print("="*60)

    if args.dry_run:
        print("\n[DRY RUN] Файлы не созданы.")
        sys.exit(0)

    confirm = input("\nСоздать партнёра? (y/n): ")
    if confirm.lower() != 'y':
        print("Отменено.")
        sys.exit(0)

    # Создаём файлы
    partner_dir = create_partner_directory(data['partner_id'])
    create_env_file(partner_dir, data)
    create_config_file(partner_dir, data)

    # Генерируем systemd service
    service_content = create_systemd_service(data['partner_id'], data)
    service_path = partner_dir / f"nl-bot-{data['partner_id']}.service"
    with open(service_path, 'w') as f:
        f.write(service_content)
    print(f"Создан: {service_path}")

    # Инструкции
    print("\n" + "="*60)
    print("    ГОТОВО!")
    print("="*60)
    print(f"""
Партнёр {data['name']} создан!

Файлы:
  - {partner_dir}/.env
  - {partner_dir}/config.yaml
  - {partner_dir}/nl-bot-{data['partner_id']}.service

Для запуска на сервере:

1. Скопируй файлы на сервер:
   scp -r partners/{data['partner_id']} root@194.87.86.103:/root/nl-bots/partners/

2. Установи systemd сервис:
   sudo cp /root/nl-bots/partners/{data['partner_id']}/nl-bot-{data['partner_id']}.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable nl-bot-{data['partner_id']}
   sudo systemctl start nl-bot-{data['partner_id']}

3. Проверь статус:
   sudo systemctl status nl-bot-{data['partner_id']}
   sudo journalctl -u nl-bot-{data['partner_id']} -f
""")


if __name__ == "__main__":
    main()
