"""
v3: Link products to their existing per-product photo folders.

v2 already created per-product folders (124 products with photos).
This script just scans the filesystem and updates products_database.json
to point each product to its existing folder.
"""
import json
from pathlib import Path

PROJECT_ROOT = Path(r"c:\Users\mafio\OneDrive\Документы\projects\nl-international-ai-bots")
DB_PATH = PROJECT_ROOT / "content" / "products_database.json"
MEDIA_PATH = PROJECT_ROOT / "content" / "unified_products"

# Load products database
with open(DB_PATH, encoding="utf-8") as f:
    data = json.load(f)

# Build index of existing photo folders on disk
# folder_name -> (photo_count, [file_names])
photo_folders = {}
if MEDIA_PATH.exists():
    for folder in MEDIA_PATH.iterdir():
        if folder.is_dir():
            photos_dir = folder / "photos"
            if photos_dir.exists():
                jpgs = sorted(photos_dir.glob("*.jpg"))
                if jpgs:
                    photo_folders[folder.name] = len(jpgs)

print(f"Found {len(photo_folders)} folders with photos on disk")

# Update each product
matched = 0
unmatched = 0
matched_products = []
unmatched_products = []

for cat_name, prods in data["categories"].items():
    for p in prods:
        key = p["key"]
        if key in photo_folders:
            p["image_folder"] = key
            p["image_count"] = photo_folders[key]
            matched += 1
            matched_products.append(f"  [{cat_name}] {p['name']} -> {key}/ ({photo_folders[key]} photos)")
        else:
            p["image_folder"] = None
            p["image_count"] = 0
            unmatched += 1
            unmatched_products.append(f"  [{cat_name}] {p['name']} (key={key})")

# Save
with open(DB_PATH, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

# Report
print(f"\nMatched: {matched}")
print(f"Unmatched: {unmatched}")

print(f"\n=== MATCHED ({matched}) ===")
for m in matched_products:
    print(m)

print(f"\n=== UNMATCHED ({unmatched}) ===")
for u in unmatched_products:
    print(u)

print(f"\nDatabase saved to {DB_PATH}")
