"""
Fixtures: 100 тестовых пользователей для нагрузочного тестирования

Создаёт разнообразных виртуальных пользователей с:
- Разными сегментами (A-E)
- Разными интентами (business, product, curious, skeptic)
- Разными pain points (weight, energy, immunity, beauty, money)
- Реалистичными профилями (имя, возраст, город)
"""

from typing import List
import random
import sys
from pathlib import Path

# Добавляем родительскую директорию в PATH для импорта
parent_dir = Path(__file__).parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from user_simulator import VirtualUser


# Реальные имена для тестовых пользователей
MALE_NAMES = [
    "Александр", "Дмитрий", "Максим", "Сергей", "Андрей",
    "Алексей", "Артём", "Илья", "Кирилл", "Михаил",
    "Иван", "Николай", "Роман", "Владимир", "Павел",
    "Егор", "Денис", "Тимофей", "Игорь", "Олег",
    "Виктор", "Антон", "Владислав", "Юрий", "Константин",
]

FEMALE_NAMES = [
    "Анна", "Мария", "Елена", "Ольга", "Наталья",
    "Татьяна", "Ирина", "Светлана", "Екатерина", "Дарья",
    "Юлия", "Виктория", "Анастасия", "Алина", "Полина",
    "Ксения", "Марина", "Людмила", "Валентина", "Нина",
    "София", "Алиса", "Вероника", "Кристина", "Маргарита",
]

CITIES = [
    "Москва", "Санкт-Петербург", "Новосибирск", "Екатеринбург", "Казань",
    "Нижний Новгород", "Челябинск", "Самара", "Омск", "Ростов-на-Дону",
    "Уфа", "Красноярск", "Воронеж", "Пермь", "Волгоград",
    "Краснодар", "Саратов", "Тюмень", "Тольятти", "Ижевск",
]


# Распределение по сегментам (аудитория NL)
SEGMENTS_DISTRIBUTION = {
    "A": 0.25,  # Амбициозные предприниматели (25%)
    "B": 0.20,  # Мамы в декрете, ищут доход (20%)
    "C": 0.15,  # Студенты / молодые специалисты (15%)
    "D": 0.25,  # Потребители продуктов (25%)
    "E": 0.15,  # Скептики / любопытные (15%)
}

# Распределение по интентам
INTENTS_DISTRIBUTION = {
    "business": 0.40,  # Интересуются бизнесом (40%)
    "product": 0.35,   # Интересуются продуктами (35%)
    "curious": 0.15,   # Просто любопытные (15%)
    "skeptic": 0.10,   # Скептики (10%)
}

# Распределение по pain points
PAIN_POINTS_DISTRIBUTION = {
    "weight": 0.30,    # Снижение веса (30%)
    "energy": 0.20,    # Энергия и бодрость (20%)
    "immunity": 0.15,  # Иммунитет (15%)
    "beauty": 0.20,    # Красота (20%)
    "money": 0.15,     # Дополнительный доход (15%)
}

# Распределение по поведению
BEHAVIORS_DISTRIBUTION = {
    "active": 0.40,    # Активные, много вопросов (40%)
    "passive": 0.35,   # Пассивные, короткие ответы (35%)
    "skeptic": 0.25,   # Скептичные, критикуют (25%)
}


def _weighted_choice(distribution: dict) -> str:
    """Выбирает значение на основе весов распределения"""
    items = list(distribution.keys())
    weights = list(distribution.values())
    return random.choices(items, weights=weights)[0]


def _generate_profile(user_id: int) -> dict:
    """
    Генерирует профиль пользователя

    Args:
        user_id: ID пользователя

    Returns:
        Профиль с name, age, city, gender, segment, intent, pain_point, behavior
    """
    # Случайный выбор пола
    is_male = random.choice([True, False])
    name = random.choice(MALE_NAMES if is_male else FEMALE_NAMES)

    # Возраст зависит от сегмента
    segment = _weighted_choice(SEGMENTS_DISTRIBUTION)

    if segment == "A":  # Амбициозные предприниматели
        age = random.randint(25, 45)
    elif segment == "B":  # Мамы в декрете
        age = random.randint(25, 40)
    elif segment == "C":  # Студенты
        age = random.randint(18, 28)
    elif segment == "D":  # Потребители
        age = random.randint(30, 55)
    else:  # E - Скептики
        age = random.randint(20, 50)

    city = random.choice(CITIES)
    intent = _weighted_choice(INTENTS_DISTRIBUTION)
    pain_point = _weighted_choice(PAIN_POINTS_DISTRIBUTION)
    behavior = _weighted_choice(BEHAVIORS_DISTRIBUTION)

    # Корректируем intent для сегмента
    if segment == "A":
        intent = "business" if random.random() < 0.7 else intent
    elif segment == "D":
        intent = "product" if random.random() < 0.7 else intent
    elif segment == "E":
        intent = random.choice(["skeptic", "curious"])

    return {
        "name": name,
        "age": age,
        "city": city,
        "gender": "M" if is_male else "F",
        "segment": segment,
        "intent": intent,
        "pain_point": pain_point,
        "behavior": behavior,
    }


