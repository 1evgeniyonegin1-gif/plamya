"""
Категоризация фото по контексту соседних сообщений

Анализирует сообщения ДО и ПОСЛЕ фото в чате,
чтобы определить к какому продукту оно относится.

Использование:
    python scripts/categorize_photos_by_context.py "путь/к/экспорту"
"""

import json
import re
import shutil
from pathlib import Path
from collections import defaultdict
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


class PhotoContextCategorizer:
    def __init__(self, export_path: str):
        self.export_path = Path(export_path)
        self.messages = []

        # Результаты
        self.categorized_photos = defaultdict(list)

        # Продукты с весами (более специфичные паттерны имеют больший вес)
        self.product_patterns = {
            # Energy Diet линейка
            'energy_diet': {
                'patterns': [
                    (r'energy\s*diet', 10),
                    (r'энерджи\s*дайет', 10),
                    (r'энерджи\s*диет', 10),
                    (r'функциональное питание', 5),
                    (r'\bed\b', 3),
                ],
                'name': 'Energy Diet'
            },
            'ed_smart': {
                'patterns': [
                    (r'ed\s*smart', 15),
                    (r'смарт', 5),
                ],
                'name': 'ED Smart'
            },

            # GreenFlash
            'greenflash': {
                'patterns': [
                    (r'green\s*flash', 15),
                    (r'greenflash', 15),
                    (r'грин\s*флеш', 15),
                    (r'гринфлеш', 15),
                    (r'lymph', 8),
                    (r'лимф', 8),
                    (r'gyan', 5),
                    (r'гьян', 5),
                ],
                'name': 'GreenFlash'
            },

            # Collagen
            'collagen': {
                'patterns': [
                    (r'collagen', 15),
                    (r'коллаген', 15),
                    (r'коллагена', 15),
                ],
                'name': 'Collagen'
            },

            # DrainEffect
            'draineffect': {
                'patterns': [
                    (r'drain\s*effect', 15),
                    (r'draineffect', 15),
                    (r'драйн\s*эффект', 15),
                    (r'драйн', 10),
                    (r'детокс', 5),
                ],
                'name': 'DrainEffect'
            },

            # 3D Slim
            '3d_slim': {
                'patterns': [
                    (r'3d\s*slim', 15),
                    (r'3д\s*слим', 15),
                    (r'slim', 5),
                    (r'слим', 5),
                ],
                'name': '3D Slim'
            },

            # Omega
            'omega': {
                'patterns': [
                    (r'omega\s*3', 15),
                    (r'омега\s*3', 15),
                    (r'omega', 10),
                    (r'омега', 10),
                    (r'dha', 8),
                    (r'дгк', 8),
                    (r'рыбий жир', 8),
                ],
                'name': 'Omega'
            },

            # Vision Lecithin
            'vision_lecithin': {
                'patterns': [
                    (r'vision\s*lecithin', 15),
                    (r'лецитин', 12),
                    (r'lecithin', 12),
                ],
                'name': 'Vision Lecithin'
            },

            # ProHelper
            'prohelper': {
                'patterns': [
                    (r'prohelper', 15),
                    (r'прохелпер', 15),
                    (r'pro\s*helper', 15),
                ],
                'name': 'ProHelper'
            },

            # Happy Smile (зубная паста)
            'happy_smile': {
                'patterns': [
                    (r'happy\s*smile', 15),
                    (r'хэппи\s*смайл', 15),
                    (r'зубная паста', 10),
                    (r'зубн', 5),
                ],
                'name': 'Happy Smile'
            },

            # Детская линейка
            'nlka': {
                'patterns': [
                    (r"nl'?ka", 15),
                    (r'нлка', 15),
                    (r'детское питание', 10),
                    (r'для детей', 8),
                    (r'для малыш', 8),
                    (r'baby', 5),
                    (r'kids', 5),
                ],
                'name': "NL'ka"
            },

            # Occuba
            'occuba': {
                'patterns': [
                    (r'occuba', 15),
                    (r'оккуба', 15),
                ],
                'name': 'Occuba'
            },

            # Be Loved
            'beloved': {
                'patterns': [
                    (r'be\s*loved', 15),
                    (r'белавед', 15),
                ],
                'name': 'Be Loved'
            },

            # Спорт
            'sport': {
                'patterns': [
                    (r'протеин', 12),
                    (r'protein', 12),
                    (r'спортивн', 10),
                    (r'sport', 8),
                    (r'гейнер', 10),
                    (r'bcaa', 10),
                    (r'pre-workout', 10),
                ],
                'name': 'Спортивное питание'
            },

            # Calcium
            'calcium': {
                'patterns': [
                    (r'calcium', 15),
                    (r'кальций', 15),
                ],
                'name': 'Calcium'
            },

            # Imperial Herb
            'imperial_herb': {
                'patterns': [
                    (r'imperial\s*herb', 15),
                    (r'империал', 10),
                    (r'травяной чай', 10),
                ],
                'name': 'Imperial Herb'
            },

            # Бизнес
            'business': {
                'patterns': [
                    (r'стартов\w+\s*набор', 12),
                    (r'регистрац', 8),
                    (r'партнёр', 8),
                    (r'партнер', 8),
                    (r'бизнес', 5),
                    (r'маркетинг', 5),
                ],
                'name': 'Бизнес'
            },
        }

        # Контекстное окно (сколько сообщений до/после смотреть)
        self.context_window = 3

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

    def get_context_text(self, idx: int) -> str:
        """Получает текст из контекстного окна вокруг сообщения"""
        texts = []

        # Сообщения ДО
        for i in range(max(0, idx - self.context_window), idx):
            texts.append(self.get_text(self.messages[i]))

        # Само сообщение
        texts.append(self.get_text(self.messages[idx]))

        # Сообщения ПОСЛЕ
        for i in range(idx + 1, min(len(self.messages), idx + self.context_window + 1)):
            texts.append(self.get_text(self.messages[i]))

        return ' '.join(texts)

    def detect_product(self, text: str) -> tuple:
        """Определяет продукт по тексту с учётом весов"""
        text_lower = text.lower()
        scores = defaultdict(int)

        for product_id, info in self.product_patterns.items():
            for pattern, weight in info['patterns']:
                matches = re.findall(pattern, text_lower, re.IGNORECASE)
                scores[product_id] += len(matches) * weight

        if not scores:
            return 'general', 0

        # Возвращаем продукт с максимальным весом
        best_product = max(scores.items(), key=lambda x: x[1])
        return best_product[0], best_product[1]

    def categorize_photos(self):
        """Категоризирует все фото по контексту"""
        print("\n" + "=" * 60)
        print("КАТЕГОРИЗАЦИЯ ФОТО ПО КОНТЕКСТУ")
        print("=" * 60)

        stats = defaultdict(int)

        for idx, msg in enumerate(self.messages):
            if idx % 1000 == 0:
                print(f"Обработано: {idx}/{len(self.messages)}")

            if not msg.get('photo'):
                continue

            photo_path = self.export_path / msg['photo']
            if not photo_path.exists():
                continue

            # Получаем контекст
            context = self.get_context_text(idx)

            # Определяем продукт
            product_id, score = self.detect_product(context)

            # Сохраняем только если уверенность достаточная
            # Если score < 5, отправляем в general
            if score < 5:
                product_id = 'general'

            self.categorized_photos[product_id].append({
                'path': str(photo_path),
                'filename': msg['photo'],
                'score': score,
                'context_snippet': context[:200],
                'date': msg.get('date', ''),
            })

            stats[product_id] += 1

        print("\n" + "-" * 40)
        print("РЕЗУЛЬТАТЫ КАТЕГОРИЗАЦИИ:")
        print("-" * 40)

        for product_id, count in sorted(stats.items(), key=lambda x: -x[1]):
            name = self.product_patterns.get(product_id, {}).get('name', product_id)
            print(f"  {name}: {count} фото")

        return stats

    def organize_to_folders(self):
        """Организует фото по папкам"""
        print("\n" + "=" * 60)
        print("ОРГАНИЗАЦИЯ ФОТО ПО ПАПКАМ")
        print("=" * 60)

        output_base = Path(__file__).parent.parent / 'content' / 'nl_photos_categorized'
        output_base.mkdir(parents=True, exist_ok=True)

        stats = {'copied': 0, 'products': 0}

        for product_id, photos in self.categorized_photos.items():
            if not photos:
                continue

            product_dir = output_base / product_id
            product_dir.mkdir(exist_ok=True)
            stats['products'] += 1

            # Сортируем по score (лучшие первые)
            sorted_photos = sorted(photos, key=lambda x: -x['score'])

            # Копируем фото с понятными именами
            seen = set()
            product_name = self.product_patterns.get(product_id, {}).get('name', product_id)
            # Очищаем название для имени файла
            safe_name = re.sub(r'[^\w\s-]', '', product_name).strip().replace(' ', '_').lower()

            for idx, photo in enumerate(sorted_photos):
                src = Path(photo['path'])
                if src.exists() and src.name not in seen:
                    seen.add(src.name)

                    # Понятное имя: collagen_0001_score15.jpg
                    ext = src.suffix
                    new_name = f"{safe_name}_{idx:04d}_score{photo['score']}{ext}"
                    dst = product_dir / new_name

                    try:
                        shutil.copy2(src, dst)
                        stats['copied'] += 1
                    except Exception as e:
                        pass

            # Сохраняем метаданные
            meta_path = product_dir / 'metadata.json'
            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'product_id': product_id,
                    'name': self.product_patterns.get(product_id, {}).get('name', product_id),
                    'total_photos': len(photos),
                    'photos': sorted_photos[:50],  # Топ 50
                }, f, ensure_ascii=False, indent=2)

        print(f"\nСкопировано: {stats['copied']} фото")
        print(f"Папок создано: {stats['products']}")
        print(f"\nПапка: {output_base}")

        return output_base

    def create_report(self, output_base: Path):
        """Создаёт отчёт"""
        report_path = output_base / 'REPORT.md'

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("# Отчёт по категоризации фото\n\n")

            total = sum(len(p) for p in self.categorized_photos.values())
            general = len(self.categorized_photos.get('general', []))
            categorized = total - general

            f.write(f"**Всего фото:** {total}\n")
            f.write(f"**Категоризировано:** {categorized} ({categorized*100//total}%)\n")
            f.write(f"**Не удалось определить:** {general} ({general*100//total}%)\n\n")

            f.write("## По продуктам\n\n")
            for product_id, photos in sorted(self.categorized_photos.items(), key=lambda x: -len(x[1])):
                if product_id == 'general':
                    continue
                name = self.product_patterns.get(product_id, {}).get('name', product_id)
                f.write(f"### {name}\n")
                f.write(f"- Фото: {len(photos)}\n")
                avg_score = sum(p['score'] for p in photos) / len(photos) if photos else 0
                f.write(f"- Средняя уверенность: {avg_score:.1f}\n\n")

        print(f"Отчёт: {report_path}")

    def run(self):
        """Главная функция"""
        if not self.load_export():
            return False

        self.categorize_photos()
        output_base = self.organize_to_folders()
        self.create_report(output_base)

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

    categorizer = PhotoContextCategorizer(export_path)
    categorizer.run()


if __name__ == "__main__":
    main()
