"""
Обработка Telegram экспортов V3 - с поддержкой разных типов и дедупликацией

Типы экспортов:
- assistant: NL Assistant AI (бот с Q&A, фото продуктов)
- university: NL University (обучающий контент)
- news: NL_News (новости компании, фильтрация по датам)

ВАЖНО:
- Дедуплицирует с существующими данными в knowledge_base
- Копирует фото в unified_products/[product]/photos/
- Извлекает Q&A пары из бота assistant

Использование:
    python scripts/process_telegram_exports_v3.py --export-path "путь" --export-type assistant
"""

import json
import re
import shutil
import hashlib
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


class TelegramExportProcessor:
    def __init__(self, export_path: str, export_type: str):
        self.export_path = Path(export_path)
        self.export_type = export_type
        self.messages = []
        self.channel_name = ''

        # Пути к выходным папкам
        self.base_dir = Path(__file__).parent.parent
        self.content_dir = self.base_dir / 'content'
        self.unified_products_dir = self.content_dir / 'unified_products'
        self.knowledge_base_dir = self.content_dir / 'knowledge_base'

        # Существующие данные для дедупликации
        self.existing_texts = set()
        self.existing_photo_hashes = set()

        # Результаты
        self.extracted = {
            'qa_pairs': [],           # Q&A из assistant бота
            'training': [],           # Обучающий контент
            'products': [],           # Информация о продуктах
            'news': [],               # Новости (только 2024-2026)
            'photos': [],             # Фото для копирования
        }

        # Статистика
        self.stats = {
            'messages_total': 0,
            'messages_processed': 0,
            'duplicates_skipped': 0,
            'photos_copied': 0,
            'qa_pairs_found': 0,
            'documents_created': 0,
        }

        # Паттерны продуктов (для привязки фото)
        self.product_patterns = {
            'energy_diet': [r'energy\s*diet', r'энерджи\s*дайет', r'\bed\b'],
            'ed_smart': [r'ed\s*smart', r'смарт.*ed', r'эд.*смарт'],
            'greenflash': [r'green\s*flash', r'greenflash', r'грин.*флеш'],
            'collagen': [r'collagen', r'коллаген'],
            'draineffect': [r'drain\s*effect', r'draineffect', r'драйн'],
            'omega': [r'omega', r'омега'],
            '3d_slim': [r'3d\s*slim', r'слим'],
            'calcium': [r'calcium', r'кальций'],
            'occuba': [r'occuba', r'оккуба'],
            'beloved': [r'be\s*loved', r'белавед'],
            'nlka': [r"nl'?ka", r'нлка', r'для детей'],
            'prohelper': [r'prohelper', r'прохелпер'],
            'happy_smile': [r'happy\s*smile', r'зубная паста'],
            'sport': [r'протеин', r'спортивн', r'bcaa'],
            'imperial_herb': [r'imperial\s*herb', r'травяной чай'],
            'vitamin_d': [r'витамин\s*d', r'vitamin\s*d'],
            'biotuning': [r'biotuning', r'биотюнинг'],
            'biodrone': [r'biodrone', r'биодрон'],
        }

        # Фильтр дат для news
        self.min_date = datetime(2024, 1, 1)

    def load_export(self) -> bool:
        """Загружает данные из экспорта"""
        print("=" * 60)
        print(f"ЗАГРУЗКА ЭКСПОРТА: {self.export_type.upper()}")
        print("=" * 60)

        result_json = self.export_path / 'result.json'
        if not result_json.exists():
            print(f"[ERROR] Файл не найден: {result_json}")
            return False

        with open(result_json, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.channel_name = data.get('name', 'Unknown')
        all_messages = data.get('messages', [])

        # Фильтруем только сообщения
        self.messages = [m for m in all_messages if m.get('type') == 'message']
        self.stats['messages_total'] = len(self.messages)

        print(f"Канал: {self.channel_name}")
        print(f"Сообщений: {self.stats['messages_total']}")

        return True

    def load_existing_data(self):
        """Загружает существующие данные для дедупликации"""
        print("\n" + "=" * 60)
        print("ЗАГРУЗКА СУЩЕСТВУЮЩИХ ДАННЫХ ДЛЯ ДЕДУПЛИКАЦИИ")
        print("=" * 60)

        # Загружаем тексты из knowledge_base
        kb_dir = self.knowledge_base_dir
        if kb_dir.exists():
            for txt_file in kb_dir.rglob('*.txt'):
                try:
                    text = txt_file.read_text(encoding='utf-8')
                    # Берём первые 100 символов каждого абзаца
                    for para in text.split('\n\n'):
                        prefix = para.strip()[:100].lower()
                        if len(prefix) > 20:
                            self.existing_texts.add(prefix)
                except Exception:
                    pass

            for md_file in kb_dir.rglob('*.md'):
                try:
                    text = md_file.read_text(encoding='utf-8')
                    for para in text.split('\n\n'):
                        prefix = para.strip()[:100].lower()
                        if len(prefix) > 20:
                            self.existing_texts.add(prefix)
                except Exception:
                    pass

        # Загружаем хеши фото из unified_products
        if self.unified_products_dir.exists():
            for photo in self.unified_products_dir.rglob('*.jpg'):
                try:
                    self.existing_photo_hashes.add(self._file_hash(photo))
                except Exception:
                    pass
            for photo in self.unified_products_dir.rglob('*.png'):
                try:
                    self.existing_photo_hashes.add(self._file_hash(photo))
                except Exception:
                    pass

        print(f"Загружено текстов: {len(self.existing_texts)}")
        print(f"Загружено хешей фото: {len(self.existing_photo_hashes)}")

    def _file_hash(self, filepath: Path) -> str:
        """Вычисляет MD5 хеш файла"""
        hasher = hashlib.md5()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                hasher.update(chunk)
        return hasher.hexdigest()

    def _get_text(self, msg: dict) -> str:
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

    def _is_duplicate_text(self, text: str) -> bool:
        """Проверяет, является ли текст дубликатом"""
        prefix = text.strip()[:100].lower()
        if prefix in self.existing_texts:
            return True
        return False

    def _detect_product(self, text: str) -> str:
        """Определяет продукт по тексту"""
        text_lower = text.lower()
        for product_id, patterns in self.product_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    return product_id
        return 'general'

    def _parse_date(self, date_str: str) -> datetime:
        """Парсит дату из строки"""
        try:
            return datetime.fromisoformat(date_str.replace('T', ' ').split('.')[0])
        except Exception:
            return datetime(2020, 1, 1)

    def process_assistant_export(self):
        """Обработка экспорта NL Assistant AI (бот с Q&A)"""
        print("\n" + "=" * 60)
        print("ОБРАБОТКА NL ASSISTANT AI")
        print("=" * 60)

        # В боте структура: вопрос пользователя -> ответ бота
        # Ищем пары сообщений
        for i, msg in enumerate(self.messages):
            text = self._get_text(msg)
            if not text.strip():
                continue

            # Обрабатываем фото
            if msg.get('photo'):
                photo_path = self.export_path / msg['photo']
                if photo_path.exists():
                    # Проверяем дубликат по хешу
                    try:
                        photo_hash = self._file_hash(photo_path)
                        if photo_hash not in self.existing_photo_hashes:
                            product = self._detect_product(text)
                            self.extracted['photos'].append({
                                'path': str(photo_path),
                                'hash': photo_hash,
                                'product': product,
                                'context': text[:200],
                                'date': msg.get('date', ''),
                            })
                            self.existing_photo_hashes.add(photo_hash)
                    except Exception:
                        pass

            # Ищем Q&A пары (вопрос заканчивается на ?)
            if '?' in text and len(text) > 30:
                # Это вопрос, ищем ответ в следующих сообщениях
                answer = ''
                for j in range(i + 1, min(i + 3, len(self.messages))):
                    next_text = self._get_text(self.messages[j])
                    if next_text and len(next_text) > 50 and '?' not in next_text[:50]:
                        answer = next_text
                        break

                if answer and not self._is_duplicate_text(text + answer):
                    self.extracted['qa_pairs'].append({
                        'question': text,
                        'answer': answer,
                        'product': self._detect_product(text + answer),
                        'date': msg.get('date', ''),
                    })
                    self.existing_texts.add((text + answer)[:100].lower())
                    self.stats['qa_pairs_found'] += 1

            # Также сохраняем информативные тексты о продуктах
            if len(text) > 200 and not self._is_duplicate_text(text):
                product = self._detect_product(text)
                if product != 'general':
                    self.extracted['products'].append({
                        'text': text,
                        'product': product,
                        'date': msg.get('date', ''),
                    })
                    self.existing_texts.add(text[:100].lower())

            self.stats['messages_processed'] += 1

    def process_university_export(self):
        """Обработка экспорта NL University (обучение)"""
        print("\n" + "=" * 60)
        print("ОБРАБОТКА NL UNIVERSITY")
        print("=" * 60)

        # Паттерны обучающего контента
        training_patterns = [
            r'урок', r'обучен', r'курс', r'тренинг',
            r'#nlu', r'как.*делать', r'инструкц',
            r'шаг\s*\d', r'этап\s*\d', r'правил',
            r'совет', r'рекомендац', r'лайфхак',
        ]

        for msg in self.messages:
            text = self._get_text(msg)
            if not text.strip() or len(text) < 100:
                continue

            # Проверяем дубликат
            if self._is_duplicate_text(text):
                self.stats['duplicates_skipped'] += 1
                continue

            # Проверяем паттерны обучения
            is_training = any(re.search(p, text.lower()) for p in training_patterns)

            if is_training:
                self.extracted['training'].append({
                    'text': text,
                    'date': msg.get('date', ''),
                    'has_media': bool(msg.get('photo') or msg.get('file')),
                })
                self.existing_texts.add(text[:100].lower())

            self.stats['messages_processed'] += 1

    def process_news_export(self):
        """Обработка экспорта NL_News (фильтрация по датам 2024-2026)"""
        print("\n" + "=" * 60)
        print("ОБРАБОТКА NL_NEWS (2024-2026)")
        print("=" * 60)

        for msg in self.messages:
            # Фильтруем по дате
            msg_date = self._parse_date(msg.get('date', ''))
            if msg_date < self.min_date:
                continue

            text = self._get_text(msg)
            if not text.strip() or len(text) < 50:
                continue

            # Проверяем дубликат
            if self._is_duplicate_text(text):
                self.stats['duplicates_skipped'] += 1
                continue

            # Определяем категорию
            is_product = any(re.search(p, text.lower()) for patterns in self.product_patterns.values() for p in patterns)

            self.extracted['news'].append({
                'text': text,
                'date': msg.get('date', ''),
                'is_product_related': is_product,
                'product': self._detect_product(text) if is_product else 'general',
            })
            self.existing_texts.add(text[:100].lower())

            self.stats['messages_processed'] += 1

    def process(self):
        """Главный метод обработки"""
        if self.export_type == 'assistant':
            self.process_assistant_export()
        elif self.export_type == 'university':
            self.process_university_export()
        elif self.export_type == 'news':
            self.process_news_export()
        else:
            print(f"[ERROR] Неизвестный тип: {self.export_type}")
            return False
        return True

    def copy_photos_to_unified(self):
        """Копирует фото в unified_products/[product]/photos/"""
        print("\n" + "=" * 60)
        print("КОПИРОВАНИЕ ФОТО В UNIFIED_PRODUCTS")
        print("=" * 60)

        for photo in self.extracted['photos']:
            src = Path(photo['path'])
            if not src.exists():
                continue

            product = photo['product']
            product_dir = self.unified_products_dir / product / 'photos'
            product_dir.mkdir(parents=True, exist_ok=True)

            # Уникальное имя
            date_str = photo['date'][:10].replace('-', '') if photo['date'] else '00000000'
            new_name = f"{product}_{date_str}_{src.name}"
            dst = product_dir / new_name

            # Проверяем существование
            if dst.exists():
                continue

            try:
                shutil.copy2(src, dst)
                self.stats['photos_copied'] += 1
            except Exception as e:
                print(f"  [WARN] Ошибка копирования: {e}")

        print(f"Скопировано фото: {self.stats['photos_copied']}")

    def save_knowledge_base_documents(self):
        """Сохраняет документы в knowledge_base"""
        print("\n" + "=" * 60)
        print("СОХРАНЕНИЕ ДОКУМЕНТОВ В KNOWLEDGE_BASE")
        print("=" * 60)

        from_telegram_dir = self.knowledge_base_dir / 'from_telegram'
        from_telegram_dir.mkdir(parents=True, exist_ok=True)

        faq_dir = self.knowledge_base_dir / 'faq'
        faq_dir.mkdir(parents=True, exist_ok=True)

        training_dir = self.knowledge_base_dir / 'training'
        training_dir.mkdir(parents=True, exist_ok=True)

        # Сохраняем Q&A пары как FAQ
        if self.extracted['qa_pairs']:
            qa_path = faq_dir / f'qa_from_{self.export_type}_{datetime.now().strftime("%Y%m%d")}.md'
            with open(qa_path, 'w', encoding='utf-8') as f:
                f.write(f"# FAQ из {self.channel_name}\n\n")
                f.write(f"Источник: {self.export_type}\n")
                f.write(f"Дата обработки: {datetime.now().isoformat()}\n\n")
                f.write("---\n\n")

                for qa in self.extracted['qa_pairs'][:50]:  # Топ 50
                    f.write(f"## Вопрос\n\n{qa['question']}\n\n")
                    f.write(f"## Ответ\n\n{qa['answer']}\n\n")
                    if qa['product'] != 'general':
                        f.write(f"*Продукт: {qa['product']}*\n\n")
                    f.write("---\n\n")

            self.stats['documents_created'] += 1
            print(f"  Создан: {qa_path.name}")

        # Сохраняем обучающий контент
        if self.extracted['training']:
            training_path = training_dir / f'training_from_{self.export_type}_{datetime.now().strftime("%Y%m%d")}.md'
            with open(training_path, 'w', encoding='utf-8') as f:
                f.write(f"# Обучающие материалы из {self.channel_name}\n\n")
                f.write(f"Источник: {self.export_type}\n")
                f.write(f"Дата: {datetime.now().isoformat()}\n\n")
                f.write("---\n\n")

                for item in self.extracted['training'][:30]:
                    f.write(f"{item['text']}\n\n")
                    f.write("---\n\n")

            self.stats['documents_created'] += 1
            print(f"  Создан: {training_path.name}")

        # Сохраняем информацию о продуктах
        if self.extracted['products']:
            products_path = from_telegram_dir / f'products_from_{self.export_type}_{datetime.now().strftime("%Y%m%d")}.md'
            with open(products_path, 'w', encoding='utf-8') as f:
                f.write(f"# Информация о продуктах из {self.channel_name}\n\n")
                f.write("---\n\n")

                # Группируем по продуктам
                by_product = defaultdict(list)
                for item in self.extracted['products']:
                    by_product[item['product']].append(item)

                for product, items in by_product.items():
                    f.write(f"## {product.replace('_', ' ').title()}\n\n")
                    for item in items[:5]:
                        f.write(f"{item['text']}\n\n")
                        f.write("---\n\n")

            self.stats['documents_created'] += 1
            print(f"  Создан: {products_path.name}")

        # Сохраняем новости (только актуальные)
        if self.extracted['news']:
            news_path = from_telegram_dir / f'news_from_{self.export_type}_{datetime.now().strftime("%Y%m%d")}.md'
            with open(news_path, 'w', encoding='utf-8') as f:
                f.write(f"# Новости NL International (2024-2026)\n\n")
                f.write(f"Источник: {self.channel_name}\n")
                f.write("---\n\n")

                for item in self.extracted['news'][:50]:
                    f.write(f"### {item['date'][:10]}\n\n")
                    f.write(f"{item['text']}\n\n")
                    f.write("---\n\n")

            self.stats['documents_created'] += 1
            print(f"  Создан: {news_path.name}")

        print(f"\nВсего создано документов: {self.stats['documents_created']}")

    def create_index_for_unified_products(self):
        """Создаёт/обновляет индекс продуктов"""
        index_path = self.unified_products_dir / '_index.json'

        # Загружаем существующий индекс
        if index_path.exists():
            with open(index_path, 'r', encoding='utf-8') as f:
                index = json.load(f)
        else:
            index = {'products': {}, 'last_updated': ''}

        # Обновляем информацию
        for product_dir in self.unified_products_dir.iterdir():
            if product_dir.is_dir() and not product_dir.name.startswith('_'):
                product_id = product_dir.name
                photos_dir = product_dir / 'photos'
                docs_dir = product_dir / 'documents'

                index['products'][product_id] = {
                    'photos_count': len(list(photos_dir.glob('*'))) if photos_dir.exists() else 0,
                    'documents_count': len(list(docs_dir.glob('*'))) if docs_dir.exists() else 0,
                    'has_description': (product_dir / 'description.md').exists(),
                    'has_faq': (product_dir / 'faq.md').exists(),
                }

        index['last_updated'] = datetime.now().isoformat()

        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(index, f, ensure_ascii=False, indent=2)

        print(f"\nОбновлён индекс: {index_path}")

    def print_summary(self):
        """Выводит итоговую статистику"""
        print("\n" + "=" * 60)
        print("ИТОГОВАЯ СТАТИСТИКА")
        print("=" * 60)

        print(f"Тип экспорта: {self.export_type}")
        print(f"Канал: {self.channel_name}")
        print(f"\nСообщений всего: {self.stats['messages_total']}")
        print(f"Обработано: {self.stats['messages_processed']}")
        print(f"Дубликатов пропущено: {self.stats['duplicates_skipped']}")
        print(f"\nQ&A пар найдено: {self.stats['qa_pairs_found']}")
        print(f"Фото скопировано: {self.stats['photos_copied']}")
        print(f"Документов создано: {self.stats['documents_created']}")

        print("\n" + "=" * 60)
        print("ГОТОВО!")
        print("=" * 60)

    def run(self):
        """Главная функция"""
        print("\n" + "=" * 60)
        print("TELEGRAM EXPORT PROCESSOR V3")
        print("=" * 60)
        print(f"Путь: {self.export_path}")
        print(f"Тип: {self.export_type}\n")

        if not self.load_export():
            return False

        self.load_existing_data()

        if not self.process():
            return False

        self.copy_photos_to_unified()
        self.save_knowledge_base_documents()
        self.create_index_for_unified_products()
        self.print_summary()

        return True


def main():
    parser = argparse.ArgumentParser(description='Обработка Telegram экспортов для NL International')
    parser.add_argument('--export-path', required=True, help='Путь к папке с экспортом')
    parser.add_argument('--export-type', required=True, choices=['assistant', 'university', 'news'],
                        help='Тип экспорта: assistant (бот), university (обучение), news (новости)')

    args = parser.parse_args()

    if not Path(args.export_path).exists():
        print(f"[ERROR] Папка не найдена: {args.export_path}")
        return

    processor = TelegramExportProcessor(args.export_path, args.export_type)
    processor.run()


if __name__ == "__main__":
    main()
