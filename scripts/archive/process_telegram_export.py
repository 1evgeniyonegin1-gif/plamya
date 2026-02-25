"""
Обработка экспорта Telegram-канала лидера NL International
Извлекает информацию о продуктах, цены, описания, фото
"""

import json
import re
from pathlib import Path
from datetime import datetime
import shutil
from collections import defaultdict
import sys
import io

# Фикс кодировки для Windows консоли
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

class TelegramExportProcessor:
    def __init__(self, export_path):
        """
        :param export_path: Путь к папке с экспортом Telegram
        """
        self.export_path = Path(export_path)
        self.messages = []
        self.products_info = defaultdict(list)
        self.product_photos = defaultdict(list)

        # Регулярные выражения для поиска информации
        self.patterns = {
            'price': r'(\d+)\s*(?:руб|₽|rub)',
            'pv': r'(\d+(?:\.\d+)?)\s*PV',
            'discount': r'(?:скидка|акция|sale)\s*(\d+)\s*%',
            'product_names': [
                r'Energy Diet',
                r'Greenflash',
                r'Be Loved',
                r'Collagen',
                r'BioDrone',
                r'BioTuning',
                r'BioSetting',
                r'DrainEffect',
                r'3D SLIM',
                r'Occuba',
                r'Enerwood',
                r'Herbal Tea',
            ]
        }

    def load_telegram_export(self):
        """Загружает данные из экспорта Telegram"""
        print("[1/5] Загрузка экспорта Telegram...")

        # Ищем result.json (формат экспорта Telegram Desktop)
        result_json = self.export_path / 'result.json'

        if result_json.exists():
            print(f"  [OK] Найден result.json")
            with open(result_json, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.messages = data.get('messages', [])
                print(f"  [OK] Загружено {len(self.messages)} сообщений")
        else:
            print(f"  [INFO] result.json не найден, ищу другие форматы...")
            # Ищем другие форматы экспорта
            json_files = list(self.export_path.glob('*.json'))
            if json_files:
                print(f"  [OK] Найдено {len(json_files)} JSON файлов")
                for json_file in json_files:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            self.messages.extend(data)
                        elif isinstance(data, dict) and 'messages' in data:
                            self.messages.extend(data['messages'])
                print(f"  [OK] Загружено {len(self.messages)} сообщений")
            else:
                print("  [ERROR] Не найдены JSON файлы экспорта")
                return False

        return True

    def extract_product_info(self):
        """Извлекает информацию о продуктах из сообщений"""
        print("\n[2/5] Извлечение информации о продуктах...")

        product_mentions = defaultdict(list)
        total_msgs = len(self.messages)

        for idx, msg in enumerate(self.messages):
            # Прогресс каждые 1000 сообщений
            if idx % 1000 == 0:
                print(f"  Обработано: {idx}/{total_msgs} ({idx*100//total_msgs}%)")
            # Получаем текст сообщения
            text = ""
            if isinstance(msg, dict):
                if 'text' in msg:
                    if isinstance(msg['text'], str):
                        text = msg['text']
                    elif isinstance(msg['text'], list):
                        # Telegram экспорт может хранить текст как список объектов
                        text = ' '.join([
                            item if isinstance(item, str) else item.get('text', '')
                            for item in msg['text']
                        ])

                date = msg.get('date', '')
                msg_id = msg.get('id', 0)

                # Ищем упоминания продуктов
                for product_name in self.patterns['product_names']:
                    if re.search(product_name, text, re.IGNORECASE):
                        # Извлекаем цену
                        price_match = re.search(self.patterns['price'], text)
                        price = price_match.group(1) if price_match else None

                        # Извлекаем PV
                        pv_match = re.search(self.patterns['pv'], text)
                        pv = pv_match.group(1) if pv_match else None

                        # Извлекаем скидку
                        discount_match = re.search(self.patterns['discount'], text, re.IGNORECASE)
                        discount = discount_match.group(1) if discount_match else None

                        product_mentions[product_name].append({
                            'text': text,
                            'date': date,
                            'msg_id': msg_id,
                            'price': price,
                            'pv': pv,
                            'discount': discount,
                            'photo': msg.get('photo', None),
                            'file': msg.get('file', None),
                        })

        self.products_info = product_mentions

        total_mentions = sum(len(v) for v in product_mentions.values())
        print(f"  [OK] Найдено упоминаний продуктов: {total_mentions}")
        print(f"  [OK] Уникальных продуктов: {len(product_mentions)}")

        # Выводим топ-5 самых упоминаемых
        top_products = sorted(product_mentions.items(), key=lambda x: len(x[1]), reverse=True)[:5]
        print("\n  Топ-5 упоминаемых продуктов:")
        for product, mentions in top_products:
            print(f"    - {product}: {len(mentions)} упоминаний")

    def extract_photos(self):
        """Копирует фото продуктов в отдельную папку"""
        print("\n[3/5] Извлечение фотографий продуктов...")

        photos_dir = Path(__file__).parent.parent / 'content' / 'product_images' / 'from_telegram'
        photos_dir.mkdir(exist_ok=True, parents=True)

        copied_photos = 0

        print(f"  Продуктов с упоминаниями: {len(self.products_info)}")

        for idx, (product_name, mentions) in enumerate(self.products_info.items()):
            print(f"  [{idx+1}/{len(self.products_info)}] {product_name}: {len(mentions)} упоминаний")
            product_dir = photos_dir / product_name.replace(' ', '_').lower()
            product_dir.mkdir(exist_ok=True)

            for i, mention in enumerate(mentions):
                # Ищем фото в сообщении
                photo_path = None

                if mention.get('photo'):
                    photo_path = self.export_path / mention['photo']
                elif mention.get('file'):
                    file_path = self.export_path / mention['file']
                    # Проверяем, это изображение?
                    if file_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp']:
                        photo_path = file_path

                if photo_path and photo_path.exists():
                    # Копируем фото
                    dest = product_dir / f"{i:03d}_{photo_path.name}"
                    shutil.copy2(photo_path, dest)
                    copied_photos += 1

                    self.product_photos[product_name].append(str(dest))

        print(f"  [OK] Скопировано фотографий: {copied_photos}")
        print(f"  [OK] Папка: {photos_dir}")

    def generate_product_summaries(self):
        """Создаёт сводки по каждому продукту"""
        print("\n[4/5] Генерация сводок по продуктам...")

        summaries_dir = Path(__file__).parent.parent / 'content' / 'telegram_summaries'
        summaries_dir.mkdir(exist_ok=True)

        for product_name, mentions in self.products_info.items():
            summary = {
                'product': product_name,
                'total_mentions': len(mentions),
                'dates': [m['date'] for m in mentions if m.get('date')],
                'prices': list(set([m['price'] for m in mentions if m.get('price')])),
                'pv_values': list(set([m['pv'] for m in mentions if m.get('pv')])),
                'all_texts': [m['text'] for m in mentions],
                'photos': self.product_photos.get(product_name, []),
            }

            # Сохраняем сводку
            filename = product_name.replace(' ', '_').lower() + '.json'
            with open(summaries_dir / filename, 'w', encoding='utf-8') as f:
                json.dump(summary, f, ensure_ascii=False, indent=2)

        print(f"  [OK] Создано сводок: {len(self.products_info)}")
        print(f"  [OK] Папка: {summaries_dir}")

    def create_master_report(self):
        """Создаёт итоговый отчёт"""
        print("\n[5/5] Создание итогового отчёта...")

        report = {
            'export_date': datetime.now().isoformat(),
            'total_messages': len(self.messages),
            'products_found': len(self.products_info),
            'total_photos': sum(len(v) for v in self.product_photos.values()),
            'products': {}
        }

        for product_name, mentions in self.products_info.items():
            report['products'][product_name] = {
                'mentions': len(mentions),
                'has_prices': any(m.get('price') for m in mentions),
                'has_pv': any(m.get('pv') for m in mentions),
                'photos_count': len(self.product_photos.get(product_name, [])),
            }

        # Сохраняем отчёт
        report_path = Path(__file__).parent.parent / 'content' / 'telegram_export_report.json'
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"  [OK] Отчёт сохранён: {report_path}")

        # Выводим статистику
        print("\n" + "="*60)
        print("ИТОГОВАЯ СТАТИСТИКА")
        print("="*60)
        print(f"Всего сообщений: {report['total_messages']}")
        print(f"Найдено продуктов: {report['products_found']}")
        print(f"Всего фотографий: {report['total_photos']}")
        print(f"")
        print("Что дальше:")
        print("  1. Проверь папку: content/product_images/from_telegram/")
        print("  2. Проверь сводки: content/telegram_summaries/")
        print("  3. Используй эти данные для обновления базы знаний")
        print("="*60)

    def process(self):
        """Главная функция обработки"""
        print("="*60)
        print("ОБРАБОТКА ЭКСПОРТА TELEGRAM-КАНАЛА")
        print("="*60)
        print(f"Путь к экспорту: {self.export_path}")
        print("")

        if not self.load_telegram_export():
            print("\n[ERROR] Не удалось загрузить экспорт")
            return False

        self.extract_product_info()
        self.extract_photos()
        self.generate_product_summaries()
        self.create_master_report()

        return True


def main():
    # ПУТЬ К ЭКСПОРТУ - УКАЖИ СВОЙ!
    export_path = input("Введи путь к папке с экспортом Telegram: ").strip('"')

    if not Path(export_path).exists():
        print(f"[ERROR] Папка не найдена: {export_path}")
        return

    processor = TelegramExportProcessor(export_path)
    processor.process()


if __name__ == "__main__":
    main()
