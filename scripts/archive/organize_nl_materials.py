"""
Организация материалов NL Ассистента по папкам продуктов

Создаёт структуру:
/content/nl_knowledge/
├── energy_diet/
│   ├── photos/
│   ├── documents/
│   └── info.json (YouTube ссылки, описание)
├── greenflash/
├── collagen/
└── ...

Использование:
    python scripts/organize_nl_materials.py "путь/к/экспорту"
"""

import json
import re
import shutil
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


class NLMaterialsOrganizer:
    def __init__(self, export_path: str):
        self.export_path = Path(export_path)
        self.messages = []

        # Результаты по продуктам
        self.products_data = defaultdict(lambda: {
            'photos': [],
            'documents': [],
            'videos': [],
            'texts': [],
            'faq': [],
        })

        # Расширенный словарь продуктов NL
        self.product_patterns = {
            # Energy Diet линейка
            'energy_diet': {
                'patterns': [
                    r'energy\s*diet', r'энерджи\s*дайет', r'энерджи\s*диет',
                    r'\bed\b', r'е\.д\.', r'ед\s', r'функциональное питание'
                ],
                'name': 'Energy Diet',
                'category': 'functional_food'
            },
            'ed_smart': {
                'patterns': [r'ed\s*smart', r'smart', r'смарт'],
                'name': 'ED Smart',
                'category': 'functional_food'
            },
            'ed_hd': {
                'patterns': [r'ed\s*hd', r'\bhd\b', r'хд'],
                'name': 'ED HD',
                'category': 'functional_food'
            },

            # GreenFlash
            'greenflash': {
                'patterns': [
                    r'green\s*flash', r'greenflash', r'грин\s*флеш', r'гринфлеш',
                    r'lymph\s*gyan', r'лимф\s*гьян',
                    r'lux\s*gyan', r'люкс\s*гьян',
                    r'uri\s*gyan', r'ури\s*гьян',
                    r'livo\s*gyan', r'ливо\s*гьян',
                    r'gut\s*vigyan', r'гат\s*вигьян',
                    r'gyan', r'гьян', r'vigyan', r'вигьян'
                ],
                'name': 'GreenFlash',
                'category': 'supplements'
            },

            # Collagen
            'collagen': {
                'patterns': [r'collagen', r'коллаген'],
                'name': 'Collagen',
                'category': 'beauty'
            },

            # DrainEffect
            'draineffect': {
                'patterns': [r'drain\s*effect', r'draineffect', r'драйн', r'дрейн', r'детокс'],
                'name': 'DrainEffect',
                'category': 'detox'
            },

            # 3D Slim
            '3d_slim': {
                'patterns': [r'3d\s*slim', r'3д\s*слим', r'слим', r'похудение'],
                'name': '3D Slim',
                'category': 'weight_loss'
            },

            # Omega
            'omega': {
                'patterns': [r'omega', r'омега', r'dha', r'дгк', r'рыбий жир'],
                'name': 'Omega',
                'category': 'supplements'
            },

            # Vision Lecithin
            'vision_lecithin': {
                'patterns': [r'vision\s*lecithin', r'лецитин', r'lecithin', r'vision'],
                'name': 'Vision Lecithin',
                'category': 'supplements'
            },

            # ProHelper
            'prohelper': {
                'patterns': [r'prohelper', r'прохелпер', r'pro\s*helper'],
                'name': 'ProHelper',
                'category': 'supplements'
            },

            # Imperial Herb
            'imperial_herb': {
                'patterns': [r'imperial\s*herb', r'империал\s*херб', r'травяной чай'],
                'name': 'Imperial Herb',
                'category': 'tea'
            },

            # Happy Smile (зубная паста)
            'happy_smile': {
                'patterns': [r'happy\s*smile', r'хэппи\s*смайл', r'зубная паста', r'зуб'],
                'name': 'Happy Smile',
                'category': 'cosmetics'
            },

            # Детская линейка NL'ka
            'nlka_baby': {
                'patterns': [r"nl'?ka\s*baby", r'нлка\s*бейби', r'детское.*с первых дней', r'для новорожд'],
                'name': "NL'ka Baby",
                'category': 'baby'
            },
            'nlka_kids': {
                'patterns': [r"nl'?ka\s*kids", r'нлка\s*кидс', r'детское.*2-3', r'для детей'],
                'name': "NL'ka Kids",
                'category': 'baby'
            },
            'nlka_cosmetics': {
                'patterns': [r"nl'?ka.*косметика", r'детская косметика', r'nlka_kosmetika'],
                'name': "NL'ka Косметика",
                'category': 'baby'
            },

            # Occuba (косметика)
            'occuba': {
                'patterns': [r'occuba', r'оккуба', r'косметика nl'],
                'name': 'Occuba',
                'category': 'cosmetics'
            },

            # Be Loved
            'beloved': {
                'patterns': [r'be\s*loved', r'белавед', r'би\s*лавед'],
                'name': 'Be Loved',
                'category': 'cosmetics'
            },

            # Спорт
            'sport': {
                'patterns': [r'протеин', r'protein', r'спорт', r'гейнер', r'bcaa', r'pre-workout'],
                'name': 'Спортивное питание',
                'category': 'sport'
            },

            # Бизнес/Стартовые наборы
            'starter_kits': {
                'patterns': [r'стартов\w+\s*набор', r'starter', r'регистраци', r'бизнес\s*пак'],
                'name': 'Стартовые наборы',
                'category': 'business'
            },

            # Calcium
            'calcium': {
                'patterns': [r'calcium', r'кальций', r'ca\b'],
                'name': 'Calcium',
                'category': 'supplements'
            },
        }

        # Типы контента по расширениям файлов
        self.doc_types = {
            '.pdf': 'document',
            '.doc': 'document',
            '.docx': 'document',
            '.ppt': 'presentation',
            '.pptx': 'presentation',
            '.xls': 'spreadsheet',
            '.xlsx': 'spreadsheet',
            '.ogg': 'audio',
            '.mp3': 'audio',
            '.mp4': 'video',
        }

    def load_export(self) -> bool:
        """Загружает экспорт"""
        print("=" * 60)
        print("ЗАГРУЗКА ЭКСПОРТА")
        print("=" * 60)

        result_json = self.export_path / 'result.json'
        if not result_json.exists():
            print(f"[ERROR] Файл не найден: {result_json}")
            return False

        with open(result_json, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.messages = [m for m in data.get('messages', []) if m.get('type') == 'message']
        print(f"Загружено сообщений: {len(self.messages)}")
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

    def detect_products(self, text: str, filename: str = '') -> list:
        """Определяет продукты из текста и имени файла"""
        search_text = (text + ' ' + filename).lower()
        found = []

        for product_id, info in self.product_patterns.items():
            for pattern in info['patterns']:
                if re.search(pattern, search_text, re.IGNORECASE):
                    found.append(product_id)
                    break

        return list(set(found)) if found else ['general']

    def extract_youtube_links(self, text: str) -> list:
        """Извлекает YouTube ссылки"""
        patterns = [
            r'https?://(?:www\.)?youtube\.com/watch\?v=([\w-]+)',
            r'https?://youtu\.be/([\w-]+)',
        ]
        links = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for video_id in matches:
                links.append(f'https://youtube.com/watch?v={video_id}')
        return links

    def extract_all_links(self, text: str) -> list:
        """Извлекает все ссылки"""
        pattern = r'https?://[^\s<>\"\']+'
        return re.findall(pattern, text)

    def process_messages(self):
        """Обрабатывает все сообщения"""
        print("\n" + "=" * 60)
        print("АНАЛИЗ СООБЩЕНИЙ")
        print("=" * 60)

        for idx, msg in enumerate(self.messages):
            if idx % 1000 == 0:
                print(f"Обработано: {idx}/{len(self.messages)}")

            text = self.get_text(msg)

            # Обрабатываем фото
            if msg.get('photo'):
                photo_path = self.export_path / msg['photo']
                if photo_path.exists():
                    products = self.detect_products(text, msg['photo'])
                    for product in products:
                        self.products_data[product]['photos'].append({
                            'path': str(photo_path),
                            'filename': msg['photo'],
                            'context': text[:500],
                            'date': msg.get('date', ''),
                        })

            # Обрабатываем файлы/документы
            if msg.get('file'):
                file_path = self.export_path / msg['file']
                filename = msg['file']
                products = self.detect_products(text, filename)

                ext = Path(filename).suffix.lower()
                doc_type = self.doc_types.get(ext, 'other')

                for product in products:
                    self.products_data[product]['documents'].append({
                        'path': str(file_path),
                        'filename': filename,
                        'type': doc_type,
                        'context': text[:300],
                        'date': msg.get('date', ''),
                    })

            # Извлекаем видео ссылки
            youtube_links = self.extract_youtube_links(text)
            if youtube_links:
                products = self.detect_products(text)
                for product in products:
                    for link in youtube_links:
                        self.products_data[product]['videos'].append({
                            'url': link,
                            'context': text[:300],
                            'date': msg.get('date', ''),
                        })

            # Сохраняем текстовые ответы бота (FAQ, описания)
            if text and len(text) > 200:
                products = self.detect_products(text)
                for product in products:
                    # Проверяем, похоже ли на FAQ
                    if any(kw in text.lower() for kw in ['вопрос', 'ответ', '?', 'как', 'почему', 'зачем']):
                        self.products_data[product]['faq'].append({
                            'text': text,
                            'date': msg.get('date', ''),
                        })
                    else:
                        self.products_data[product]['texts'].append({
                            'text': text,
                            'date': msg.get('date', ''),
                        })

        # Статистика
        print("\n" + "-" * 40)
        print("СТАТИСТИКА ПО ПРОДУКТАМ:")
        print("-" * 40)

        for product_id, data in sorted(self.products_data.items(), key=lambda x: -len(x[1]['photos'])):
            name = self.product_patterns.get(product_id, {}).get('name', product_id)
            print(f"\n{name}:")
            print(f"  Фото: {len(data['photos'])}")
            print(f"  Документы: {len(data['documents'])}")
            print(f"  Видео: {len(data['videos'])}")
            print(f"  Тексты: {len(data['texts'])}")
            print(f"  FAQ: {len(data['faq'])}")

    def organize_to_folders(self):
        """Организует всё по папкам"""
        print("\n" + "=" * 60)
        print("СОЗДАНИЕ СТРУКТУРЫ ПАПОК")
        print("=" * 60)

        output_base = Path(__file__).parent.parent / 'content' / 'nl_knowledge'
        output_base.mkdir(parents=True, exist_ok=True)

        stats = {'photos': 0, 'documents': 0}

        for product_id, data in self.products_data.items():
            if not any([data['photos'], data['documents'], data['videos']]):
                continue

            # Создаём папку продукта
            product_dir = output_base / product_id
            product_dir.mkdir(exist_ok=True)

            # Папка для фото
            if data['photos']:
                photos_dir = product_dir / 'photos'
                photos_dir.mkdir(exist_ok=True)

                # Копируем только уникальные фото (первые 100)
                seen = set()
                for idx, photo in enumerate(data['photos'][:100]):
                    src = Path(photo['path'])
                    if src.exists() and src.name not in seen:
                        seen.add(src.name)
                        dst = photos_dir / f"{idx:04d}_{src.name}"
                        try:
                            shutil.copy2(src, dst)
                            stats['photos'] += 1
                        except Exception as e:
                            pass

            # Папка для документов
            if data['documents']:
                docs_dir = product_dir / 'documents'
                docs_dir.mkdir(exist_ok=True)

                seen = set()
                for doc in data['documents']:
                    src = Path(doc['path'])
                    if src.exists() and src.name not in seen:
                        seen.add(src.name)
                        dst = docs_dir / src.name
                        try:
                            shutil.copy2(src, dst)
                            stats['documents'] += 1
                        except Exception as e:
                            pass

            # Сохраняем info.json с видео и текстами
            info = {
                'product_id': product_id,
                'name': self.product_patterns.get(product_id, {}).get('name', product_id),
                'category': self.product_patterns.get(product_id, {}).get('category', 'other'),
                'videos': list({v['url'] for v in data['videos']}),  # Уникальные видео
                'photo_count': len(data['photos']),
                'document_count': len(data['documents']),
            }

            with open(product_dir / 'info.json', 'w', encoding='utf-8') as f:
                json.dump(info, f, ensure_ascii=False, indent=2)

            # Сохраняем FAQ если есть
            if data['faq']:
                faq_path = product_dir / 'faq.txt'
                with open(faq_path, 'w', encoding='utf-8') as f:
                    f.write(f"# FAQ по {info['name']}\n\n")
                    seen_texts = set()
                    for item in data['faq']:
                        text_hash = item['text'][:100]
                        if text_hash not in seen_texts:
                            seen_texts.add(text_hash)
                            f.write(f"---\n{item['text']}\n\n")

            # Сохраняем описания/тексты
            if data['texts']:
                texts_path = product_dir / 'descriptions.txt'
                with open(texts_path, 'w', encoding='utf-8') as f:
                    f.write(f"# Описания {info['name']}\n\n")
                    seen_texts = set()
                    for item in data['texts'][:50]:  # Топ 50
                        text_hash = item['text'][:100]
                        if text_hash not in seen_texts:
                            seen_texts.add(text_hash)
                            f.write(f"---\n{item['text']}\n\n")

        print(f"\nСкопировано:")
        print(f"  Фото: {stats['photos']}")
        print(f"  Документы: {stats['documents']}")
        print(f"\nПапка: {output_base}")

        return output_base

    def create_summary_report(self, output_base: Path):
        """Создаёт сводный отчёт"""
        print("\n" + "=" * 60)
        print("СОЗДАНИЕ СВОДНОГО ОТЧЁТА")
        print("=" * 60)

        report_path = output_base / 'SUMMARY.md'

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("# Материалы NL International\n\n")
            f.write(f"Дата обработки: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
            f.write("## Структура по продуктам\n\n")

            # Группируем по категориям
            categories = defaultdict(list)
            for product_id, data in self.products_data.items():
                if any([data['photos'], data['documents'], data['videos']]):
                    cat = self.product_patterns.get(product_id, {}).get('category', 'other')
                    categories[cat].append((product_id, data))

            category_names = {
                'functional_food': '🍽️ Функциональное питание',
                'supplements': '💊 БАДы и добавки',
                'beauty': '✨ Красота',
                'cosmetics': '🧴 Косметика',
                'baby': '👶 Детская линейка',
                'detox': '🌿 Детокс',
                'weight_loss': '⚖️ Похудение',
                'tea': '🍵 Чаи',
                'sport': '💪 Спорт',
                'business': '💼 Бизнес',
                'other': '📦 Другое',
            }

            for cat, cat_name in category_names.items():
                if cat in categories:
                    f.write(f"\n### {cat_name}\n\n")
                    for product_id, data in categories[cat]:
                        name = self.product_patterns.get(product_id, {}).get('name', product_id)
                        f.write(f"#### {name}\n")
                        f.write(f"- Фото: {len(data['photos'])}\n")
                        f.write(f"- Документы: {len(data['documents'])}\n")
                        if data['videos']:
                            f.write(f"- Видео: {len(data['videos'])}\n")
                            for v in list(set(v['url'] for v in data['videos']))[:5]:
                                f.write(f"  - {v}\n")
                        f.write("\n")

            # Все YouTube ссылки
            f.write("\n## Все видео-ссылки\n\n")
            all_videos = set()
            for data in self.products_data.values():
                for v in data['videos']:
                    all_videos.add(v['url'])

            for url in sorted(all_videos):
                f.write(f"- {url}\n")

        print(f"Отчёт сохранён: {report_path}")

    def run(self):
        """Главная функция"""
        if not self.load_export():
            return False

        self.process_messages()
        output_base = self.organize_to_folders()
        self.create_summary_report(output_base)

        print("\n" + "=" * 60)
        print("ГОТОВО!")
        print("=" * 60)
        print(f"\nМатериалы организованы в: {output_base}")
        print("\nСтруктура:")
        print("  /product_name/")
        print("    /photos/       - Фото продукта")
        print("    /documents/    - PDF, презентации")
        print("    info.json      - Метаданные и YouTube ссылки")
        print("    faq.txt        - Вопросы-ответы")
        print("    descriptions.txt - Описания")

        return True


def main():
    if len(sys.argv) > 1:
        export_path = sys.argv[1]
    else:
        export_path = input("Путь к папке с экспортом: ").strip('"')

    if not Path(export_path).exists():
        print(f"[ERROR] Папка не найдена: {export_path}")
        return

    organizer = NLMaterialsOrganizer(export_path)
    organizer.run()


if __name__ == "__main__":
    main()