def generate_test_personas(count: int = 100) -> List[VirtualUser]:
    """
    Генерирует тестовых пользователей

    Args:
        count: Количество пользователей (по умолчанию 100)

    Returns:
        Список VirtualUser с разнообразными профилями
    """
    personas = []

    for i in range(count):
        profile = _generate_profile(user_id=i + 1)

        user = VirtualUser(
            user_id=i + 1,
            telegram_id=1000000 + i,  # Telegram ID начинается с 1000000
            name=profile["name"],
            age=profile["age"],
            city=profile["city"],
            segment=profile["segment"],
            intent=profile["intent"],
            pain_point=profile["pain_point"],
            behavior=profile["behavior"],
        )

        # Генерируем тестовые сообщения на основе профиля
        user.test_messages = user.generate_test_messages()

        personas.append(user)

    return personas


def get_personas_by_segment(personas: List[VirtualUser], segment: str) -> List[VirtualUser]:
    """Фильтрует пользователей по сегменту"""
    return [p for p in personas if p.segment == segment]


def get_personas_by_intent(personas: List[VirtualUser], intent: str) -> List[VirtualUser]:
    """Фильтрует пользователей по интенту"""
    return [p for p in personas if p.intent == intent]


def get_personas_by_behavior(personas: List[VirtualUser], behavior: str) -> List[VirtualUser]:
    """Фильтрует пользователей по поведению"""
    return [p for p in personas if p.behavior == behavior]


def print_personas_stats(personas: List[VirtualUser]):
    """
    Выводит статистику по созданным персонам

    Args:
        personas: Список пользователей
    """
    total = len(personas)

    # Распределение по сегментам
    segments = {}
    for p in personas:
        segments[p.segment] = segments.get(p.segment, 0) + 1

    # Распределение по интентам
    intents = {}
    for p in personas:
        intents[p.intent] = intents.get(p.intent, 0) + 1

    # Распределение по pain points
    pain_points = {}
    for p in personas:
        pain_points[p.pain_point] = pain_points.get(p.pain_point, 0) + 1

    # Распределение по поведению
    behaviors = {}
    for p in personas:
        behaviors[p.behavior] = behaviors.get(p.behavior, 0) + 1

    print(f"\n{'='*60}")
    print(f"Тестовые персоны: {total} пользователей")
    print(f"{'='*60}\n")

    print("Распределение по сегментам:")
    for segment, count in sorted(segments.items()):
        percentage = (count / total) * 100
        print(f"  {segment}: {count:3d} ({percentage:5.1f}%)")

    print("\nРаспределение по интентам:")
    for intent, count in sorted(intents.items()):
        percentage = (count / total) * 100
        print(f"  {intent:12s}: {count:3d} ({percentage:5.1f}%)")

    print("\nРаспределение по pain points:")
    for pain, count in sorted(pain_points.items()):
        percentage = (count / total) * 100
        print(f"  {pain:10s}: {count:3d} ({percentage:5.1f}%)")

    print("\nРаспределение по поведению:")
    for behavior, count in sorted(behaviors.items()):
        percentage = (count / total) * 100
        print(f"  {behavior:10s}: {count:3d} ({percentage:5.1f}%)")

    print(f"\n{'='*60}\n")


# Предгенерированные персоны (100 шт, создаются при импорте)
TEST_PERSONAS: List[VirtualUser] = []


def get_test_personas() -> List[VirtualUser]:
    """
    Возвращает предгенерированные тестовые персоны

    Returns:
        Список из 100 VirtualUser
    """
    global TEST_PERSONAS

    # Генерируем один раз при первом вызове
    if not TEST_PERSONAS:
        random.seed(42)  # Фиксированный seed для воспроизводимости
        TEST_PERSONAS = generate_test_personas(count=100)

    return TEST_PERSONAS


# Примеры использования
if __name__ == "__main__":
    # Генерируем персоны
    personas = get_test_personas()

    # Выводим статистику
    print_personas_stats(personas)

    # Примеры фильтрации
    print("\nПримеры пользователей:")
    print("-" * 60)

    for persona in personas[:5]:
        print(f"\n{persona.name}, {persona.age} лет, {persona.city}")
        print(f"  Сегмент: {persona.segment}")
        print(f"  Интент: {persona.intent}")
        print(f"  Pain Point: {persona.pain_point}")
        print(f"  Поведение: {persona.behavior}")
        print(f"  Сообщений: {len(persona.test_messages)}")

    # Примеры фильтров
    print("\n\nФильтры:")
    print("-" * 60)

    business_users = get_personas_by_intent(personas, "business")
    print(f"Пользователей с интентом 'business': {len(business_users)}")

    segment_a = get_personas_by_segment(personas, "A")
    print(f"Пользователей в сегменте A: {len(segment_a)}")

    active_users = get_personas_by_behavior(personas, "active")
    print(f"Активных пользователей: {len(active_users)}")
