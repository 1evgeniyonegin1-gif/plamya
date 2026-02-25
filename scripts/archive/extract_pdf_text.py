"""
Извлечение текста из PDF документов NL International

Парсит PDF файлы из nl_knowledge/ и создаёт текстовые файлы для RAG базы

Использование:
    python scripts/extract_pdf_text.py
"""

import sys
import io
from pathlib import Path
from collections import defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

try:
    from PyPDF2 import PdfReader
except ImportError:
    print("Установите PyPDF2: pip install PyPDF2")
    sys.exit(1)


class PDFTextExtractor:
    def __init__(self):
        self.base_path = Path(__file__).parent.parent / 'content' / 'nl_knowledge'
        self.output_path = Path(__file__).parent.parent / 'content' / 'knowledge_base' / 'from_pdf'
        self.stats = defaultdict(int)

    def extract_text_from_pdf(self, pdf_path: Path) -> str:
        """Извлекает текст из PDF файла"""
        try:
            reader = PdfReader(pdf_path)
            text_parts = []

            for page in reader.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)

            return '\n\n'.join(text_parts)
        except Exception as e:
            print(f"  [ERROR] {pdf_path.name}: {e}")
            return ""

    def clean_text(self, text: str) -> str:
        """Очищает извлечённый текст"""
        # Убираем множественные пробелы и переносы
        import re
        text = re.sub(r' +', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)

        # Убираем странные символы
        text = text.replace('\x00', '')

        return text.strip()

    def process_all_pdfs(self):
        """Обрабатывает все PDF файлы"""
        print("=" * 60)
        print("ИЗВЛЕЧЕНИЕ ТЕКСТА ИЗ PDF")
        print("=" * 60)

        self.output_path.mkdir(parents=True, exist_ok=True)

        # Также ищем PDF в основном экспорте
        export_files_path = Path("C:/Users/mafio/Downloads/Telegram Desktop/ChatExport_2026-01-23 (1)/files")

        # Собираем все PDF
        all_pdfs = []

        # Из nl_knowledge
        if self.base_path.exists():
            for product_dir in self.base_path.iterdir():
                if product_dir.is_dir():
                    docs_dir = product_dir / 'documents'
                    if docs_dir.exists():
                        for pdf_file in docs_dir.glob('*.pdf'):
                            all_pdfs.append((pdf_file, product_dir.name))

        # Из экспорта напрямую
        if export_files_path.exists():
            for pdf_file in export_files_path.glob('*.pdf'):
                # Определяем продукт по имени файла
                product = self.detect_product_from_filename(pdf_file.name)
                all_pdfs.append((pdf_file, product))

        print(f"Найдено PDF файлов: {len(all_pdfs)}")

        # Группируем по продуктам
        by_product = defaultdict(list)
        for pdf_path, product in all_pdfs:
            by_product[product].append(pdf_path)

        # Обрабатываем
        for product, pdfs in by_product.items():
            print(f"\n--- {product} ---")

            all_texts = []

            for pdf_path in pdfs:
                print(f"  Обрабатываю: {pdf_path.name}")

                text = self.extract_text_from_pdf(pdf_path)
                if text:
                    cleaned = self.clean_text(text)
                    if len(cleaned) > 100:  # Минимум 100 символов
                        all_texts.append({
                            'filename': pdf_path.name,
                            'text': cleaned,
                        })
                        self.stats['extracted'] += 1
                    else:
                        print(f"    [SKIP] Слишком мало текста")
                        self.stats['skipped'] += 1
                else:
                    self.stats['failed'] += 1

            # Сохраняем объединённый файл для RAG
            if all_texts:
                output_file = self.output_path / f'{product}_from_pdf.txt'
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(f"# {product.upper()} - Информация из PDF документов\n\n")
                    f.write(f"Источник: PDF презентации и FAQ NL International\n")
                    f.write(f"Файлов обработано: {len(all_texts)}\n\n")
                    f.write("=" * 60 + "\n\n")

                    for item in all_texts:
                        f.write(f"## Источник: {item['filename']}\n\n")
                        f.write(item['text'])
                        f.write("\n\n" + "-" * 40 + "\n\n")

                print(f"  Сохранено: {output_file.name}")

    def detect_product_from_filename(self, filename: str) -> str:
        """Определяет продукт по имени файла"""
        filename_lower = filename.lower()

        patterns = {
            'collagen': ['collagen', 'коллаген'],
            'greenflash': ['greenflash', 'green_flash', 'lymph', 'lux_gyan', 'uri_gyan', 'livo_gyan', 'gut_vigyan', 'gyan'],
            'draineffect': ['drain', 'детокс'],
            'omega': ['omega', 'омега', 'dha'],
            'ed_smart': ['smart', 'ed_smart'],
            'vision_lecithin': ['lecithin', 'лецитин', 'vision'],
            'prohelper': ['prohelper', 'прохелпер'],
            'happy_smile': ['happy_smile', 'smile', 'зуб'],
            'nlka': ['nlka', 'baby', 'kids', 'детск'],
            'calcium': ['calcium', 'кальций', 'ca_'],
            'occuba': ['occuba', 'оккуба'],
            'sport': ['протеин', 'protein', 'sport', 'спорт'],
            'imperial_herb': ['imperial', 'herb'],
            'starter_kits': ['startov', 'стартов', 'набор'],
        }

        for product, keywords in patterns.items():
            for kw in keywords:
                if kw in filename_lower:
                    return product

        return 'general'

    def print_stats(self):
        """Выводит статистику"""
        print("\n" + "=" * 60)
        print("СТАТИСТИКА")
        print("=" * 60)
        print(f"Успешно извлечено: {self.stats['extracted']}")
        print(f"Пропущено (мало текста): {self.stats['skipped']}")
        print(f"Ошибки: {self.stats['failed']}")
        print(f"\nФайлы сохранены в: {self.output_path}")

    def run(self):
        """Главная функция"""
        self.process_all_pdfs()
        self.print_stats()


def main():
    extractor = PDFTextExtractor()
    extractor.run()


if __name__ == "__main__":
    main()
