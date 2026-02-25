#!/usr/bin/env python3
"""
Import line photos from Telegram export into content/line_photos/.

Photos are named as slugified line names (e.g., "ED Smart 4.0" -> "ed_smart_4.0.jpg").
Mapping comes from result.json which contains text labels before each photo.
"""

import json
import re
import shutil
from pathlib import Path

SOURCE_DIR = Path(r"C:\Users\mafio\Downloads\Telegram Desktop\фото линеек")
TARGET_DIR = Path(r"c:\Users\mafio\OneDrive\Документы\projects\nl-international-ai-bots\content\line_photos")

# Mapping: photo filename -> line name in our catalog
PHOTO_TO_LINE = {
    "photo_1@09-02-2026_15-05-20.jpg": "ED Smart 4.0",
    "photo_2@09-02-2026_15-05-36.jpg": "ED Smart 5.0",
    "photo_3@09-02-2026_15-06-17.jpg": "Imperial Herb",
    "photo_4@09-02-2026_15-06-50.jpg": "Occuba",
    "photo_5@09-02-2026_15-07-22.jpg": "BL Oriental",
    "photo_6@09-02-2026_15-08-12.jpg": "Косметика BL для тела",
    "photo_7@09-02-2026_15-09-00.jpg": "Biome",
    "photo_8@09-02-2026_15-56-27.jpg": "BL Sun Cream",
    "photo_9@09-02-2026_15-57-14.jpg": "3D Slim Cosmetics",
    "photo_10@09-02-2026_15-57-49.jpg": "The LAB для мужчин",
    "photo_11@09-02-2026_15-58-35.jpg": "Зубные пасты",
    "photo_12@09-02-2026_16-01-18.jpg": "Липосомальные",
    "photo_13@09-02-2026_16-02-57.jpg": "БАД направленного действия",
    "photo_14@09-02-2026_16-03-54.jpg": "DrainEffect",
    "photo_15@09-02-2026_16-05-24.jpg": "Herbal Tea",
    "photo_16@09-02-2026_16-06-05.jpg": "Enerwood",
    "photo_17@09-02-2026_16-07-15.jpg": "Уходовая коллекция",
    "photo_18@09-02-2026_16-07-59.jpg": "БАД",
    # photo_19 = NLka Baby (merged into "Уходовая коллекция", skip)
}


def line_name_to_slug(name: str) -> str:
    """Convert line name to filesystem-safe slug."""
    slug = name.lower().strip()
    slug = slug.replace(" ", "_")
    slug = re.sub(r"[^\w.]", "", slug, flags=re.UNICODE)
    return slug


def main():
    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    photos_dir = SOURCE_DIR / "photos"

    copied = 0
    for photo_file, line_name in PHOTO_TO_LINE.items():
        src = photos_dir / photo_file
        if not src.exists():
            print(f"  SKIP (not found): {photo_file}")
            continue

        slug = line_name_to_slug(line_name)
        dst = TARGET_DIR / f"{slug}.jpg"
        shutil.copy2(src, dst)
        size_kb = dst.stat().st_size / 1024
        print(f"  OK: {line_name} -> {slug}.jpg ({size_kb:.0f} KB)")
        copied += 1

    print(f"\nCopied {copied}/{len(PHOTO_TO_LINE)} line photos")

    # List all catalog lines and check coverage
    db_path = Path(r"c:\Users\mafio\OneDrive\Документы\projects\nl-international-ai-bots\content\products_database.json")
    with open(db_path, encoding="utf-8") as f:
        db = json.load(f)

    all_lines = {}
    for cat, prods in db["categories"].items():
        for p in prods:
            line = p.get("line", "")
            if line and line not in all_lines:
                all_lines[line] = cat

    print(f"\nCatalog lines: {len(all_lines)}")
    covered_lines = set(PHOTO_TO_LINE.values())
    missing = []
    for line, cat in sorted(all_lines.items()):
        slug = line_name_to_slug(line)
        photo_path = TARGET_DIR / f"{slug}.jpg"
        if photo_path.exists():
            print(f"  [OK] {line} ({cat})")
        else:
            print(f"  [--] {line} ({cat}) <- NO PHOTO")
            missing.append((line, cat))

    if missing:
        print(f"\nLines WITHOUT photos ({len(missing)}):")
        for line, cat in missing:
            print(f"  - {line} ({cat})")


if __name__ == "__main__":
    main()
