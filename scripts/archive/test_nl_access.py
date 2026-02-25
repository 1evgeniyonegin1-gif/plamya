"""
Тестовый скрипт для проверки доступа к сайту NL International
Проверяет несколько методов доступа
"""

import requests
from pathlib import Path

def test_direct_access():
    """Тест прямого доступа"""
    print("\n[ТЕСТ 1] Прямой доступ к сайту...")
    try:
        response = requests.get(
            "https://nl.international",
            timeout=10,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        print(f"✓ Статус: {response.status_code}")
        print(f"✓ Размер ответа: {len(response.content)} байт")
        return True
    except Exception as e:
        print(f"✗ Ошибка: {e}")
        return False

def test_product_page():
    """Тест доступа к странице продукта"""
    print("\n[ТЕСТ 2] Доступ к странице продукта...")

    # Популярные URL продуктов NL
    test_urls = [
        "https://nl.international/catalog/bady/biodrone/",
        "https://nl.international/catalog/collagen/collagentrinity/",
        "https://nl.international/catalog/energy-diet/",
    ]

    for url in test_urls:
        try:
            response = requests.get(
                url,
                timeout=10,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            )
            print(f"✓ {url}")
            print(f"  Статус: {response.status_code}, Размер: {len(response.content)} байт")

            # Сохраняем для анализа
            output_dir = Path(__file__).parent.parent / 'content' / 'html_dumps'
            output_dir.mkdir(exist_ok=True, parents=True)

            filename = url.split('/')[-2] + '.html'
            with open(output_dir / filename, 'w', encoding='utf-8') as f:
                f.write(response.text)
            print(f"  Сохранено в: {filename}")

            return True

        except Exception as e:
            print(f"✗ {url}: {e}")

    return False

def test_catalog_api():
    """Тест доступа к API каталога (если есть)"""
    print("\n[ТЕСТ 3] Проверка API...")

    api_endpoints = [
        "https://nl.international/api/catalog/products/",
        "https://nl.international/api/v1/products/",
    ]

    for endpoint in api_endpoints:
        try:
            response = requests.get(endpoint, timeout=10)
            if response.status_code == 200:
                print(f"✓ Найден API: {endpoint}")
                return True
        except:
            pass

    print("✗ API не найден (это нормально)")
    return False

def main():
    print("=" * 60)
    print("ТЕСТИРОВАНИЕ ДОСТУПА К САЙТУ NL INTERNATIONAL")
    print("=" * 60)

    results = {
        'direct': test_direct_access(),
        'product': test_product_page(),
        'api': test_catalog_api(),
    }

    print("\n" + "=" * 60)
    print("РЕЗУЛЬТАТЫ:")
    print("=" * 60)
    print(f"Прямой доступ: {'✓ РАБОТАЕТ' if results['direct'] else '✗ НЕ РАБОТАЕТ'}")
    print(f"Страницы продуктов: {'✓ РАБОТАЕТ' if results['product'] else '✗ НЕ РАБОТАЕТ'}")
    print(f"API: {'✓ НАЙДЕН' if results['api'] else '- НЕ ОБНАРУЖЕН'}")

    if results['product']:
        print("\n✓ Отлично! Можем парсить сайт напрямую.")
        print("Проверь папку: content/html_dumps/")
    else:
        print("\n⚠ Нужен прокси или VPN для доступа к сайту.")

if __name__ == "__main__":
    main()
