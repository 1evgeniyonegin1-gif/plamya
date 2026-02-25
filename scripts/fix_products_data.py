"""
Фаза 1: Исправление данных в products_database.json

Все изменения по плану:
1. Удалить "Трюфели"
2. Удалить "Travel набор" из БАДов
3. Переместить "Горячий напиток Малина" в "Чай и напитки"
4. Переместить "Beauty Blend" в "БАДы"
5. Объединить ED Smart Milky в ED Smart 4.0
6. Добавить BioSetting/BioDrone/BioTuning в линейку "Адаптогены"
7. Убрать Pro-indole/Metabiotic из отдельных линеек
8. Создать категорию "Для питомцев" и перенести туда питомцев
9. Добавить "Имбирный пряник" в ED Smart 5.0
10. Переименовать линейки BL
11. Исправить самые кривые названия продуктов
"""
import json
from pathlib import Path

PROJECT_ROOT = Path(r"c:\Users\mafio\OneDrive\Документы\projects\nl-international-ai-bots")
DB_PATH = PROJECT_ROOT / "content" / "products_database.json"

# Load
with open(DB_PATH, encoding="utf-8") as f:
    data = json.load(f)

cats = data["categories"]
changes_log = []


def log(msg):
    changes_log.append(msg)
    print(msg)


def find_and_remove(category, predicate):
    """Find and remove products matching predicate from category. Returns removed."""
    removed = []
    remaining = []
    for p in cats.get(category, []):
        if predicate(p):
            removed.append(p)
        else:
            remaining.append(p)
    cats[category] = remaining
    return removed


def move_product(from_cat, to_cat, predicate, new_category_name=None):
    """Move products matching predicate from one category to another."""
    removed = find_and_remove(from_cat, predicate)
    for p in removed:
        if new_category_name:
            p["category"] = new_category_name
        else:
            p["category"] = to_cat
        cats.setdefault(to_cat, []).append(p)
        log(f"  MOVE: '{p['name']}' from '{from_cat}' -> '{to_cat}'")
    return removed


# ============================================================
# 1. DELETE "Трюфели"
# ============================================================
log("\n=== 1. Удаление 'Трюфели' ===")
removed = find_and_remove("Функциональное питание", lambda p: p["key"] == "трюфели")
for p in removed:
    log(f"  DELETED: '{p['name']}'")

# ============================================================
# 2. DELETE "Travel набор" (Стартовые наборы)
# ============================================================
log("\n=== 2. Удаление 'Travel набор' ===")
removed = find_and_remove("БАДы", lambda p: p.get("line") == "Стартовые наборы")
for p in removed:
    log(f"  DELETED: '{p['name']}'")

# ============================================================
# 3. MOVE "Горячий напиток Малина" -> "Чай и напитки"
# ============================================================
log("\n=== 3. Перемещение 'Горячий напиток Малина' -> 'Чай и напитки' ===")
moved = move_product(
    "Функциональное питание", "Чай и напитки",
    lambda p: "горяч" in p.get("name", "").lower() and "малин" in p.get("name", "").lower(),
    new_category_name="Чай и напитки"
)
# Update line
for p in cats["Чай и напитки"]:
    if "горяч" in p.get("name", "").lower():
        p["line"] = "Напитки"
        log(f"  Set line='Напитки' for '{p['name']}'")

# ============================================================
# 4. MOVE "Beauty Blend" -> "БАДы"
# ============================================================
log("\n=== 4. Перемещение 'Beauty Blend' -> 'БАДы' ===")
# First find it in any category
for cat_name in list(cats.keys()):
    moved = move_product(
        cat_name, "БАДы",
        lambda p: "beauty" in p.get("name", "").lower() and "blend" in p.get("name", "").lower(),
        new_category_name="БАДы"
    )
    if moved:
        for p in cats["БАДы"]:
            if "beauty" in p.get("name", "").lower() and "blend" in p.get("name", "").lower():
                p["line"] = "Greenflash"
                log(f"  Set line='Greenflash' for '{p['name']}'")
        break

# ============================================================
# 5. MERGE ED Smart Milky into ED Smart 4.0
# ============================================================
log("\n=== 5. Объединение ED Smart Milky -> ED Smart 4.0 ===")
for p in cats.get("Функциональное питание", []):
    if p.get("line") == "ED Smart Milky":
        old_line = p["line"]
        p["line"] = "ED Smart 4.0"
        log(f"  MERGE: '{p['name']}' line '{old_line}' -> 'ED Smart 4.0'")

# ============================================================
# 6. ADD BioSetting/BioDrone/BioTuning to "Адаптогены"
# ============================================================
log("\n=== 6. BioSetting/BioDrone/BioTuning -> линейка 'Адаптогены' ===")
for p in cats.get("БАДы", []):
    if p.get("line") in ["BioSetting", "BioDrone", "BioTuning"]:
        old_line = p["line"]
        p["line"] = "Адаптогены"
        log(f"  RELINE: '{p['name']}' from '{old_line}' -> 'Адаптогены'")

