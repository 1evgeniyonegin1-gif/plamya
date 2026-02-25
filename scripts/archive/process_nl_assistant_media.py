"""
Обработка медиа-материалов из бота NL Ассистент

Извлекает:
1. Рекламные фото продуктов (для image-to-image YandexART)
2. Ссылки на видео
3. Привязку к конкретным продуктам

Использование:
    python scripts/process_nl_assistant_media.py "путь/к/экспорту"
"""

import json
import re
import shutil
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import sys
import io

# Фикс кодировки для Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


class NLAssistantMediaExtractor:
    def __init__(self, export_path: str):
        self.export_path = Path(export_path)
        self.messages = []

        # Результаты
        self.product_images = defaultdict(list)  # product -> [images]
        self.video_links = []
        self.documents = []

        # Продукты NL для распознавания
        self.products = {
            # Energy Diet
            'energy_diet': {
                'keywords': ['energy diet', 'энерджи дайет', 'энерджи диет', 'ed '],
                'category': 'functional_food',
                'name': 'Energy Diet'
            },
            'energy_diet_smart': {
                'keywords': ['ed smart', 'smart', 'смарт'],
                'category': 'functional_food',
                'name': 'Energy Diet Smart'
            },
            'energy_diet_hd': {
                'keywords': ['ed hd', 'hd', 'хд'],
                'category': 'functional_food',
                'name': 'Energy Diet HD'
            },

            # Green Flash
            'greenflash': {
                'keywords': ['greenflash', 'green flash', 'грин флеш', 'гринфлеш'],
                'category': 'supplements',
                'name': 'GreenFlash'
            },

            # Collagen
            'collagen': {
                'keywords': ['collagen', 'коллаген'],
                'category': 'beauty',
                'name': 'Collagen'
            },

            # DrainEffect
            'draineffect': {
                'keywords': ['draineffect', 'drain effect', 'драйн', 'дрейн'],
                'category': 'detox',
                'name': 'DrainEffect'
            },

            # 3D Slim
            '3d_slim': {
                'keywords': ['3d slim', '3д слим', 'слим'],
                'category': 'weight_loss',
                'name': '3D Slim'
            },

            # Omega
            'omega': {
                'keywords': ['omega', 'омега'],
                'category': 'supplements',
                'name': 'Omega'
            },

            # BioDrone
            'biodrone': {
                'keywords': ['biodrone', 'биодрон'],
                'category': 'supplements',
                'name': 'BioDrone'
            },

            # Enerwood
            'enerwood': {
                'keywords': ['enerwood', 'энервуд'],
                'category': 'tea',
                'name': 'Enerwood'
            },

            # Occuba
            'occuba': {
                'keywords': ['occuba', 'оккуба', 'косметика'],
                'category': 'cosmetics',
                'name': 'Occuba'
            },

            # Be Loved
            'beloved': {
                'keywords': ['be loved', 'белавед', 'би лавед'],
                'category': 'cosmetics',
                'name': 'Be Loved'
            },

            # Детское питание
            'baby_food': {
                'keywords': ['детское', 'baby', 'малыш', 'ребёнок', 'дети'],
                'category': 'baby',
                'name': 'Детское питание'
            },

            # Протеин/Спорт
            'sport': {
                'keywords': ['протеин', 'protein', 'спорт', 'sport', 'гейнер', 'bcaa'],
                'category': 'sport',
                'name': 'Спортивное питание'
            }
        }

        # Категории медиа
        self.media_categories = {
            'promo': ['реклама', 'акция', 'скидка', 'предложение', 'promo'],
            'presentation': ['презентация', 'слайд', 'карточка'],
            'result': ['результат', 'до/после', 'похудел', 'минус'],
            'recipe': ['рецепт', 'приготовление', 'готовим'],
            'info': ['состав', 'польза', 'свойства', 'ингредиент'],
        }

    def load_export(self) -> bool:
        """Загружает экспорт Telegram"""
        print("=" * 60)
        print("ЗАГРУЗКА ЭКСПОРТА NL АССИСТЕНТА")
        print("=" * 60)

        result_json = self.export_path / 'result.json'

        if not result_json.exists():
            print(f"[ERROR] Файл не найден: {result_json}")
            return False

        with open(result_json, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.bot_name = data.get('name', 'NL Assistant')
        self.messages = data.get('messages', [])

        print(f"Бот: {self.bot_name}")
        print(f"Загружено сообщений: {len(self.messages)}")

        # Фильтруем только сообщения
        self.messages = [m for m in self.messages if m.get('type') == 'message']
        print(f"Сообщений (без сервисных): {len(self.messages)}")

        return True

    def get_text(self, msg: dict) -> str:
        """Извлекает текст из сообщения"""
        text = msg.get('text', '')
        if isinstance(text, str):
            return text
        elif isinstance(text, list):
            parts = []
            for item in text:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    parts.append(item.get('text', ''))
            return ' '.join(parts)
        return ''

    def detect_product(self, text: str) -> list:
        """Определяет продукты, упомянутые в тексте"""
        text_lower = text.lower()
        found_products = []

        for product_id, product_info in self.products.items():
            for keyword in product_info['keywords']:
                if keyword in text_lower:
                    found_products.append({
                        'id': product_id,
                        'name': product_info['name'],
                        'category': product_info['category']
                    })
                    break

        return found_products

    def detect_media_category(self, text: str) -> str:
        """Определяет категорию медиа по тексту"""
        text_lower = text.lower()

        for category, keywords in self.media_categories.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return category

        return 'general'

    def extract_video_links(self, text: str) -> list:
        """Извлекает ссылки на видео"""
        patterns = [
            r'https?://(?:www\.)?youtube\.com/watch\?v=[\w-]+',
            r'https?://youtu\.be/[\w-]+',
            r'https?://(?:www\.)?vk\.com/video[\w-]+',
            r'https?://rutube\.ru/video/[\w-]+',
            r'https?://t\.me/[\w/]+',
            r'https?://(?:www\.)?tiktok\.com/@[\w/]+',
        ]

        links = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            links.extend(matches)

        return links

    def process_messages(self):
        """Обрабатывает все сообщения"""
        print("\n" + "=" * 60)
        print("ИЗВЛЕЧЕНИЕ МЕДИА")
        print("=" * 60)

        photos_found = 0
        videos_found = 0

        for idx, msg in enumerate(self.messages):
            if idx % 500 == 0:
                print(f"Обработано: {idx}/{len(self.messages)}")

            text = self.get_text(msg)
            products = self.detect_product(text)
            media_category = self.detect_media_category(text)

            # Обработка фото
            if msg.get('photo'):
                photo_path = msg.get('photo')
                full_photo_path = self.export_path / photo_path

                if full_photo_path.exists():
                    photo_info = {
                        'original_path': str(photo_path),
                        'full_path': str(full_photo_path),
                        'date': msg.get('date', ''),
                        'text': text[:500],  # Первые 500 символов
                        'products': products,
                        'media_category': media_category,
                        'message_id': msg.get('id'),
                    }

                    # Если определены продукты - добавляем к ним
                    if products:
                        for product in products:
                            self.product_images[product['id']].append(photo_info)
                    else:
                        # Общие фото без привязки к продукту
                        self.product_images['general'].append(photo_info)

                    photos_found += 1

            # Обработка видео-ссылок
            video_links = self.extract_video_links(text)
            if video_links:
                for link in video_links:
                    self.video_links.append({
                        'url': link,
                        'date': msg.get('date', ''),
                        'context': text[:300],
                        'products': products,
                    })
                videos_found += len(video_links)

            # Документы/файлы
            if msg.get('file'):
                self.documents.append({
                    'file': msg.get('file'),
                    'date': msg.get('date', ''),
                    'text': text[:200],
                    'products': products,
                })

        print(f"\nНайдено:")
        print(f"  Фото: {photos_found}")
        print(f"  Видео-ссылок: {videos_found}")
        print(f"  Документов: {len(self.documents)}")

        print(f"\nФото по продуктам:")
        for product_id, images in sorted(self.product_images.items(), key=lambda x: -len(x[1])):
            product_name = self.products.get(product_id, {}).get('name', product_id)
            print(f"  {product_name}: {len(images)} фото")

    def organize_media(self):
        """Организует медиа по папкам"""
        print("\n" + "=" * 60)
        print("ОРГАНИЗАЦИЯ МЕДИА")
        print("=" * 60)

        output_base = Path(__file__).parent.parent / 'content' / 'nl_assistant_materials'

        # Создаём структуру папок
        images_dir = output_base / 'images'
        videos_dir = output_base / 'videos'

        # По продуктам
        for product_id in self.product_images.keys():
            product_dir = images_dir / product_id
            product_dir.mkdir(parents=True, exist_ok=True)

        copied_photos = 0

        # Копируем фото
        for product_id, images in self.product_images.items():
            product_dir = images_dir / product_id

            for idx, img_info in enumerate(images):
                src_path = Path(img_info['full_path'])
                if src_path.exists():
                    # Формируем имя: product_category_date_idx.ext
                    date_str = img_info['date'][:10].replace('-', '') if img_info['date'] else 'nodate'
                    category = img_info['media_category']
                    ext = src_path.suffix

                    new_name = f"{product_id}_{category}_{date_str}_{idx:04d}{ext}"
                    dst_path = product_dir / new_name

                    try:
                        shutil.copy2(src_path, dst_path)
                        img_info['organized_path'] = str(dst_path)
                        copied_photos += 1
                    except Exception as e:
                        print(f"  [WARN] Не удалось скопировать {src_path}: {e}")

        print(f"Скопировано фото: {copied_photos}")

        # Сохраняем индекс
        return output_base

    def create_reference_database(self, output_base: Path):
        """Создаёт базу данных референсов для YandexART"""
        print("\n" + "=" * 60)
        print("СОЗДАНИЕ БАЗЫ РЕФЕРЕНСОВ")
        print("=" * 60)

        db_path = output_base / 'image_references.json'

        # Структура для YandexART image-to-image
        reference_db = {
            'created_at': datetime.now().isoformat(),
            'source': 'NL Assistant Bot',
            'products': {},
            'categories': defaultdict(list),
        }

        for product_id, images in self.product_images.items():
            product_info = self.products.get(product_id, {'name': product_id, 'category': 'general'})

            # Выбираем лучшие фото (те, что с большим текстом контекста)
            sorted_images = sorted(images, key=lambda x: len(x.get('text', '')), reverse=True)
            top_images = sorted_images[:20]  # Топ 20 для каждого продукта

            reference_db['products'][product_id] = {
                'name': product_info.get('name', product_id),
                'category': product_info.get('category', 'general'),
                'total_images': len(images),
                'references': [
                    {
                        'path': img.get('organized_path', img['full_path']),
                        'category': img['media_category'],
                        'context': img['text'][:200],
                        'date': img['date'],
                    }
                    for img in top_images
                    if img.get('organized_path') or Path(img['full_path']).exists()
                ]
            }

            # Группируем по категориям медиа
            for img in top_images:
                if img.get('organized_path'):
                    reference_db['categories'][img['media_category']].append({
                        'product': product_id,
                        'path': img['organized_path'],
                    })

        # Конвертируем defaultdict в обычный dict
        reference_db['categories'] = dict(reference_db['categories'])

        with open(db_path, 'w', encoding='utf-8') as f:
            json.dump(reference_db, f, ensure_ascii=False, indent=2)

        print(f"База референсов сохранена: {db_path}")

        # Создаём также текстовый отчёт
        report_path = output_base / 'references_report.txt'
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write("ОТЧЁТ ПО РЕФЕРЕНСАМ ДЛЯ YANDEX ART\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"Дата создания: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
            f.write(f"Источник: NL Assistant Bot\n\n")

            f.write("ПРОДУКТЫ:\n")
            f.write("-" * 40 + "\n")
            for product_id, data in reference_db['products'].items():
                f.write(f"\n{data['name']} ({product_id}):\n")
                f.write(f"  Категория: {data['category']}\n")
                f.write(f"  Всего фото: {data['total_images']}\n")
                f.write(f"  Референсов: {len(data['references'])}\n")

            f.write("\n\nКАТЕГОРИИ МЕДИА:\n")
            f.write("-" * 40 + "\n")
            for category, items in reference_db['categories'].items():
                f.write(f"\n{category}: {len(items)} фото\n")

        print(f"Отчёт сохранён: {report_path}")

        return db_path

    def save_video_links(self, output_base: Path):
        """Сохраняет ссылки на видео"""
        if not self.video_links:
            return

        videos_path = output_base / 'video_links.json'

        with open(videos_path, 'w', encoding='utf-8') as f:
            json.dump({
                'total': len(self.video_links),
                'links': self.video_links,
            }, f, ensure_ascii=False, indent=2)

        print(f"Видео-ссылки сохранены: {videos_path}")

        # Также текстовый файл
        txt_path = output_base / 'video_links.txt'
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write("ВИДЕО-МАТЕРИАЛЫ NL INTERNATIONAL\n")
            f.write("=" * 60 + "\n\n")

            for link_info in self.video_links:
                f.write(f"URL: {link_info['url']}\n")
                if link_info['products']:
                    products = ', '.join(p['name'] for p in link_info['products'])
                    f.write(f"Продукты: {products}\n")
                f.write(f"Контекст: {link_info['context'][:100]}...\n")
                f.write("-" * 40 + "\n")

    def run(self):
        """Главная функция"""
        print("\n" + "=" * 60)
        print("ИЗВЛЕЧЕНИЕ МЕДИА ИЗ NL АССИСТЕНТА")
        print("=" * 60)
        print(f"Путь: {self.export_path}\n")

        if not self.load_export():
            return False

        self.process_messages()
        output_base = self.organize_media()
        self.create_reference_database(output_base)
        self.save_video_links(output_base)

        print("\n" + "=" * 60)
        print("ГОТОВО!")
        print("=" * 60)
        print(f"\nМатериалы сохранены в: {output_base}")
        print("\nСтруктура:")
        print("  /images/               - Фото по продуктам")
        print("  /image_references.json - База референсов для YandexART")
        print("  /video_links.json      - Ссылки на видео")
        print("  /references_report.txt - Текстовый отчёт")

        return True


def main():
    if len(sys.argv) > 1:
        export_path = sys.argv[1]
    else:
        export_path = input("Путь к папке с экспортом NL Ассистента: ").strip('"')

    if not Path(export_path).exists():
        print(f"[ERROR] Папка не найдена: {export_path}")
        return

    extractor = NLAssistantMediaExtractor(export_path)
    extractor.run()


if __name__ == "__main__":
    main()
