"""
Копирование фото из Telegram экспортов в unified_products

Анализирует контекст соседних сообщений для определения продукта,
удаляет дубликаты по хешу, копирует в unified_products/[product]/photos/

Использование:
    python scripts/copy_photos_from_exports.py "путь/к/экспорту"
"""

import json
import re
import shutil
import hashlib
from pathlib import Path
from collections import defaultdict
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


class PhotoCopier:
    def __init__(self, export_path: str):
        self.export_path = Path(export_path)
        self.messages = []

        # Выходная папка
        self.base_dir = Path(__file__).parent.parent
        self.unified_products_dir = self.base_dir / 'content' / 'unified_products'

        # Существующие хеши для дедупликации
        self.existing_hashes = set()

        # Статистика
        self.stats = {
            'photos_total': 0,
            'photos_copied': 0,
            'duplicates_skipped': 0,
            'by_product': defaultdict(int),
        }

        # Паттерны продуктов
        self.product_patterns = {
            'energy_diet': {
                'patterns': [r'energy\s*diet', r'энерджи\s*дайет', r'функциональное питание'],
                'weight': 10
            },
            'ed_smart': {
                'patterns': [r'ed\s*smart', r'смарт'],
                'weight': 15
            },
            'greenflash': {
                'patterns': [r'green\s*flash', r'greenflash', r'грин\s*флеш', r'lymph', r'лимф', r'gyan', r'гьян'],
                'weight': 12
            },
            'collagen': {
                'patterns': [r'collagen', r'коллаген'],
                'weight': 15
            },
            'draineffect': {
                'patterns': [r'drain\s*effect', r'draineffect', r'драйн', r'детокс'],
                'weight': 12
            },
            'omega': {
                'patterns': [r'omega', r'омега', r'рыбий жир', r'dha'],
                'weight': 12
            },
            '3d_slim': {
                'patterns': [r'3d\s*slim', r'слим'],
                'weight': 12
            },
            'calcium': {
                'patterns': [r'calcium', r'кальций'],
                'weight': 15
            },
            'occuba': {
                'patterns': [r'occuba', r'оккуба'],
                'weight': 15
            },
            'beloved': {
                'patterns': [r'be\s*loved', r'белавед', r'косметик'],
                'weight': 12
            },
            'nlka': {
                'patterns': [r"nl'?ka", r'нлка', r'для детей', r'детское'],
                'weight': 12
            },
            'prohelper': {
                'patterns': [r'prohelper', r'прохелпер'],
                'weight': 15
            },
            'happy_smile': {
                'patterns': [r'happy\s*smile', r'зубная паста', r'зубн'],
                'weight': 12
            },
            'sport': {
                'patterns': [r'протеин', r'спортивн', r'bcaa', r'protein'],
                'weight': 10
            },
            'imperial_herb': {
                'patterns': [r'imperial\s*herb', r'империал', r'травяной чай', r'аюрвед'],
                'weight': 12
            },
            'vitamin_d': {
                'patterns': [r'витамин\s*d', r'vitamin\s*d', r'витамин д'],
                'weight': 12
            },
            'biotuning': {
                'patterns': [r'biotuning', r'биотюнинг'],
                'weight': 15
            },
            'biodrone': {
                'patterns': [r'biodrone', r'биодрон'],
                'weight': 15
            },
            'lovely': {
                'patterns': [r'lovely', r'лавли'],
                'weight': 12
            },
            'enerwood': {
                'patterns': [r'enerwood', r'энервуд'],
                'weight': 15
            },
            'antiage': {
                'patterns': [r'anti.*age', r'антиэйдж', r'анти.*возраст'],
                'weight': 10
            },
            'starter_kit': {
                'patterns': [r'стартов\w+\s*набор', r'starter\s*kit'],
                'weight': 10
            },
        }

        # Контекстное окно
        self.context_window = 5

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

        self.channel_name = data.get('name', 'Unknown')
        self.messages = [m for m in data.get('messages', []) if m.get('type') == 'message']

        # Считаем фото
        photos = [m for m in self.messages if m.get('photo')]
        self.stats['photos_total'] = len(photos)

        print(f"Канал: {self.channel_name}")
        print(f"Сообщений: {len(self.messages)}")
        print(f"Фото: {self.stats['photos_total']}")

        return True

    def load_existing_hashes(self):
        """Загружает хеши существующих фото"""
        print("\n" + "=" * 60)
        print("ЗАГРУЗКА СУЩЕСТВУЮЩИХ ХЕШЕЙ")
        print("=" * 60)

        for photo in self.unified_products_dir.rglob('*.jpg'):
            try:
                self.existing_hashes.add(self._file_hash(photo))
            except Exception:
                pass

        for photo in self.unified_products_dir.rglob('*.png'):
            try:
                self.existing_hashes.add(self._file_hash(photo))
            except Exception:
                pass

        print(f"Загружено хешей: {len(self.existing_hashes)}")

    def _file_hash(self, filepath: Path) -> str:
        """MD5 хеш файла"""
        hasher = hashlib.md5()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                hasher.update(chunk)
        return hasher.hexdigest()

    def _get_text(self, msg: dict) -> str:
        """Извлекает текст"""
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

    def _get_context(self, idx: int) -> str:
        """Получает контекст вокруг сообщения"""
        texts = []
        start = max(0, idx - self.context_window)
        end = min(len(self.messages), idx + self.context_window + 1)

        for i in range(start, end):
            texts.append(self._get_text(self.messages[i]))

        return ' '.join(texts)

    def _detect_product(self, text: str) -> str:
        """Определяет продукт по тексту"""
        text_lower = text.lower()
        scores = defaultdict(int)

        for product_id, info in self.product_patterns.items():
            for pattern in info['patterns']:
                matches = re.findall(pattern, text_lower, re.IGNORECASE)
                scores[product_id] += len(matches) * info['weight']

        if not scores:
            return 'general'

        best = max(scores.items(), key=lambda x: x[1])
        if best[1] >= 5:
            return best[0]
        return 'general'

    def copy_photos(self):
        """Копирует фото"""
        print("\n" + "=" * 60)
        print("КОПИРОВАНИЕ ФОТО")
        print("=" * 60)

        for idx, msg in enumerate(self.messages):
            if idx % 500 == 0:
                print(f"Обработано: {idx}/{len(self.messages)}")

            if not msg.get('photo'):
                continue

            # Путь к фото
            photo_rel = msg['photo']
            photo_path = self.export_path / photo_rel

            if not photo_path.exists():
                continue

            # Проверяем дубликат
            try:
                photo_hash = self._file_hash(photo_path)
                if photo_hash in self.existing_hashes:
                    self.stats['duplicates_skipped'] += 1
                    continue
            except Exception:
                continue

            # Определяем продукт по контексту
            context = self._get_context(idx)
            product = self._detect_product(context)

            # Создаём папку продукта
            product_dir = self.unified_products_dir / product / 'photos'
            product_dir.mkdir(parents=True, exist_ok=True)

            # Уникальное имя
            date_str = msg.get('date', '')[:10].replace('-', '')
            new_name = f"{product}_{date_str}_{photo_path.name}"
            dst = product_dir / new_name

            # Проверяем существование
            counter = 1
            while dst.exists():
                new_name = f"{product}_{date_str}_{counter}_{photo_path.name}"
                dst = product_dir / new_name
                counter += 1

            try:
                shutil.copy2(photo_path, dst)
                self.existing_hashes.add(photo_hash)
                self.stats['photos_copied'] += 1
                self.stats['by_product'][product] += 1
            except Exception as e:
                print(f"  [WARN] Ошибка: {e}")

        print(f"\nСкопировано: {self.stats['photos_copied']}")
        print(f"Дубликатов пропущено: {self.stats['duplicates_skipped']}")

    def update_index(self):
        """Обновляет индекс"""
        index_path = self.unified_products_dir / '_index.json'

        if index_path.exists():
            with open(index_path, 'r', encoding='utf-8') as f:
                index = json.load(f)
        else:
            index = {'products': {}, 'last_updated': ''}

        for product_dir in self.unified_products_dir.iterdir():
            if product_dir.is_dir() and not product_dir.name.startswith('_'):
                product_id = product_dir.name
                photos_dir = product_dir / 'photos'
                docs_dir = product_dir / 'documents'

                index['products'][product_id] = {
                    'photos_count': len(list(photos_dir.glob('*'))) if photos_dir.exists() else 0,
                    'documents_count': len(list(docs_dir.glob('*'))) if docs_dir.exists() else 0,
                }

        from datetime import datetime
        index['last_updated'] = datetime.now().isoformat()

        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(index, f, ensure_ascii=False, indent=2)

        print(f"\nОбновлён индекс: {index_path}")

    def print_summary(self):
        """Выводит статистику"""
        print("\n" + "=" * 60)
        print("СТАТИСТИКА ПО ПРОДУКТАМ")
        print("=" * 60)

        for product, count in sorted(self.stats['by_product'].items(), key=lambda x: -x[1]):
            print(f"  {product}: {count} фото")

        print("\n" + "=" * 60)
        print("ИТОГО")
        print("=" * 60)
        print(f"Фото в экспорте: {self.stats['photos_total']}")
        print(f"Скопировано: {self.stats['photos_copied']}")
        print(f"Дубликатов: {self.stats['duplicates_skipped']}")

    def run(self):
        """Главная функция"""
        print("\n" + "=" * 60)
        print("КОПИРОВАНИЕ ФОТО ИЗ TELEGRAM ЭКСПОРТА")
        print("=" * 60)
        print(f"Путь: {self.export_path}\n")

        if not self.load_export():
            return False

        self.load_existing_hashes()
        self.copy_photos()
        self.update_index()
        self.print_summary()

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
        print(f"[ERROR] Папка не найдена: {export_path}")
        return

    copier = PhotoCopier(export_path)
    copier.run()


if __name__ == "__main__":
    main()
