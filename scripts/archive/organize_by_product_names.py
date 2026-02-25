"""
Организация материалов по КОНКРЕТНЫМ названиям продуктов

Анализирует структуру чата:
1. Название продукта (короткое сообщение с эмодзи)
2. Описание/презентация
3. Вопрос-ответы
4. Фото

Группирует всё по конкретным продуктам (не линейкам!)

Использование:
    python scripts/organize_by_product_names.py "путь/к/экспорту"
"""

import json
import re
import shutil
from pathlib import Path
from collections import defaultdict
from datetime import datetime
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


class ProductNameOrganizer:
    def __init__(self, export_path: str):
        self.export_path = Path(export_path)
        self.messages = []

        # Результаты по продуктам
        self.products = defaultdict(lambda: {
            'name': '',
            'photos': [],
            'documents': [],
            'texts': [],
            'faq': [],
        })

        # Служебные фразы которые НЕ являются названиями продуктов
        self.skip_phrases = [
            'выберите продукт', 'про какой продукт', 'вопрос-ответ', 'вопрос ответ',
            'презентация', 'фото для соцсетей', 'применение', 'состав стартовых',
            'главное меню', 'голосовые ответы', 'еще истории', 'другие вкусы',
            'другой вопрос', 'выбери тему', 'выбери свой', 'для возврата',
            'для выбора языка', 'запись прямого эфира', 'главные результаты',
        ]

        # Текущий контекст (какой продукт сейчас обсуждается)
        self.current_product = None
        self.current_product_idx = 0

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

    def is_product_name(self, text: str) -> bool:
        """Определяет, является ли текст названием продукта"""
        text = text.strip()

        # Слишком короткий или длинный
        if len(text) < 3 or len(text) > 80:
            return False

        # Служебные фразы
        text_lower = text.lower()
        for phrase in self.skip_phrases:
            if phrase in text_lower:
                return False

        # Название должно начинаться с эмодзи или заглавной буквы
        if not re.match(r'^[\U0001F300-\U0001F9FF\U0001FA00-\U0001FAFF]|^[A-ZА-ЯЁ]', text):
            return False

        # Не должно быть длинным вопросом
        if '?' in text and len(text) > 50:
            return False

        return True

    def clean_product_name(self, name: str) -> str:
        """Очищает название продукта для использования как ID"""
        # Убираем эмодзи
        clean = re.sub(r'[\U0001F300-\U0001F9FF\U0001FA00-\U0001FAFF]', '', name)
        # Убираем спецсимволы
        clean = re.sub(r'[^\w\s-]', '', clean)
        # Нормализуем пробелы
        clean = ' '.join(clean.split())
        # Для имени файла
        safe = clean.strip().replace(' ', '_').lower()
        return safe if safe else 'unknown'

    def process_messages(self):
        """Обрабатывает сообщения с отслеживанием текущего продукта"""
        print("\n" + "=" * 60)
        print("АНАЛИЗ СТРУКТУРЫ ЧАТА")
        print("=" * 60)

        current_product_id = None
        current_product_name = None
        messages_since_product = 0

        for idx, msg in enumerate(self.messages):
            if idx % 1000 == 0:
                print(f"Обработано: {idx}/{len(self.messages)}")

            text = self.get_text(msg)
            text_stripped = text.strip()

            # Проверяем, это название нового продукта?
            if self.is_product_name(text_stripped) and len(text_stripped) < 60:
                # Это похоже на название продукта
                new_product_id = self.clean_product_name(text_stripped)

                # Обновляем текущий контекст
                if new_product_id and new_product_id != 'unknown':
                    current_product_id = new_product_id
                    current_product_name = text_stripped
                    messages_since_product = 0

                    # Инициализируем продукт
                    if not self.products[current_product_id]['name']:
                        self.products[current_product_id]['name'] = current_product_name

            # Если у нас есть текущий продукт и это недалеко от его названия
            if current_product_id and messages_since_product < 20:
                messages_since_product += 1

                # Обрабатываем фото
                if msg.get('photo'):
                    photo_path = self.export_path / msg['photo']
                    if photo_path.exists():
                        self.products[current_product_id]['photos'].append({
                            'path': str(photo_path),
                            'filename': msg['photo'],
                            'date': msg.get('date', ''),
                        })

                # Обрабатываем документы
                if msg.get('file'):
                    file_path = self.export_path / msg['file']
                    self.products[current_product_id]['documents'].append({
                        'path': str(file_path),
                        'filename': msg['file'],
                        'date': msg.get('date', ''),
                    })

                # Обрабатываем тексты
                if text_stripped and len(text_stripped) > 100:
                    # Это FAQ или описание?
                    if '?' in text_stripped or 'ответ' in text_stripped.lower():
                        self.products[current_product_id]['faq'].append({
                            'text': text_stripped,
                            'date': msg.get('date', ''),
                        })
                    else:
                        self.products[current_product_id]['texts'].append({
                            'text': text_stripped,
                            'date': msg.get('date', ''),
                        })

        # Статистика
        print("\n" + "-" * 40)
        print(f"НАЙДЕНО ПРОДУКТОВ: {len(self.products)}")
        print("-" * 40)

        # Топ продуктов по количеству материалов
        sorted_products = sorted(
            self.products.items(),
            key=lambda x: len(x[1]['photos']) + len(x[1]['documents']),
            reverse=True
        )

        for product_id, data in sorted_products[:30]:
            total = len(data['photos']) + len(data['documents']) + len(data['texts'])
            print(f"  {data['name'][:40]}: {len(data['photos'])} фото, {len(data['documents'])} док, {len(data['texts'])} текст")

    def organize_to_folders(self):
        """Организует по папкам"""
        print("\n" + "=" * 60)
        print("СОЗДАНИЕ СТРУКТУРЫ ПАПОК")
        print("=" * 60)

        output_base = Path(__file__).parent.parent / 'content' / 'nl_products_detailed'
        output_base.mkdir(parents=True, exist_ok=True)

        stats = {'products': 0, 'photos': 0, 'documents': 0}

        for product_id, data in self.products.items():
            # Пропускаем пустые
            if not data['photos'] and not data['documents'] and not data['texts']:
                continue

            # Создаём папку продукта
            product_dir = output_base / product_id
            product_dir.mkdir(exist_ok=True)
            stats['products'] += 1

            # Копируем фото
            if data['photos']:
                photos_dir = product_dir / 'photos'
                photos_dir.mkdir(exist_ok=True)

                seen = set()
                for idx, photo in enumerate(data['photos']):
                    src = Path(photo['path'])
                    if src.exists() and src.name not in seen:
                        seen.add(src.name)
                        # Имя: product_0001.jpg
                        ext = src.suffix
                        new_name = f"{product_id}_{idx:04d}{ext}"
                        dst = photos_dir / new_name
                        try:
                            shutil.copy2(src, dst)
                            stats['photos'] += 1
                        except:
                            pass

            # Копируем документы
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
                        except:
                            pass

            # Сохраняем тексты
            if data['texts'] or data['faq']:
                # Описания
                if data['texts']:
                    with open(product_dir / 'description.txt', 'w', encoding='utf-8') as f:
                        f.write(f"# {data['name']}\n\n")
                        for item in data['texts']:
                            f.write(f"{item['text']}\n\n---\n\n")

                # FAQ
                if data['faq']:
                    with open(product_dir / 'faq.txt', 'w', encoding='utf-8') as f:
                        f.write(f"# FAQ: {data['name']}\n\n")
                        for item in data['faq']:
                            f.write(f"{item['text']}\n\n---\n\n")

            # Метаданные
            with open(product_dir / 'info.json', 'w', encoding='utf-8') as f:
                json.dump({
                    'product_id': product_id,
                    'name': data['name'],
                    'photos_count': len(data['photos']),
                    'documents_count': len(data['documents']),
                    'texts_count': len(data['texts']),
                    'faq_count': len(data['faq']),
                }, f, ensure_ascii=False, indent=2)

        print(f"\nСоздано папок продуктов: {stats['products']}")
        print(f"Скопировано фото: {stats['photos']}")
        print(f"Скопировано документов: {stats['documents']}")
        print(f"\nПапка: {output_base}")

        return output_base

    def create_index(self, output_base: Path):
        """Создаёт индекс всех продуктов"""
        index_path = output_base / 'INDEX.md'

        with open(index_path, 'w', encoding='utf-8') as f:
            f.write("# Каталог продуктов NL International\n\n")
            f.write(f"Дата создания: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")

            # Группируем по первой букве
            sorted_products = sorted(self.products.items(), key=lambda x: x[1]['name'].lower())

            current_letter = ''
            for product_id, data in sorted_products:
                if not data['photos'] and not data['documents']:
                    continue

                first_letter = data['name'][0].upper() if data['name'] else '?'
                # Убираем эмодзи из первой буквы
                if ord(first_letter) > 127:
                    first_letter = data['name'].lstrip()
                    for c in first_letter:
                        if c.isalpha():
                            first_letter = c.upper()
                            break
                    else:
                        first_letter = '#'

                if first_letter != current_letter:
                    current_letter = first_letter
                    f.write(f"\n## {current_letter}\n\n")

                f.write(f"### [{data['name']}]({product_id}/)\n")
                f.write(f"- Фото: {len(data['photos'])}\n")
                f.write(f"- Документы: {len(data['documents'])}\n")
                if data['faq']:
                    f.write(f"- FAQ: {len(data['faq'])}\n")
                f.write("\n")

        print(f"Индекс: {index_path}")

    def run(self):
        """Главная функция"""
        if not self.load_export():
            return False

        self.process_messages()
        output_base = self.organize_to_folders()
        self.create_index(output_base)

        print("\n" + "=" * 60)
        print("ГОТОВО!")
        print("=" * 60)

        return True


def main():
    if len(sys.argv) > 1:
        export_path = sys.argv[1]
    else:
        export_path = input("Путь к папке с экспортом: ").strip('"')

    if not Path(export_path).exists():
        print(f"[ERROR] Папка не найден: {export_path}")
        return

    organizer = ProductNameOrganizer(export_path)
    organizer.run()


if __name__ == "__main__":
    main()
