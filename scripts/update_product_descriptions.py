"""
Script to update products_database.json with descriptions extracted from knowledge base.
Matches product names using fuzzy string matching.
"""
import json
import re
import os
from difflib import SequenceMatcher

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRODUCTS_DB = os.path.join(BASE_DIR, "content", "products_database.json")
DESCRIPTIONS_FILE = os.path.join(
    os.environ.get("TEMP", "/tmp"),
    "claude",
    "c--Users-mafio-OneDrive-----------projects-nl-international-ai-bots",
    "226a0f1c-ce96-47d2-979b-a89c8b204b0c",
    "scratchpad",
    "product_descriptions.json",
)

# Also support passing path as argument
import sys
if len(sys.argv) > 1:
    DESCRIPTIONS_FILE = sys.argv[1]


def normalize(text: str) -> str:
    """Normalize text for comparison."""
    text = text.lower().strip()
    # Remove content in parentheses for matching
    text = re.sub(r'\([^)]*\)', '', text)
    # Remove special chars
    text = re.sub(r'[«»""\'.,!?:;/\\+\-–—]', ' ', text)
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def extract_key_parts(name: str) -> set:
    """Extract meaningful parts from a product name."""
    parts = set()
    name_lower = name.lower()

    # Extract English words
    english = re.findall(r'[a-z][a-z0-9]+', name_lower)
    parts.update(english)

    # Extract Russian words (3+ chars)
    russian = re.findall(r'[а-яё]{3,}', name_lower)
    parts.update(russian)

    return parts


def find_best_match(product_name: str, descriptions: dict) -> tuple:
    """Find the best matching description for a product name."""
    norm_product = normalize(product_name)
    product_parts = extract_key_parts(product_name)

    best_match = None
    best_score = 0

    for desc_key in descriptions:
        norm_desc = normalize(desc_key)
        desc_parts = extract_key_parts(desc_key)

        # Method 1: Direct substring match
        if norm_desc in norm_product or norm_product in norm_desc:
            score = 0.9
            if score > best_score:
                best_score = score
                best_match = desc_key
            continue

        # Method 2: SequenceMatcher ratio
        ratio = SequenceMatcher(None, norm_product, norm_desc).ratio()

        # Method 3: Common parts overlap
        common = product_parts & desc_parts
        if product_parts and desc_parts:
            overlap = len(common) / max(len(product_parts), len(desc_parts))
        else:
            overlap = 0

        # Combined score
        score = max(ratio, overlap * 0.95)

        # Boost if key English words match
        eng_product = set(re.findall(r'[a-z][a-z0-9]+', product_name.lower()))
        eng_desc = set(re.findall(r'[a-z][a-z0-9]+', desc_key.lower()))
        if eng_product and eng_desc:
            eng_common = eng_product & eng_desc
            if len(eng_common) >= 2:
                score = max(score, 0.85)
            elif len(eng_common) >= 1 and any(len(w) > 4 for w in eng_common):
                score = max(score, 0.7)

        if score > best_score:
            best_score = score
            best_match = desc_key

    return best_match, best_score


def main():
    # Load files
    with open(PRODUCTS_DB, 'r', encoding='utf-8') as f:
        db = json.load(f)

    with open(DESCRIPTIONS_FILE, 'r', encoding='utf-8') as f:
        descriptions = json.load(f)

    print(f"Products in DB: {db['total_products']}")
    print(f"Descriptions available: {len(descriptions)}")
    print()

    matched = 0
    unmatched = []

    for cat_name, products in db['categories'].items():
        print(f"\n=== {cat_name} ({len(products)} products) ===")
        for product in products:
            name = product['name']
            match_key, score = find_best_match(name, descriptions)

            if score >= 0.5 and match_key:
                product['description'] = descriptions[match_key]
                matched += 1
                print(f"  [OK] {name}")
                print(f"    -> {match_key} (score: {score:.2f})")
            else:
                unmatched.append((cat_name, name, match_key, score))
                print(f"  [--] {name}")
                if match_key:
                    print(f"    best: {match_key} (score: {score:.2f})")

    print(f"\n\n=== RESULTS ===")
    print(f"Matched: {matched}/{db['total_products']}")
    print(f"Unmatched: {len(unmatched)}")

    if unmatched:
        print(f"\nUnmatched products:")
        for cat, name, best, score in unmatched:
            print(f"  [{cat}] {name}")
            if best:
                print(f"    best candidate: {best} ({score:.2f})")

    # Save updated DB
    with open(PRODUCTS_DB, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

    print(f"\nSaved updated products_database.json")


if __name__ == '__main__':
    main()
