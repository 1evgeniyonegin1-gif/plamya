"""
Расширенная обработка экспорта Telegram-канала NL International
Извлекает ВСЕ полезные категории контента для RAG базы знаний

Категории:
1. Рекомендации по продуктам (схемы приёма)
2. Обучающий контент (уроки, инструкции)
3. Примеры постов (шаблоны для генерации)
4. Истории успеха (результаты, до/после)
5. FAQ и ответы на возражения
6. Информация о продуктах
7. Бизнес и мотивация

ВАЖНО: Данные разделяются на:
- EVERGREEN (вечные) — без цен, акций, дат — для RAG базы знаний
- TIME_SENSITIVE (временные) — с ценами, акциями — только для примеров постов
"""

import json
import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import sys
import io

# Фикс кодировки для Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


class TelegramKnowledgeExtractor:
    def __init__(self, export_path: str):
        self.export_path = Path(export_path)
        self.messages = []
        self.extracted_content = defaultdict(list)

        # Минимальная длина текста для разных категорий
        self.min_lengths = {
            'recommendations': 200,  # Схемы приёма должны быть подробными
            'training': 150,         # Обучение может быть короче
            'post_examples': 200,    # Примеры постов - средние
            'success_stories': 100,  # Истории могут быть короткими с фото
            'faq': 100,              # Вопросы-ответы
            'products': 150,         # Описания продуктов
            'business': 150,         # Бизнес контент
            'motivation': 100,       # Мотивация
        }

        # Ключевые слова для категоризации
        self.category_patterns = {
            'recommendations': {
                'keywords': [
                    r'рекомендац', r'схема приём', r'как принимать', r'курс приёма',
                    r'программа.*похуден', r'программа.*здоров', r'комплекс.*приём',
                    r'✅.*:', r'принимать.*утр', r'принимать.*вечер', r'дозировк',
                    r'пить.*раз.*день', r'капсул.*день', r'саше.*день',
                    r'лишний вес.*:', r'диабет.*:', r'суставы.*:', r'иммунитет.*:',
                    r'для.*рекоменду', r'при.*рекоменду',
                ],
                'negative': [r'рецепт.*кулич', r'рецепт.*торт', r'готов.*блюд'],
            },
            'training': {
                'keywords': [
                    r'урок', r'обучен', r'вебинар', r'школ', r'курс',
                    r'gostories', r'инструкц', r'как.*делать', r'как.*создать',
                    r'шаг.*\d', r'этап.*\d', r'правил.*\d',
                    r'ошибк.*котор', r'секрет', r'лайфхак',
                    r'профил.*instagram', r'stories', r'reels', r'контент.*план',
                ],
                'negative': [],
            },
            'post_examples': {
                'keywords': [
                    r'пример поста', r'пост.*пример', r'шаблон', r'образец поста',
                    r'копируй', r'используй.*текст', r'готовый.*пост',
                    r'^до\s*-?\d+\s*кг', r'минус.*кг.*за', r'результат.*дн',
                ],
                'negative': [],
            },
            'success_stories': {
                'keywords': [
                    r'результат', r'похудел', r'сбросил', r'минус.*кг',
                    r'до/после', r'до и после', r'было.*стало',
                    r'история.*успех', r'мой.*путь', r'как я',
                    r'благодар.*nl', r'благодар.*energy', r'изменил.*жизнь',
                    r'-\d+\s*кг', r'ушло.*кг', r'скинул',
                ],
                'negative': [],
            },
            'faq': {
                'keywords': [
                    r'вопрос.*ответ', r'часто.*спрашива', r'faq',
                    r'почему.*\?', r'как.*\?', r'что.*если.*\?',
                    r'мифы.*о', r'правда.*о', r'заблужден',
                    r'это.*развод', r'это.*пирамид', r'это.*млм',
                    r'возражен', r'отвечать.*на',
                ],
                'negative': [],
            },
            'products': {
                'keywords': [
                    r'energy\s*diet', r'greenflash', r'green\s*flash',
                    r'collagen', r'коллаген', r'biodrone', r'биодрон',
                    r'draineffect', r'драйн', r'occuba', r'оккуба',
                    r'enerwood', r'энервуд', r'3d\s*slim', r'слим',
                    r'omega', r'омега', r'витамин', r'бад',
                    r'состав.*продукт', r'ингредиент', r'свойств.*продукт',
                ],
                'negative': [],
            },
            'business': {
                'keywords': [
                    r'бизнес', r'партнёр', r'партнер', r'структур',
                    r'квалификац', r'маркетинг.*план', r'заработ', r'доход',
                    r'регистрац.*nl', r'стать.*партнёр', r'команд',
                    r'лидер', r'наставник', r'спонсор', r'менеджер',
                    r'товарооборот', r'pv', r'бонус', r'чек',
                ],
                'negative': [],
            },
            'motivation': {
                'keywords': [
                    r'мотивац', r'вдохновен', r'верь.*себ', r'ты.*сможешь',
                    r'не сдавай', r'цель', r'мечт', r'достиг', r'успех',
                    r'измени.*жизнь', r'новая.*жизнь', r'начни.*сегодн',
                    r'возможност', r'потенциал', r'рост',
                ],
                'negative': [],
            },
        }

        # Продукты NL для тегирования
        self.nl_products = [
            'Energy Diet', 'Greenflash', 'Green Flash', 'Collagen', 'Коллаген',
            'BioDrone', 'Биодрон', 'DrainEffect', 'Драйн', 'Occuba', 'Оккуба',
            'Enerwood', 'Энервуд', '3D Slim', 'Omega', 'Омега', 'BioTuning',
            'BioSetting', 'Herbal Tea', 'Detox', 'Детокс', 'Be Loved',
        ]

        # Паттерны для определения временных данных (цены, акции, даты)
        self.time_sensitive_patterns = [
            r'\d+\s*₽',                    # 1500₽
            r'\d+\s*руб',                  # 1500 рублей
            r'\d+\s*rub',                  # 1500 rub
            r'цена\s*:?\s*\d+',            # цена: 1500
            r'стоит\s*\d+',                # стоит 1500
            r'всего\s*\d+',                # всего 1500
            r'акция',                      # акция
            r'скидк[аи]',                  # скидка/скидки
            r'промо',                      # промо
            r'только сегодня',             # только сегодня
            r'до конца (недели|месяца|года)',  # до конца месяца
            r'распродаж',                  # распродажа
            r'специальн\w+ цен',           # специальная цена
            r'вместо\s*\d+',               # вместо 2000
            r'-\d+%',                      # -20%
            r'\d+%\s*скидк',               # 20% скидка
        ]

        # Категории которые ВСЕГДА вечные (не проверяем на цены)
        self.always_evergreen = ['training', 'faq', 'motivation']

        # Категории которые нужно проверять на временные данные
        self.check_for_time_sensitive = ['products', 'recommendations', 'business', 'success_stories', 'post_examples']

    def load_export(self) -> bool:
        """Загружает данные из экспорта Telegram"""
        print("=" * 60)
        print("ЗАГРУЗКА ЭКСПОРТА TELEGRAM")
        print("=" * 60)

        result_json = self.export_path / 'result.json'

        if not result_json.exists():
            print(f"[ERROR] Файл не найден: {result_json}")
            return False

        with open(result_json, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.channel_name = data.get('name', 'Unknown')
        self.messages = data.get('messages', [])

        print(f"Канал: {self.channel_name}")
        print(f"Загружено сообщений: {len(self.messages)}")

        # Фильтруем только сообщения (не сервисные)
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

    def categorize_message(self, msg: dict) -> list:
        """Определяет категории сообщения"""
        text = self.get_text(msg).lower()
        if not text.strip():
            return []

        categories = []

        for category, patterns in self.category_patterns.items():
            # Проверяем негативные паттерны (исключения)
            skip = False
            for neg_pattern in patterns.get('negative', []):
                if re.search(neg_pattern, text, re.IGNORECASE):
                    skip = True
                    break

            if skip:
                continue

            # Проверяем позитивные паттерны
            for pattern in patterns['keywords']:
                if re.search(pattern, text, re.IGNORECASE):
                    # Проверяем минимальную длину
                    if len(text) >= self.min_lengths.get(category, 100):
                        categories.append(category)
                    break

        return categories

    def extract_products_mentioned(self, text: str) -> list:
        """Находит упомянутые продукты NL"""
        products = []
        text_lower = text.lower()
        for product in self.nl_products:
            if product.lower() in text_lower:
                products.append(product)
        return list(set(products))

    def is_time_sensitive(self, text: str) -> bool:
        """Проверяет, содержит ли текст временные данные (цены, акции)"""
        text_lower = text.lower()
        for pattern in self.time_sensitive_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True
        return False

    def clean_prices_from_text(self, text: str) -> str:
        """Удаляет цены и акционную информацию из текста для evergreen версии"""
        cleaned = text

        # Удаляем цены в рублях
        cleaned = re.sub(r'\d+\s*₽', '[цена по запросу]', cleaned)
        cleaned = re.sub(r'\d+\s*руб\w*', '[цена по запросу]', cleaned)
        cleaned = re.sub(r'\d+\s*rub\w*', '[цена по запросу]', cleaned, flags=re.IGNORECASE)

        # Удаляем конструкции "цена: XXXX"
        cleaned = re.sub(r'цена\s*:?\s*\d+\s*(₽|руб\w*)?', '[цена по запросу]', cleaned, flags=re.IGNORECASE)

        # Удаляем "стоит XXXX"
        cleaned = re.sub(r'стоит\s*\d+\s*(₽|руб\w*)?', 'стоит [цена по запросу]', cleaned, flags=re.IGNORECASE)

        # Удаляем "вместо XXXX"
        cleaned = re.sub(r'вместо\s*\d+\s*(₽|руб\w*)?', '', cleaned, flags=re.IGNORECASE)

        # Удаляем проценты скидок
        cleaned = re.sub(r'-?\d+%\s*(скидк\w*)?', '', cleaned, flags=re.IGNORECASE)

        # Удаляем "только сегодня", "до конца месяца" и т.д.
        cleaned = re.sub(r'только сегодня\s*[-—]?\s*', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'до конца\s+(недели|месяца|года)\s*', '', cleaned, flags=re.IGNORECASE)

        # Удаляем слова "акция", "промо", "распродажа" в заголовках
        cleaned = re.sub(r'🎉?\s*акция\s*🎉?', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'промо\s*:?\s*', '', cleaned, flags=re.IGNORECASE)

        # Убираем множественные пробелы и пустые строки
        cleaned = re.sub(r'  +', ' ', cleaned)
        cleaned = re.sub(r'\n\s*\n\s*\n+', '\n\n', cleaned)

        return cleaned.strip()

    def calculate_quality_score(self, msg: dict, text: str) -> int:
        """Оценивает качество контента (0-100)"""
        score = 0

        # Длина текста (макс 30 баллов)
        length = len(text)
        if length > 1000:
            score += 30
        elif length > 500:
            score += 25
        elif length > 300:
            score += 20
        elif length > 150:
            score += 10

        # Наличие структуры (макс 20 баллов)
        if re.search(r'[✅✔️☑️]', text):
            score += 10
        if re.search(r'\d+[.)\-]', text):  # Нумерованные списки
            score += 10

        # Наличие эмодзи (показатель оформленного поста) - макс 10
        emoji_count = len(re.findall(r'[\U0001F300-\U0001F9FF]', text))
        if emoji_count > 3:
            score += 10
        elif emoji_count > 0:
            score += 5

        # Упоминание продуктов NL (макс 15)
        products = self.extract_products_mentioned(text)
        score += min(len(products) * 5, 15)

        # Наличие фото (макс 10)
        if msg.get('photo'):
            score += 10

        # Наличие ссылок (макс 5)
        if 'http' in text.lower() or 't.me' in text.lower():
            score += 5

        return min(score, 100)

    def process_messages(self):
        """Обрабатывает все сообщения и категоризирует их"""
        print("\n" + "=" * 60)
        print("КАТЕГОРИЗАЦИЯ КОНТЕНТА")
        print("=" * 60)

        stats = defaultdict(int)

        for idx, msg in enumerate(self.messages):
            if idx % 2000 == 0:
                print(f"Обработано: {idx}/{len(self.messages)}")

            text = self.get_text(msg)
            if not text.strip():
                continue

            categories = self.categorize_message(msg)
            if not categories:
                continue

            # Оцениваем качество
            quality = self.calculate_quality_score(msg, text)

            # Сохраняем только качественный контент (score >= 25)
            if quality < 25:
                continue

            # Определяем временную чувствительность
            time_sensitive = self.is_time_sensitive(text)

            # Создаём запись
            entry = {
                'id': msg.get('id'),
                'date': msg.get('date', ''),
                'text': text,
                'text_cleaned': self.clean_prices_from_text(text) if time_sensitive else text,
                'author': msg.get('from', msg.get('actor', '')),
                'quality_score': quality,
                'products_mentioned': self.extract_products_mentioned(text),
                'has_photo': bool(msg.get('photo')),
                'photo_path': msg.get('photo', ''),
                'categories': categories,
                'is_time_sensitive': time_sensitive,
            }

            # Добавляем в каждую подходящую категорию
            for category in categories:
                self.extracted_content[category].append(entry)
                stats[category] += 1

        print("\nНайдено качественного контента:")
        for category, count in sorted(stats.items(), key=lambda x: -x[1]):
            print(f"  {category}: {count}")

    def deduplicate_content(self):
        """Удаляет дубликаты (похожие сообщения)"""
        print("\n" + "=" * 60)
        print("ДЕДУПЛИКАЦИЯ")
        print("=" * 60)

        for category in self.extracted_content:
            entries = self.extracted_content[category]
            original_count = len(entries)

            # Сортируем по качеству (лучшие первые)
            entries.sort(key=lambda x: -x['quality_score'])

            # Удаляем похожие (первые 100 символов совпадают)
            seen_prefixes = set()
            unique_entries = []

            for entry in entries:
                prefix = entry['text'][:100].lower().strip()
                if prefix not in seen_prefixes:
                    seen_prefixes.add(prefix)
                    unique_entries.append(entry)

            self.extracted_content[category] = unique_entries

            removed = original_count - len(unique_entries)
            if removed > 0:
                print(f"  {category}: {original_count} -> {len(unique_entries)} (-{removed} дублей)")

    def save_results(self):
        """Сохраняет результаты в файлы"""
        print("\n" + "=" * 60)
        print("СОХРАНЕНИЕ РЕЗУЛЬТАТОВ")
        print("=" * 60)

        output_dir = Path(__file__).parent.parent / 'content' / 'telegram_knowledge'
        output_dir.mkdir(exist_ok=True, parents=True)

        total_entries = 0

        for category, entries in self.extracted_content.items():
            if not entries:
                continue

            # Сортируем по качеству
            entries.sort(key=lambda x: -x['quality_score'])

            # Берём топ-100 лучших для каждой категории
            top_entries = entries[:100]

            # Сохраняем JSON
            json_path = output_dir / f'{category}.json'
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'category': category,
                    'total_found': len(entries),
                    'saved_top': len(top_entries),
                    'entries': top_entries,
                }, f, ensure_ascii=False, indent=2)

            # Сохраняем текстовый файл для RAG (только тексты)
            txt_path = output_dir / f'{category}.txt'
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(f"# {category.upper()}\n")
                f.write(f"# Извлечено из канала: {self.channel_name}\n")
                f.write(f"# Дата обработки: {datetime.now().isoformat()}\n")
                f.write(f"# Всего записей: {len(top_entries)}\n")
                f.write("=" * 60 + "\n\n")

                for i, entry in enumerate(top_entries, 1):
                    f.write(f"--- #{i} | {entry['date']} | Score: {entry['quality_score']} ---\n")
                    if entry['products_mentioned']:
                        f.write(f"Продукты: {', '.join(entry['products_mentioned'])}\n")
                    f.write(f"\n{entry['text']}\n\n")
                    f.write("-" * 40 + "\n\n")

            print(f"  {category}: {len(top_entries)} записей -> {json_path.name}")
            total_entries += len(top_entries)

        # Создаём сводный отчёт
        report = {
            'source': str(self.export_path),
            'channel_name': self.channel_name,
            'processed_date': datetime.now().isoformat(),
            'total_messages': len(self.messages),
            'categories': {}
        }

        for category, entries in self.extracted_content.items():
            report['categories'][category] = {
                'total_found': len(entries),
                'saved': min(len(entries), 100),
                'avg_quality': sum(e['quality_score'] for e in entries[:100]) / max(len(entries[:100]), 1),
            }

        report_path = output_dir / 'extraction_report.json'
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"\nИтого сохранено: {total_entries} записей")
        print(f"Папка: {output_dir}")
        print(f"Отчёт: {report_path}")

        return output_dir

    def create_rag_documents(self, output_dir: Path):
        """Создаёт документы в формате для RAG базы знаний

        Разделяет на:
        - EVERGREEN (вечные) — для RAG, используют очищенный текст без цен
        - PROMO (примеры постов с ценами) — только для генерации контента
        """
        print("\n" + "=" * 60)
        print("СОЗДАНИЕ RAG ДОКУМЕНТОВ (с разделением)")
        print("=" * 60)

        # Основная папка RAG (evergreen контент)
        rag_dir = Path(__file__).parent.parent / 'content' / 'knowledge_base' / 'from_telegram'
        rag_dir.mkdir(exist_ok=True, parents=True)

        # Папка для примеров постов с ценами (для контент-бота)
        promo_dir = Path(__file__).parent.parent / 'content' / 'knowledge_base' / 'promo_examples'
        promo_dir.mkdir(exist_ok=True, parents=True)

        # Заголовки документов
        title_map = {
            'recommendations': 'Рекомендации по продуктам NL International',
            'training': 'Обучающие материалы NL International',
            'post_examples': 'Примеры постов NL International',
            'success_stories': 'Истории успеха партнёров NL International',
            'faq': 'Часто задаваемые вопросы о NL International',
            'products': 'Информация о продуктах NL International',
            'business': 'Бизнес с NL International',
            'motivation': 'Мотивация и вдохновение NL International',
        }

        created_evergreen = 0
        created_promo = 0

        for category, entries in self.extracted_content.items():
            if not entries:
                continue

            # Сортируем по качеству
            sorted_entries = sorted(entries, key=lambda x: -x['quality_score'])

            # Разделяем на evergreen и time_sensitive
            if category in self.always_evergreen:
                # Эти категории всегда вечные
                evergreen_entries = sorted_entries[:30]
                promo_entries = []
            else:
                # Для остальных — разделяем
                evergreen_entries = [e for e in sorted_entries if not e['is_time_sensitive']][:30]
                promo_entries = [e for e in sorted_entries if e['is_time_sensitive']][:20]

            # === СОЗДАЁМ EVERGREEN ДОКУМЕНТЫ ===
            if evergreen_entries:
                for chunk_idx in range(0, len(evergreen_entries), 10):
                    chunk = evergreen_entries[chunk_idx:chunk_idx + 10]
                    file_num = chunk_idx // 10 + 1

                    filename = f'telegram_{category}_evergreen_{file_num}.txt'
                    filepath = rag_dir / filename

                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(f"# {title_map.get(category, category)}\n\n")
                        f.write(f"Источник: Рабочий канал NL International\n")
                        f.write(f"Категория: {category}\n")
                        f.write(f"Тип: EVERGREEN (вечный контент)\n")
                        f.write(f"Примечание: Цены и акции могут измениться, уточняйте актуальную информацию\n\n")
                        f.write("---\n\n")

                        for entry in chunk:
                            # Используем очищенный текст для evergreen
                            text_to_use = entry.get('text_cleaned', entry['text'])
                            f.write(f"{text_to_use}\n\n")
                            f.write("---\n\n")

                    created_evergreen += 1

            # === СОЗДАЁМ PROMO ДОКУМЕНТЫ (примеры постов с ценами) ===
            if promo_entries:
                for chunk_idx in range(0, len(promo_entries), 10):
                    chunk = promo_entries[chunk_idx:chunk_idx + 10]
                    file_num = chunk_idx // 10 + 1

                    filename = f'telegram_{category}_promo_{file_num}.txt'
                    filepath = promo_dir / filename

                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(f"# Примеры постов: {title_map.get(category, category)}\n\n")
                        f.write(f"Источник: Рабочий канал NL International\n")
                        f.write(f"Категория: {category}\n")
                        f.write(f"Тип: PROMO (примеры с ценами/акциями)\n")
                        f.write(f"⚠️ ВАЖНО: Цены и акции в этих примерах УСТАРЕЛИ!\n")
                        f.write(f"Используйте только как ШАБЛОНЫ для структуры постов.\n\n")
                        f.write("---\n\n")

                        for entry in chunk:
                            f.write(f"[Пример от {entry['date'][:10]}]\n\n")
                            f.write(f"{entry['text']}\n\n")
                            f.write("---\n\n")

                    created_promo += 1

        print(f"\nСоздано EVERGREEN документов: {created_evergreen}")
        print(f"  Папка: {rag_dir}")
        print(f"\nСоздано PROMO примеров: {created_promo}")
        print(f"  Папка: {promo_dir}")

        # Статистика по разделению
        print("\n--- Статистика по разделению ---")
        for category, entries in self.extracted_content.items():
            if not entries:
                continue
            evergreen_count = sum(1 for e in entries if not e['is_time_sensitive'])
            promo_count = sum(1 for e in entries if e['is_time_sensitive'])
            print(f"  {category}: {evergreen_count} evergreen, {promo_count} promo")

        return rag_dir

    def run(self):
        """Главная функция"""
        print("\n" + "=" * 60)
        print("ИЗВЛЕЧЕНИЕ ЗНАНИЙ ИЗ TELEGRAM ЭКСПОРТА")
        print("=" * 60)
        print(f"Путь: {self.export_path}\n")

        if not self.load_export():
            return False

        self.process_messages()
        self.deduplicate_content()
        output_dir = self.save_results()
        self.create_rag_documents(output_dir)

        print("\n" + "=" * 60)
        print("ГОТОВО!")
        print("=" * 60)
        print("\nЧто дальше:")
        print("  1. Проверь извлечённый контент: content/telegram_knowledge/")
        print("  2. RAG документы: content/knowledge_base/from_telegram/")
        print("  3. Запусти load_knowledge_base.py для индексации")

        return True


def main():
    import sys

    if len(sys.argv) > 1:
        export_path = sys.argv[1]
    else:
        export_path = input("Путь к папке с экспортом Telegram: ").strip('"')

    if not Path(export_path).exists():
        print(f"[ERROR] Папка не найдена: {export_path}")
        return

    extractor = TelegramKnowledgeExtractor(export_path)
    extractor.run()


if __name__ == "__main__":
    main()