# ============================================================
# 7. REMOVE Pro-indole/Metabiotic from separate lines
# ============================================================
log("\n=== 7. Pro-indole/Metabiotic -> без отдельной линейки ===")
for p in cats.get("БАДы", []):
    if p.get("line") in ["Pro-indole", "Metabiotic"]:
        old_line = p["line"]
        p["line"] = "Greenflash"
        log(f"  RELINE: '{p['name']}' from '{old_line}' -> 'Greenflash'")

# ============================================================
# 8. CREATE "Для питомцев" category
# ============================================================
log("\n=== 8. Создание категории 'Для питомцев' ===")

# Move from БАДы (line "Для питомцев")
pets_from_bads = find_and_remove("БАДы", lambda p: p.get("line") == "Для питомцев")
for p in pets_from_bads:
    p["category"] = "Для питомцев"
    p["line"] = "Здоровье питомцев"
    log(f"  MOVE TO PETS: '{p['name']}' from БАДы")

# Move from Красота и уход (pet products in Occuba)
pets_from_beauty = find_and_remove("Красота и уход", lambda p:
    any(w in p.get("name", "").lower() for w in ["собак", "кошек", "шерст"]))
for p in pets_from_beauty:
    p["category"] = "Для питомцев"
    p["line"] = "Уход за питомцами"
    log(f"  MOVE TO PETS: '{p['name']}' from Красота и уход")

all_pets = pets_from_bads + pets_from_beauty
if all_pets:
    cats["Для питомцев"] = all_pets
    log(f"  Created 'Для питомцев' with {len(all_pets)} products")

# ============================================================
# 9. ADD "Имбирный пряник" to ED Smart 5.0
# ============================================================
log("\n=== 9. Добавление 'Имбирный пряник' в ED Smart 5.0 ===")
new_product = {
    "name": "ED Smart Classic «Имбирный пряник», 15 порций",
    "price": 2790,
    "pv": 19.5,
    "category": "Функциональное питание",
    "key": "ed_smart_classic_имбирный_пряник_15_порций",
    "price_per_portion": 186.0,
    "portions": 15,
    "description": "Функциональное питание нового поколения с матрицей PeptiSmart. Коктейль со вкусом имбирного пряника для замены приема пищи.",
    "image_folder": None,
    "line": "ED Smart 5.0",
    "image_count": 0
}
cats["Функциональное питание"].append(new_product)
log(f"  ADDED: '{new_product['name']}'")

# ============================================================
# 10. RENAME BL lines
# ============================================================
log("\n=== 10. Переименование линеек BL ===")
bl_renames = {
    "BL для лица": "BL Oriental",
    "BL для тела": "BL Body Care",
}
for p in cats.get("Красота и уход", []):
    old_line = p.get("line", "")
    if old_line in bl_renames:
        p["line"] = bl_renames[old_line]
        log(f"  RENAME LINE: '{p['name']}' from '{old_line}' -> '{p['line']}'")

# ============================================================
# 11. FIX worst product names (only the most problematic)
# ============================================================
log("\n=== 11. Исправление самых кривых названий ===")
name_fixes = {
    # БАДы — русификация самых кривых
    "Lactoferra (Лактоферра)": "Лактоферра",
    "Soft Sorb (Природный сорбент)": "Природный сорбент Soft Sorb",
    "Detox Sorb (Сорбент)": "Детокс сорбент Detox Sorb",
    "Gelm Cleanse (Противопаразитарное средство)": "Gelm Cleanse",
    "Collagen Peptides (дойпак, лимитка)": "Коллаген Peptides (дойпак)",
    # Питомцы — обрезанные названия
    "Общеукрепляющий комплекс для собак": "Комплекс для собак",
    "Общеукрепляющий комплекс для кошек": "Комплекс для кошек",
}

for cat_name, prods in cats.items():
    for p in prods:
        old_name = p.get("name", "")
        if old_name in name_fixes:
            p["name"] = name_fixes[old_name]
            log(f"  RENAME: '{old_name}' -> '{p['name']}'")

# Also fix truncated pet product names (partial matches)
for p in cats.get("Для питомцев", []):
    name = p.get("name", "")
    if "кастрированных" in name.lower() or "стерилизованных" in name.lower():
        if len(name) > 40:
            p["name"] = "Комплекс для кастрированных кошек"
            log(f"  RENAME: truncated pet name -> '{p['name']}'")
    if "расчёсыв" in name.lower() or "расчесыв" in name.lower():
        p["name"] = "Спрей для расчёсывания шерсти"
        log(f"  RENAME: truncated pet name -> '{p['name']}'")
    if "шампунь" in name.lower() and ("собак" in name.lower() or "кошек" in name.lower()):
        p["name"] = "Шампунь для собак и кошек"
        log(f"  RENAME: truncated pet name -> '{p['name']}'")

# ============================================================
# UPDATE total_products count
# ============================================================
total = sum(len(prods) for prods in cats.values())
data["total_products"] = total
log(f"\n=== ИТОГО: {total} продуктов в {len(cats)} категориях ===")

# Print summary
log("\nКатегории после изменений:")
for cat, prods in cats.items():
    log(f"  {cat}: {len(prods)}")

# Save
with open(DB_PATH, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
log(f"\nСохранено в {DB_PATH}")

# Print all changes
print("\n" + "=" * 60)
print("ВСЕ ИЗМЕНЕНИЯ:")
print("=" * 60)
for line in changes_log:
    print(line)
