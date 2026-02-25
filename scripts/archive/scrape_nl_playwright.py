"""
Парсинг сайта NL International через Playwright с прокси
Более надёжный метод, использует реальный браузер
"""

from playwright.sync_api import sync_playwright
import json
import time
from pathlib import Path

class NLPlaywrightScraper:
    def __init__(self, use_proxy=False):
        self.base_url = "https://nl.international"
        self.products = []
        self.use_proxy = use_proxy

    def scrape_product(self, page, url):
        """Парсинг страницы продукта"""
        try:
            page.goto(url, wait_until="networkidle")
            time.sleep(2)  # Даём странице загрузиться

            product = {
                'url': url,
                'name': page.locator('h1').first.inner_text() if page.locator('h1').count() > 0 else '',
                'description': '',
                'composition': '',
                'usage': '',
                'price': '',
                'pv': '',
            }

            # Извлекаем описание
            desc_selectors = [
                '.product-description',
                '[class*="description"]',
                '.description',
                '#description'
            ]
            for selector in desc_selectors:
                try:
                    if page.locator(selector).count() > 0:
                        product['description'] = page.locator(selector).first.inner_text()
                        break
                except:
                    pass

            # Извлекаем состав
            composition_selectors = [
                '.composition',
                '[class*="composition"]',
                '[class*="ingredients"]',
                '#composition'
            ]
            for selector in composition_selectors:
                try:
                    if page.locator(selector).count() > 0:
                        product['composition'] = page.locator(selector).first.inner_text()
                        break
                except:
                    pass

            # Извлекаем цену
            price_selectors = [
                '.price',
                '[class*="price"]',
                '.product-price'
            ]
            for selector in price_selectors:
                try:
                    if page.locator(selector).count() > 0:
                        product['price'] = page.locator(selector).first.inner_text()
                        break
                except:
                    pass

            print(f"✓ Спарсил: {product['name'][:50]}...")
            return product

        except Exception as e:
            print(f"✗ Ошибка при парсинге {url}: {e}")
            return None

    def scrape_catalog(self):
        """Главная функция парсинга"""
        with sync_playwright() as p:
            # Настройки браузера
            browser_args = {
                'headless': True,  # Поставь False, чтобы видеть браузер
            }

            # Если используем прокси
            if self.use_proxy:
                browser_args['proxy'] = {
                    'server': 'http://45.130.127.50:3128',  # Указать актуальный прокси
                }

            browser = p.chromium.launch(**browser_args)
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            page = context.new_page()

            # Список URL продуктов для парсинга
            # TODO: Сначала получить список всех продуктов из каталога
            product_urls = [
                f"{self.base_url}/catalog/product1",
                f"{self.base_url}/catalog/product2",
                # ... добавить все URL
            ]

            print(f"Начинаю парсинг {len(product_urls)} продуктов...")

            for url in product_urls:
                product = self.scrape_product(page, url)
                if product:
                    self.products.append(product)
                time.sleep(1)  # Пауза между запросами

            browser.close()

    def get_all_product_urls(self):
        """Получить все URL продуктов из каталога"""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            # Переходим на страницу каталога
            catalog_url = f"{self.base_url}/catalog"
            page.goto(catalog_url, wait_until="networkidle")

            # Собираем все ссылки на продукты
            product_links = page.locator('a[href*="/product/"]').all()
            urls = [link.get_attribute('href') for link in product_links]

            # Делаем абсолютные URL
            urls = [self.base_url + url if not url.startswith('http') else url for url in urls]

            browser.close()
            return urls

    def save_products(self, filename='nl_products_playwright.json'):
        """Сохранить результаты"""
        output_path = Path(__file__).parent.parent / 'content' / filename
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.products, f, ensure_ascii=False, indent=2)
        print(f"\n✓ Сохранено {len(self.products)} продуктов в {output_path}")

def main():
    print("=" * 60)
    print("Парсер сайта NL International (Playwright)")
    print("=" * 60)

    scraper = NLPlaywrightScraper(use_proxy=False)  # Сначала без прокси

    # Шаг 1: Получаем все URL продуктов
    print("\n[1/2] Получаю список всех продуктов...")
    # product_urls = scraper.get_all_product_urls()
    # print(f"Найдено продуктов: {len(product_urls)}")

    # Шаг 2: Парсим каждый продукт
    print("\n[2/2] Парсинг продуктов...")
    scraper.scrape_catalog()

    # Сохраняем
    scraper.save_products()

if __name__ == "__main__":
    # Установи сначала: pip install playwright
    # Затем: playwright install chromium
    main()
