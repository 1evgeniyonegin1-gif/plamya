#!/usr/bin/env python3
"""
Restructure products_database.json to match the official NL store structure.

Changes:
1. Rename "Функциональное питание" -> "Коктейли ED/ED Smart"
2. Restructure БАДы: consolidate lines, move DrainEffect/WhiteTea from 3D Slim
3. Restructure Красота: rename lines, create "3D Slim Cosmetics" line, add Hot
4. Create new "Адаптогены" category from БАДы
5. Restructure "Для детей": new line names
6. Restructure "Чай и напитки": rename lines, move Beauty Blend from БАДы
7. Delete "3D Slim" category (products redistributed)
"""

import json
from pathlib import Path
from copy import deepcopy

PROJECT_ROOT = Path(r"c:\Users\mafio\OneDrive\Документы\projects\nl-international-ai-bots")
DB_PATH = PROJECT_ROOT / "content" / "products_database.json"


def load_db():
    with open(DB_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_db(db):
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)
    print(f"Saved to {DB_PATH}")


def remove_products(products_list, keys_to_remove):
    """Remove products by key from list, return (remaining, removed)."""
    removed = []
    remaining = []
    for p in products_list:
        if p["key"] in keys_to_remove:
            removed.append(p)
        else:
            remaining.append(p)
    return remaining, removed


def rename_line(products_list, old_line, new_line):
    """Rename line for all matching products. Returns count."""
    count = 0
    for p in products_list:
        if p.get("line") == old_line:
            p["line"] = new_line
            count += 1
    return count


def set_category(products_list, new_category):
    """Set category for all products in list."""
    for p in products_list:
        p["category"] = new_category


