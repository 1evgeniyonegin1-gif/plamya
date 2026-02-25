"""
Объединение фото из всех источников в unified_products

Источники:
- content/nl_products_detailed/*/photos/
- content/nl_photos_categorized/*/
- content/nl_assistant_materials/images/
- content/nl_knowledge/*/photos/

Функции:
- Определяет продукт по имени папки/файла
- Удаляет дубликаты по MD5 хешу
- Копирует в unified_products/[product]/photos/

Использование:
    python scripts/merge_photos_by_product.py
"""

import hashlib
import shutil
import re
from pathlib import Path
from collections import defaultdict
import sys
import io
import json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


class PhotoMerger:
    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        self.content_dir = self.base_dir / 'content'
        self.unified_products_dir = self.content_dir / 'unified_products'

        # Источники фото
        self.sources = [
            self.content_dir / 'nl_products_detailed',
            self.content_dir / 'nl_photos_categorized',
            self.content_dir / 'nl_assistant_materials' / 'images',
            self.content_dir / 'nl_knowledge',
        ]

        # Существующие хеши
        self.existing_hashes = set()

        # Статистика
        self.stats = {
            'photos_found': 0,
            'photos_copied': 0,
            'duplicates_skipped': 0,
            'by_product': defaultdict(int),
            'by_source': defaultdict(int),
        }

        # Нормализация названий продуктов
        self.product_aliases = {
            'energy diet': 'energy_diet',
            'energydiet': 'energy_diet',
            'ed': 'energy_diet',
            'ed smart': 'ed_smart',
            'edsmart': 'ed_smart',
            'smart': 'ed_smart',
            'green flash': 'greenflash',
            'green_flash': 'greenflash',
            'grin flash': 'greenflash',
            'коллаген': 'collagen',
            'drain effect': 'draineffect',
            'drain_effect': 'draineffect',
            'драйн': 'draineffect',
            '3d slim': '3d_slim',
            '3dslim': '3d_slim',
            'слим': '3d_slim',
            'омега': 'omega',
            'omega3': 'omega',
            'omega 3': 'omega',
            'кальций': 'calcium',
            'be loved': 'beloved',
            'be_loved': 'beloved',
            "nl'ka": 'nlka',
            'nlka': 'nlka',
            'nlka_cosmetics': 'nlka',
            'pro helper': 'prohelper',
            'pro_helper': 'prohelper',
            'happy smile': 'happy_smile',
            'happysmile': 'happy_smile',
            'imperial herb': 'imperial_herb',
            'imperial_herb': 'imperial_herb',
            'vitamin d': 'vitamin_d',
            'vitamind': 'vitamin_d',
            'витамин д': 'vitamin_d',
            'bio tuning': 'biotuning',
            'bio_tuning': 'biotuning',
            'bio drone': 'biodrone',
            'bio_drone': 'biodrone',
            'ener wood': 'enerwood',
            'ener_wood': 'enerwood',
            'sport': 'sport',
            'спорт': 'sport',
            'sport_nutrition': 'sport',
            'бизнес': 'business',
            'business': 'business',
        }

    def _file_hash(self, filepath: Path) -> str:
        """MD5 хеш файла"""
        hasher = hashlib.md5()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                hasher.update(chunk)
        return hasher.hexdigest()

    def _normalize_product_name(self, name: str) -> str:
        """Нормализует название продукта"""
        name_lower = name.lower().strip()

        # Убираем цифры в конце (ed_smart_40 -> ed_smart)
        name_clean = re.sub(r'_\d+$', '', name_lower)

        # Проверяем алиасы
        if name_clean in self.product_aliases:
            return self.product_aliases[name_clean]

        # Проверяем частичные совпадения
        for alias, normalized in self.product_aliases.items():
            if alias in name_clean:
                return normalized

        # Очищаем от спецсимволов
        name_clean = re.sub(r'[^\w\s]', '', name_clean)
        name_clean = re.sub(r'\s+', '_', name_clean).strip('_')

        return name_clean if name_clean else 'general'

    def load_existing_hashes(self):
        """Загружает хеши существующих фото в unified_products"""
        print("=" * 60)
        print("ЗАГРУЗКА СУЩЕСТВУЮЩИХ ХЕШЕЙ")
        print("=" * 60)

        if self.unified_products_dir.exists():
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

    def scan_nl_products_detailed(self):
        """Сканирует nl_products_detailed"""
        print("\n" + "=" * 60)
        print("СКАНИРОВАНИЕ nl_products_detailed")
        print("=" * 60)

        source_dir = self.content_dir / 'nl_products_detailed'
        if not source_dir.exists():
            print("Папка не найдена")
            return []

        photos = []
        for product_dir in source_dir.iterdir():
            if not product_dir.is_dir():
                continue

            photos_dir = product_dir / 'photos'
            if not photos_dir.exists():
                continue

            product_name = self._normalize_product_name(product_dir.name)

            for photo in photos_dir.glob('*.jpg'):
                photos.append({
                    'path': photo,
                    'product': product_name,
                    'source': 'nl_products_detailed',
                })
                self.stats['photos_found'] += 1

            for photo in photos_dir.glob('*.png'):
                photos.append({
                    'path': photo,
                    'product': product_name,
                    'source': 'nl_products_detailed',
                })
                self.stats['photos_found'] += 1

        print(f"Найдено: {len(photos)} фото")
        return photos

    def scan_nl_photos_categorized(self):
        """Сканирует nl_photos_categorized"""
        print("\n" + "=" * 60)
        print("СКАНИРОВАНИЕ nl_photos_categorized")
        print("=" * 60)

        source_dir = self.content_dir / 'nl_photos_categorized'
        if not source_dir.exists():
            print("Папка не найдена")
            return []

        photos = []
        for item in source_dir.iterdir():
            if item.is_file() and item.suffix.lower() in ['.jpg', '.png']:
                photos.append({
                    'path': item,
                    'product': 'general',
                    'source': 'nl_photos_categorized',
                })
                self.stats['photos_found'] += 1
            elif item.is_dir():
                product_name = self._normalize_product_name(item.name)

                for photo in item.glob('*.jpg'):
                    photos.append({
                        'path': photo,
                        'product': product_name,
                        'source': 'nl_photos_categorized',
                    })
                    self.stats['photos_found'] += 1

                for photo in item.glob('*.png'):
                    photos.append({
                        'path': photo,
                        'product': product_name,
                        'source': 'nl_photos_categorized',
                    })
                    self.stats['photos_found'] += 1

        print(f"Найдено: {len(photos)} фото")
        return photos

    def scan_nl_assistant_materials(self):
        """Сканирует nl_assistant_materials"""
        print("\n" + "=" * 60)
        print("СКАНИРОВАНИЕ nl_assistant_materials")
        print("=" * 60)

        source_dir = self.content_dir / 'nl_assistant_materials' / 'images'
        if not source_dir.exists():
            print("Папка не найдена")
            return []

        photos = []
        for item in source_dir.rglob('*.jpg'):
            # Пытаемся определить продукт по имени файла
            product = self._detect_product_from_filename(item.name)
            photos.append({
                'path': item,
                'product': product,
                'source': 'nl_assistant_materials',
            })
            self.stats['photos_found'] += 1

        for item in source_dir.rglob('*.png'):
            product = self._detect_product_from_filename(item.name)
            photos.append({
                'path': item,
                'product': product,
                'source': 'nl_assistant_materials',
            })
            self.stats['photos_found'] += 1

        print(f"Найдено: {len(photos)} фото")
        return photos

    def scan_nl_knowledge(self):
        """Сканирует nl_knowledge"""
        print("\n" + "=" * 60)
        print("СКАНИРОВАНИЕ nl_knowledge")
        print("=" * 60)

        source_dir = self.content_dir / 'nl_knowledge'
        if not source_dir.exists():
            print("Папка не найдена")
            return []

        photos = []
        for product_dir in source_dir.iterdir():
            if not product_dir.is_dir():
                continue

            product_name = self._normalize_product_name(product_dir.name)

            # Ищем фото в подпапках
            for photo in product_dir.rglob('*.jpg'):
                photos.append({
                    'path': photo,
                    'product': product_name,
                    'source': 'nl_knowledge',
                })
                self.stats['photos_found'] += 1

            for photo in product_dir.rglob('*.png'):
                photos.append({
                    'path': photo,
                    'product': product_name,
                    'source': 'nl_knowledge',
                })
                self.stats['photos_found'] += 1

        print(f"Найдено: {len(photos)} фото")
        return photos

    def _detect_product_from_filename(self, filename: str) -> str:
        """Определяет продукт по имени файла"""
        filename_lower = filename.lower()

        keywords = {
            'collagen': 'collagen',
            'коллаген': 'collagen',
            'greenflash': 'greenflash',
            'green_flash': 'greenflash',
            'draineffect': 'draineffect',
            'drain': 'draineffect',
            'omega': 'omega',
            'омега': 'omega',
            'calcium': 'calcium',
            'кальций': 'calcium',
            'ed_smart': 'ed_smart',
            'smart': 'ed_smart',
            'energy': 'energy_diet',
            '3d_slim': '3d_slim',
            'slim': '3d_slim',
            'sport': 'sport',
            'beloved': 'beloved',
            'nlka': 'nlka',
            'occuba': 'occuba',
            'happy': 'happy_smile',
        }

        for keyword, product in keywords.items():
            if keyword in filename_lower:
                return product

        return 'general'

    def copy_photos(self, photos: list):
        """Копирует фото с дедупликацией"""
        print("\n" + "=" * 60)
        print("КОПИРОВАНИЕ ФОТО")
        print("=" * 60)

        total = len(photos)
        for idx, photo_info in enumerate(photos):
            if idx % 500 == 0:
                print(f"Обработано: {idx}/{total}")

            src = photo_info['path']
            product = photo_info['product']
            source = photo_info['source']

            if not src.exists():
                continue

            # Проверяем дубликат
            try:
                photo_hash = self._file_hash(src)
                if photo_hash in self.existing_hashes:
                    self.stats['duplicates_skipped'] += 1
                    continue
            except Exception:
                continue

            # Создаём папку
            product_dir = self.unified_products_dir / product / 'photos'
            product_dir.mkdir(parents=True, exist_ok=True)

            # Уникальное имя
            new_name = f"{product}_{source}_{src.name}"
            dst = product_dir / new_name

            counter = 1
            while dst.exists():
                new_name = f"{product}_{source}_{counter}_{src.name}"
                dst = product_dir / new_name
                counter += 1

            try:
                shutil.copy2(src, dst)
                self.existing_hashes.add(photo_hash)
                self.stats['photos_copied'] += 1
                self.stats['by_product'][product] += 1
                self.stats['by_source'][source] += 1
            except Exception as e:
                pass

        print(f"\nСкопировано: {self.stats['photos_copied']}")
        print(f"Дубликатов пропущено: {self.stats['duplicates_skipped']}")

    def update_index(self):
        """Обновляет индекс"""
        index_path = self.unified_products_dir / '_index.json'

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

        for product, count in sorted(self.stats['by_product'].items(), key=lambda x: -x[1])[:20]:
            print(f"  {product}: {count} фото")

        print("\n" + "=" * 60)
        print("СТАТИСТИКА ПО ИСТОЧНИКАМ")
        print("=" * 60)

        for source, count in sorted(self.stats['by_source'].items(), key=lambda x: -x[1]):
            print(f"  {source}: {count} фото")

        print("\n" + "=" * 60)
        print("ИТОГО")
        print("=" * 60)
        print(f"Найдено всего: {self.stats['photos_found']}")
        print(f"Скопировано: {self.stats['photos_copied']}")
        print(f"Дубликатов: {self.stats['duplicates_skipped']}")

    def run(self):
        """Главная функция"""
        print("\n" + "=" * 60)
        print("ОБЪЕДИНЕНИЕ ФОТО ПО ПРОДУКТАМ")
        print("=" * 60)

        self.load_existing_hashes()

        # Собираем фото из всех источников
        all_photos = []
        all_photos.extend(self.scan_nl_products_detailed())
        all_photos.extend(self.scan_nl_photos_categorized())
        all_photos.extend(self.scan_nl_assistant_materials())
        all_photos.extend(self.scan_nl_knowledge())

        print(f"\n{'='*60}")
        print(f"ВСЕГО НАЙДЕНО: {len(all_photos)} фото")
        print(f"{'='*60}")

        # Копируем
        self.copy_photos(all_photos)

        # Обновляем индекс
        self.update_index()

        # Выводим статистику
        self.print_summary()

        print("\n" + "=" * 60)
        print("ГОТОВО!")
        print("=" * 60)


def main():
    merger = PhotoMerger()
    merger.run()


if __name__ == "__main__":
    main()
