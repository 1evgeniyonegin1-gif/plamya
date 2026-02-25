"""
Поиск API endpoints NL International
Пытается найти внутренние API, используемые сайтом и приложениями
"""

import requests
import json
from pathlib import Path

class NLAPIFinder:
    def __init__(self):
        self.base_domains = [
            "https://nlstar.com",
            "https://api.nlstar.com",
            "https://api.nl.international",
            "https://backend.nlstar.com",
            "https://catalog.nlstar.com",
            "https://kg.nlstore.com",  # Из мобильного приложения
            "https://ng.nlstar.com",
            "https://eu.nlstar.com",
        ]

        self.api_paths = [
            "/api/v1/products",
            "/api/v2/products",
            "/api/catalog/products",
            "/api/products",
            "/products.json",
            "/catalog.json",
            "/api/v1/catalog",
            "/rest/catalog",
            "/graphql",
        ]

    def test_endpoint(self, url):
        """Тестирует доступность endpoint"""
        headers = {
            'User-Agent': 'NL Store/2.0 (Android 12)',  # Эмуляция мобильного приложения
            'Accept': 'application/json',
            'Accept-Language': 'ru-RU,ru;q=0.9',
        }

        try:
            print(f"  Тест: {url}")
            response = requests.get(url, headers=headers, timeout=5)

            if response.status_code == 200:
                print(f"    [OK] Статус: 200")

                # Проверяем, это JSON?
                try:
                    data = response.json()
                    print(f"    [OK] JSON! Размер: {len(str(data))} символов")
                    return {'url': url, 'status': 200, 'data': data}
                except:
                    print(f"    [INFO] Не JSON, размер: {len(response.text)} символов")
                    return {'url': url, 'status': 200, 'data': response.text[:500]}

            elif response.status_code in [401, 403]:
                print(f"    [BLOCK] Доступ запрещён: {response.status_code}")
                return {'url': url, 'status': response.status_code, 'note': 'Требует авторизации'}

            else:
                print(f"    [FAIL] Статус: {response.status_code}")
                return None

        except requests.exceptions.ConnectionError:
            print(f"    [FAIL] Не удалось подключиться")
            return None
        except requests.exceptions.Timeout:
            print(f"    [FAIL] Таймаут")
            return None
        except Exception as e:
            print(f"    [FAIL] Ошибка: {e}")
            return None

    def find_apis(self):
        """Ищет доступные API"""
        print("="*60)
        print("ПОИСК API ENDPOINTS NL INTERNATIONAL")
        print("="*60)

        found_apis = []

        for domain in self.base_domains:
            print(f"\n[Домен] {domain}")

            for path in self.api_paths:
                url = domain + path
                result = self.test_endpoint(url)

                if result and result['status'] == 200:
                    found_apis.append(result)

        print("\n" + "="*60)
        print(f"НАЙДЕНО API: {len(found_apis)}")
        print("="*60)

        if found_apis:
            for api in found_apis:
                print(f"\n✓ {api['url']}")
                print(f"  Статус: {api['status']}")

            # Сохраняем результаты
            output_path = Path(__file__).parent.parent / 'content' / 'nl_api_endpoints.json'
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(found_apis, f, ensure_ascii=False, indent=2)
            print(f"\n✓ Результаты сохранены: {output_path}")
        else:
            print("\n✗ API endpoints не найдены")
            print("\nВозможные причины:")
            print("  1. API требует авторизацию (токен/ключ)")
            print("  2. Используются другие домены")
            print("  3. API закрыт для внешнего доступа")

        return found_apis

def main():
    finder = NLAPIFinder()
    apis = finder.find_apis()

    if not apis:
        print("\n" + "="*60)
        print("АЛЬТЕРНАТИВНЫЙ ПЛАН:")
        print("="*60)
        print("1. Установить мобильное приложение NL Store")
        print("2. Использовать mitmproxy для перехвата трафика")
        print("3. Извлечь API endpoints и токены из приложения")
        print("4. Использовать их для парсинга")
        print()
        print("Или:")
        print("- Использовать существующий прайс-лист + PDF каталог")
        print("- Дополнить информацию из eco-katalog.ru")

if __name__ == "__main__":
    main()