def restructure(db):
    cats = db["categories"]
    new_cats = {}

    # =============================================
    # 1. Коктейли ED/ED Smart (from Функциональное питание)
    # =============================================
    print("\n=== 1. Коктейли ED/ED Smart ===")
    ed_products = deepcopy(cats["Функциональное питание"])
    set_category(ed_products, "Коктейли ED/ED Smart")
    new_cats["Коктейли ED/ED Smart"] = ed_products
    print(f"  {len(ed_products)} products (renamed from Функциональное питание)")
    for line in sorted(set(p["line"] for p in ed_products)):
        count = len([p for p in ed_products if p["line"] == line])
        print(f"    Line '{line}': {count}")

    # =============================================
    # 2. БАДы (restructured)
    # =============================================
    print("\n=== 2. БАДы ===")
    bady_products = deepcopy(cats["БАДы"])

    # Remove Адаптогены (will become separate category)
    adaptogen_keys = [
        "иммуноактиватор_biodrone_биодрон",
        "biotuning_биотюнинг",
        "протектор_biosetting_биосеттинг",
        "картридж_для_регуляции_pн_воды_ph_balance_stones",
    ]
    bady_products, adaptogens = remove_products(bady_products, adaptogen_keys)
    print(f"  Extracted {len(adaptogens)} adaptogens -> new category")

    # Remove Beauty Blend (will move to Чай)
    bady_products, beauty_blends = remove_products(bady_products, ["beauty_blend_бьюти_бленд"])
    print(f"  Extracted {len(beauty_blends)} Beauty Blend -> Tea")

    # Add DrainEffect + White Tea from 3D Slim
    slim_products = deepcopy(cats["3D Slim"])
    for p in slim_products:
        p["category"] = "БАДы"
        # DrainEffect and White Tea lines stay as-is
    bady_products.extend(slim_products)
    print(f"  Added {len(slim_products)} products from 3D Slim (DrainEffect + White Tea)")

    # Consolidate remaining lines into "БАД направленного действия"
    consolidate_lines = {
        "Витамины и минералы",
        "Коллаген",
        "Be Best",
        "Greenflash",
        "Detox",
    }
    consolidated_count = 0
    for p in bady_products:
        if p.get("line") in consolidate_lines:
            p["line"] = "БАД направленного действия"
            consolidated_count += 1
    print(f"  Consolidated {consolidated_count} products -> 'БАД направленного действия'")

    set_category(bady_products, "БАДы")
    new_cats["БАДы"] = bady_products

    print(f"  Total: {len(bady_products)} products")
    for line in sorted(set(p["line"] for p in bady_products)):
        count = len([p for p in bady_products if p["line"] == line])
        print(f"    Line '{line}': {count}")

    # =============================================
    # 3. Красота и уход (restructured)
    # =============================================
    print("\n=== 3. Красота и уход ===")
    beauty_products = deepcopy(cats["Красота и уход"])

    # Rename lines
    renames = {
        "Occuba для волос": "Occuba",
        "BL Sun": "BL Sun Cream",
        "The Lab": "The LAB для мужчин",
        "Sklaer": "Зубные пасты",
        "Другое": "Smartum MAX",
    }
    for old, new in renames.items():
        count = rename_line(beauty_products, old, new)
        if count:
            print(f"  Renamed '{old}' -> '{new}': {count} products")

    # Move Cold, Lifting, Shaping to "3D Slim Cosmetics" line
    cosmetics_keys = {
        "охлаждающий_антицеллюлитный_кремгель_cold",
        "сыворотка_lifting_для_профилактики_растяжек",
        "скраб_моделирующий_shaping",
    }
    for p in beauty_products:
        if p["key"] in cosmetics_keys:
            p["line"] = "3D Slim Cosmetics"
            print(f"  Moved '{p['name']}' -> 3D Slim Cosmetics")

    # Add Hot product (NEW)
    hot_product = {
        "name": "Разогревающий антицеллюлитный гель Hot",
        "price": 990,
        "pv": 6.7,
        "category": "Красота и уход",
        "key": "разогревающий_антицеллюлитный_гель_hot",
        "price_per_portion": None,
        "portions": None,
        "description": "Антицеллюлитный разогревающий гель для интенсивного воздействия на проблемные зоны тела. Способствует улучшению микроциркуляции и уменьшению объемов.",
        "image_folder": "разогревающий_антицеллюлитный_гель_hot",
        "line": "3D Slim Cosmetics",
        "image_count": 1
    }
    beauty_products.append(hot_product)
    print(f"  Added NEW product: Разогревающий антицеллюлитный гель Hot")

    # Update Cold image_count: 3 -> 2 (remove Hot photo)
    for p in beauty_products:
        if p["key"] == "охлаждающий_антицеллюлитный_кремгель_cold":
            old_count = p.get("image_count", 0)
            p["image_count"] = 2
            print(f"  Updated Cold image_count: {old_count} -> 2")

    set_category(beauty_products, "Красота и уход")
    new_cats["Красота и уход"] = beauty_products

    print(f"  Total: {len(beauty_products)} products")
    for line in sorted(set(p["line"] for p in beauty_products)):
        count = len([p for p in beauty_products if p["line"] == line])
        print(f"    Line '{line}': {count}")

    # =============================================
    # 4. Адаптогены (new category from БАДы)
    # =============================================
    print("\n=== 4. Адаптогены ===")
    for p in adaptogens:
        p["category"] = "Адаптогены"
        p["line"] = "Адаптогены"
    new_cats["Адаптогены"] = adaptogens
    print(f"  {len(adaptogens)} products (1 line, auto-skip)")
    for p in adaptogens:
        print(f"    - {p['name']}")

    # =============================================
    # 5. Для детей (restructured lines)
    # =============================================
    print("\n=== 5. Для детей ===")
    kids_products = deepcopy(cats["Для детей"])

    # Happy Smile: move from Детские БАДы to its own line
    happy_smile_key = "пастилки_happy_smile_витаминизированные_60_шт"
    for p in kids_products:
        if p["key"] == happy_smile_key:
            p["line"] = "Happy Smile"
            print(f"  Moved '{p['name']}' -> Happy Smile")

    # NLka Kids + NLka Baby -> "Уходовая коллекция"
    c1 = rename_line(kids_products, "NLka Kids", "Уходовая коллекция")
    c2 = rename_line(kids_products, "NLka Baby", "Уходовая коллекция")
    print(f"  Merged NLka Kids ({c1}) + NLka Baby ({c2}) -> Уходовая коллекция")

    # Remaining Детские БАДы -> "БАД"
    c3 = rename_line(kids_products, "Детские БАДы", "БАД")
    print(f"  Renamed Детские БАДы -> БАД ({c3} products)")

    set_category(kids_products, "Для детей")
    new_cats["Для детей"] = kids_products

    print(f"  Total: {len(kids_products)} products")
    for line in sorted(set(p["line"] for p in kids_products)):
        count = len([p for p in kids_products if p["line"] == line])
        print(f"    Line '{line}': {count}")

    # =============================================
    # 6. Чай и напитки (restructured lines)
    # =============================================
    print("\n=== 6. Чай и напитки ===")
    tea_products = deepcopy(cats["Чай и напитки"])

    # Rename lines
    c1 = rename_line(tea_products, "Напитки", "Горячие напитки")
    c2 = rename_line(tea_products, "Фиточаи NL", "Herbal Tea")
    print(f"  Renamed Напитки -> Горячие напитки ({c1})")
    print(f"  Renamed Фиточаи NL -> Herbal Tea ({c2})")

    # Add Beauty Blend from БАДы
    if beauty_blends:
        bb = beauty_blends[0]
        bb["category"] = "Чай и напитки"
        bb["line"] = "Beauty Blend"
        tea_products.append(bb)
        print(f"  Added Beauty Blend from БАДы")

    set_category(tea_products, "Чай и напитки")
    new_cats["Чай и напитки"] = tea_products

    print(f"  Total: {len(tea_products)} products")
    for line in sorted(set(p["line"] for p in tea_products)):
        count = len([p for p in tea_products if p["line"] == line])
        print(f"    Line '{line}': {count}")

    # =============================================
    # 7. Imperial Herb (no change)
    # =============================================
    print("\n=== 7. Imperial Herb ===")
    imperial_products = deepcopy(cats["Imperial Herb"])
    new_cats["Imperial Herb"] = imperial_products
    print(f"  {len(imperial_products)} products (no changes)")

    # =============================================
    # Verification
    # =============================================
    total = sum(len(prods) for prods in new_cats.values())

    print(f"\n{'='*50}")
    print(f"RESULT: {total} products across {len(new_cats)} categories")
    print(f"{'='*50}")
    for cat, prods in new_cats.items():
        lines = sorted(set(p["line"] for p in prods))
        print(f"  {cat}: {len(prods)} products, {len(lines)} lines")

    # Sanity checks
    assert "3D Slim" not in new_cats, "3D Slim category should be removed!"
    assert "Функциональное питание" not in new_cats, "Old category name still present!"

    # Check all keys unique
    all_keys = [p["key"] for prods in new_cats.values() for p in prods]
    dupes = set(k for k in all_keys if all_keys.count(k) > 1)
    assert not dupes, f"Duplicate keys: {dupes}"
    print("All keys unique OK")

    new_db = {
        "total_products": total,
        "categories": new_cats
    }
    return new_db


def main():
    print("Loading products database...")
    db = load_db()

    old_actual = sum(len(prods) for prods in db["categories"].values())
    old_cats = list(db["categories"].keys())
    print(f"Current: {old_actual} products, {len(old_cats)} categories: {old_cats}")

    print("\nRestructuring...")
    new_db = restructure(db)

    new_total = new_db["total_products"]
    print(f"\nVerification: {old_actual} -> {new_total} (diff: +{new_total - old_actual})")
    assert new_total == old_actual + 1, f"Expected {old_actual + 1} (+1 Hot), got {new_total}"

    save_db(new_db)
    print("\nDone! Catalog restructured successfully.")


if __name__ == "__main__":
    main()
