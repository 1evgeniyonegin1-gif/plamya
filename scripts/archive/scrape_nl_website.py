"""
Скрипт для парсинга сайта NL International с использованием прокси
Обходит блокировку и собирает информацию о продуктах
"""

import requests
from bs4 import BeautifulSoup
import json
import time
from pathlib import Path

# Список бесплатных российских прокси (можно обновить актуальными)
PROXIES = [
    "http://45.130.127.50:3128",
    "http://188.120.246.81:8080",
    "http://185.162.230.55:80",
]

# Альтернатива: использовать прокси-сервисы
# PROXY_SERVICE = "https://api.proxyscrape.com/v2/?request=get&protocol=http&timeout=10000&country=RU"

class NLScraper:
    def __init__(self):
        self.base_url = "https://nl.international"
        self.session = requests.Session()
        self.products = []

    def get_with_proxy(self, url, max_retries=3):
        """Получить страницу через прокси"""
        for proxy in PROXIES:
            for attempt in range(max_retries):
                try:
                    print(f"Пробую прокси: {proxy}")
                    response = self.session.get(
                        url,
                        proxies={"http": proxy, "https": proxy},
                        timeout=10,
                        headers={
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                        }
                    )
                    if response.status_code == 200:
                        print(f"✓ Успешно через {proxy}")
                        return response
                except Exception as e:
                    print(f"✗ Ошибка с {proxy}: {e}")
                    time.sleep(1)

        # Если прокси не сработали, пробуем без прокси
        print("Пробую без прокси...")
        try:
            response = self.session.get(url, timeout=10)
            return response
        except Exception as e:
            print(f"Ошибка без прокси: {e}")
            return None

    def scrape_product_page(self, url):
        """Парсинг страницы продукта"""
        response = self.get_with_proxy(url)
        if not response:
            return None

        soup = BeautifulSoup(response.content, 'html.parser')

        product = {
            'url': url,
            'name': '',
            'description': '',
            'composition': '',
            'usage': '',
            'price': '',
            'pv': '',
            'images': []
        }

        # Извлекаем информацию (нужно адаптировать под реальную структуру сайта)
        try:
            product['name'] = soup.find('h1', class_='product-title').text.strip()
            product['description'] = soup.find('div', class_='product-description').text.strip()
            product['composition'] = soup.find('div', class_='product-composition').text.strip()
            # и т.д.
        except AttributeError:
            print("Не удалось найти элементы на странице")

        return product

    def scrape_category(self, category_url):
        """Парсинг категории продуктов"""
        response = self.get_with_proxy(category_url)
        if not response:
            return []

        soup = BeautifulSoup(response.content, 'html.parser')
        product_links = []

        # Ищем ссылки на продукты (адаптировать под сайт)
        for link in soup.find_all('a', class_='product-link'):
            product_url = self.base_url + link.get('href')
            product_links.append(product_url)

        return product_links

    def save_products(self, filename='nl_products_scraped.json'):
        """Сохранить собранные данные"""
        output_path = Path(__file__).parent.parent / 'content' / filename
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.products, f, ensure_ascii=False, indent=2)
        print(f"Сохранено {len(self.products)} продуктов в {output_path}")

def main():
    scraper = NLScraper()

    # Категории для парсинга
    categories = [
        '/catalog/energy-diet',
        '/catalog/greenflash',
        '/catalog/beauty',
        '/catalog/cosmetics',
        # добавить все нужные категории
    ]

    print("Начинаю парсинг сайта NL International...")

    for category in categories:
        print(f"\nОбрабатываю категорию: {category}")
        category_url = scraper.base_url + category

        # Получаем список продуктов в категории
        product_links = scraper.scrape_category(category_url)
        print(f"Найдено {len(product_links)} продуктов")

        # Парсим каждый продукт
        for link in product_links[:5]:  # Первые 5 для теста
            print(f"Парсинг: {link}")
            product = scraper.scrape_product_page(link)
            if product:
                scraper.products.append(product)
            time.sleep(2)  # Пауза между запросами

    # Сохраняем результаты
    scraper.save_products()
    print("\nГотово!")

if __name__ == "__main__":
    main()
