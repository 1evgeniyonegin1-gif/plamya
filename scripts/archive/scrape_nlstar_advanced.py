"""
Продвинутый парсер сайта nlstar.com с обходом защиты
Использует Playwright с полной эмуляцией реального браузера
"""

from playwright.sync_api import sync_playwright
import json
import time
from pathlib import Path
import random
import sys
import io

# Фикс кодировки для Windows консоли
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

class NLStarAdvancedScraper:
    def __init__(self):
        self.base_url = "https://nlstar.com"
        self.products = []

    def get_realistic_headers(self):
        """Генерация реалистичных заголовков браузера"""
        return {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
        }

    def random_delay(self, min_sec=1, max_sec=3):
        """Случайная задержка для имитации человека"""
        time.sleep(random.uniform(min_sec, max_sec))

    def scrape_with_stealth(self):
        """Парсинг с полной эмуляцией браузера и обходом защиты"""
        with sync_playwright() as p:
            # Запускаем браузер в НЕ headless режиме для обхода детекции
            browser = p.chromium.launch(
                headless=False,  # ВИДИМЫЙ браузер обходит многие защиты
                args=[
                    '--disable-blink-features=AutomationControlled',  # Скрываем автоматизацию
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-web-security',
                ]
            )

            # Создаём контекст с реалистичными параметрами
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                locale='ru-RU',
                timezone_id='Europe/Moscow',
                extra_http_headers=self.get_realistic_headers()
            )

            # Скрываем признаки автоматизации
            context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });

                window.navigator.chrome = {
                    runtime: {},
                };

                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });

                Object.defineProperty(navigator, 'languages', {
                    get: () => ['ru-RU', 'ru', 'en-US', 'en'],
                });
            """)

            page = context.new_page()

            try:
                print("\n[1/5] Переход на главную страницу...")
                page.goto(f"{self.base_url}/ru/", wait_until="networkidle", timeout=30000)
                self.random_delay(2, 4)

                # Делаем скриншот для отладки
                screenshots_dir = Path(__file__).parent.parent / 'content' / 'screenshots'
                screenshots_dir.mkdir(exist_ok=True, parents=True)
                page.screenshot(path=screenshots_dir / 'nlstar_homepage.png')
                print(f"[OK] Screenshot saved: {screenshots_dir / 'nlstar_homepage.png'}")

                print("\n[2/5] Переход на страницу каталога...")
                page.goto(f"{self.base_url}/ru/products/", wait_until="networkidle", timeout=30000)
                self.random_delay(2, 4)

                page.screenshot(path=screenshots_dir / 'nlstar_catalog.png')
                print(f"[OK] Screenshot catalog saved")

                # Сохраняем HTML для анализа
                html_dumps_dir = Path(__file__).parent.parent / 'content' / 'html_dumps'
                html_dumps_dir.mkdir(exist_ok=True, parents=True)

                html_content = page.content()
                with open(html_dumps_dir / 'nlstar_catalog.html', 'w', encoding='utf-8') as f:
                    f.write(html_content)
                print(f"✓ HTML каталога сохранён: {html_dumps_dir / 'nlstar_catalog.html'}")

                print("\n[3/5] Поиск категорий продуктов...")

                # Пробуем разные селекторы для категорий
                category_selectors = [
                    'a[href*="/catalog/"]',
                    'a[href*="/products/"]',
                    '.category-link',
                    '.product-category',
                    '[class*="category"]',
                    'nav a',
                ]

                categories = []
                for selector in category_selectors:
                    try:
                        links = page.locator(selector).all()
                        if links:
                            print(f"  Найдено {len(links)} ссылок по селектору: {selector}")
                            for link in links[:10]:  # Первые 10 для проверки
                                href = link.get_attribute('href')
                                text = link.inner_text()
                                if href and ('catalog' in href or 'product' in href):
                                    categories.append({'url': href, 'name': text})
                            if categories:
                                break
                    except Exception as e:
                        continue

                print(f"\n✓ Найдено категорий: {len(categories)}")

                if categories:
                    print("\n[4/5] Парсинг первой категории (тест)...")
                    test_category = categories[0]
                    category_url = test_category['url']
                    if not category_url.startswith('http'):
                        category_url = self.base_url + category_url

                    print(f"  Категория: {test_category['name']}")
                    print(f"  URL: {category_url}")

                    page.goto(category_url, wait_until="networkidle", timeout=30000)
                    self.random_delay(2, 3)

                    page.screenshot(path=screenshots_dir / 'nlstar_category.png')

                    # Сохраняем HTML категории
                    html_content = page.content()
                    with open(html_dumps_dir / 'nlstar_category.html', 'w', encoding='utf-8') as f:
                        f.write(html_content)

                    print("  ✓ HTML категории сохранён")

                    # Ищем продукты на странице
                    product_selectors = [
                        'a[href*="/product/"]',
                        '.product-card a',
                        '[class*="product"] a',
                        '.item-link',
                    ]

                    products = []
                    for selector in product_selectors:
                        try:
                            links = page.locator(selector).all()
                            if links:
                                print(f"  Найдено {len(links)} продуктов по селектору: {selector}")
                                for link in links[:5]:  # Первые 5 для теста
                                    href = link.get_attribute('href')
                                    text = link.inner_text()
                                    if href:
                                        products.append({'url': href, 'name': text})
                                if products:
                                    break
                        except:
                            continue

                    if products:
                        print(f"\n[5/5] Парсинг первого продукта (тест)...")
                        test_product = products[0]
                        product_url = test_product['url']
                        if not product_url.startswith('http'):
                            product_url = self.base_url + product_url

                        print(f"  Продукт: {test_product['name']}")
                        print(f"  URL: {product_url}")

                        page.goto(product_url, wait_until="networkidle", timeout=30000)
                        self.random_delay(2, 3)

                        page.screenshot(path=screenshots_dir / 'nlstar_product.png')

                        # Сохраняем HTML продукта
                        html_content = page.content()
                        with open(html_dumps_dir / 'nlstar_product.html', 'w', encoding='utf-8') as f:
                            f.write(html_content)

                        print("  ✓ HTML продукта сохранён")

                # Сохраняем найденные категории
                output_path = Path(__file__).parent.parent / 'content' / 'nlstar_categories.json'
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(categories, f, ensure_ascii=False, indent=2)

                print(f"\n✓ Категории сохранены: {output_path}")
                print(f"\n✓ Все скриншоты в: {screenshots_dir}")
                print(f"✓ Все HTML-дампы в: {html_dumps_dir}")

                print("\n" + "="*60)
                print("ВАЖНО: Проверь скриншоты и HTML-файлы!")
                print("Они помогут определить правильные CSS-селекторы")
                print("="*60)

                # Даём время посмотреть на браузер
                print("\nБраузер останется открытым 10 секунд для проверки...")
                time.sleep(10)

            except Exception as e:
                print(f"\n✗ Ошибка: {e}")
                import traceback
                traceback.print_exc()

            finally:
                browser.close()

def main():
    print("=" * 60)
    print("ПРОДВИНУТЫЙ ПАРСЕР NLSTAR.COM")
    print("=" * 60)
    print("\nСтратегия обхода защиты:")
    print("✓ Реальный видимый браузер (не headless)")
    print("✓ Скрытие признаков автоматизации")
    print("✓ Реалистичные заголовки и User-Agent")
    print("✓ Случайные задержки между действиями")
    print("✓ Сохранение скриншотов и HTML для анализа")
    print("\n" + "=" * 60)

    scraper = NLStarAdvancedScraper()
    scraper.scrape_with_stealth()

if __name__ == "__main__":
    # Установка: pip install playwright
    # Затем: playwright install chromium
    main()
