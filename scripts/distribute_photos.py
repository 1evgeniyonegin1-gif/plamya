"""
Распределение фоток из Telegram-экспорта по папкам продуктов.

Парсит result.json, матчит подписи к продуктам из products_database.json,
копирует фотки как main.jpg в content/unified_products/{image_folder}/photos/
"""
import json
import re
import shutil
from pathlib import Path
from difflib import SequenceMatcher

PROJECT_ROOT = Path(r"c:\Users\mafio\OneDrive\Документы\projects\nl-international-ai-bots")
EXPORT_DIR = Path(r"C:\Users\mafio\Downloads\Telegram Desktop") / "'rcgjhn yjdsq"
RESULT_JSON = EXPORT_DIR / "result.json"
PRODUCTS_DB = PROJECT_ROOT / "content" / "products_database.json"
MEDIA_PATH = PROJECT_ROOT / "content" / "unified_products"

# Emoji pattern for cleaning
EMOJI_PATTERN = re.compile(
    "[\U0001F300-\U0001F9FF\U00002600-\U000027BF\U0000FE00-\U0000FEFF\U0001FA00-\U0001FA6F"
    "\U0001FA70-\U0001FAFF\U00002702-\U000027B0\U0000200D\U0000FE0F\U000025AA-\U000025FE"
    "\U000025B6\U000025C0\U00002934\U00002935\U000023EA-\U000023F3"
    "\U0000231A\U0000231B\U000023CF\U000023E9-\U000023F3\U000023F8-\U000023FA"
    "\U00002B05-\U00002B07\U00002B1B\U00002B1C\U00002B50\U00002B55"
    "\U00003030\U0000303D\U00003297\U00003299\U000020E3]+",
    re.UNICODE,
)


# ============================================================
# MANUAL MAPPING: export label → product image_folder
# Maps the LAST text label before photos to the target folder.
# This overrides any automatic matching.
# ============================================================
MANUAL_LABEL_TO_FOLDER = {
    # Fineffect
    "fineffect textile": "fineffect/textile",
    "японская аквапудра": "fineffect/sensitive",
    "концентраты для стирки": "fineffect/active_plus",
    "гель для мытья посуды gloss power": "fineffect/protect",
    "fineffect уборка": "fineffect/_collection",
    "мыло-пенка для рук": "fineffect/_collection",

    # Occuba для волос
    "сыворотка active serum": "occuba/active_serum",
    "маска мгновенного действия": "occuba/maska_instant",
    "филлер-термозащита master hair": "occuba/filler_master_hair",
    "спрей-кондиционер для волос 3-in-1": "occuba/spray_conditioner_3in1",
    "шампунь восстанавливающий": "occuba/shampoo_repair",
    "кондиционер восстанавливающий": "occuba/conditioner_repair",
    "маска восстанавливающая": "occuba/mask_repair",
    "шампунь объем и сила": "occuba/shampoo_volume",
    "кондиционер объем и сила": "occuba/conditioner_volume",
    "шампунь балансирующий": "occuba/shampoo_balance",
    "кондиционер балансирующий": "occuba/conditioner_volume",
    "крем-блеск leave-in moisturizing": "occuba/cream_shine",

    # BL Oriental (лицо)
    "гидрофильный бальзам": "occuba/hydrophilic_balm",
    "бабл-пудра": "occuba/bubble_powder",
    "ночная увлажняющая маска": "occuba/night_mask",
    "патчи magic glitter": "occuba/patches_magic_glitter",
    "сыворотка vitalize moisturizing serum": "occuba/night_serum_face",
    "патчи pink glow": "occuba/patches_pink_glow",
    "пенка для умывания": "occuba/foam_cleanse",
    "диски для очищения": "occuba/cleansing_discs",
    "увлажняющий мист": "occuba/moisturizing_mist",
    "гидрофильное масло": "occuba/hydrophilic_oil",
    "очищающая маска cleansing glow mask": "occuba/mask_detox",
    "гидрогелевая маска detox hydrogel mask": "occuba/mask_detox",
    "cc dull cream": "occuba/cc_dull_cream",
    "легкий увлажняющий крем-гель": "occuba/light_cream_gel",
    "обогащенный ночной крем": "occuba/enriched_night_cream",
    "восстанавливающий крем для контура глаз": "occuba/eye_contour_cream",
    "восстанавливающая ночная сыворотка для лица": "occuba/night_serum_face",
    "ферментная пудра": "occuba/enzyme_powder",
    "энзимная пудра": "occuba/enzyme_powder",

    # BL для тела
    "расслабляющий крем-гель для душа relaxing": "occuba/body_butter",
    "увлажняющий гель для душа moisturizing": "occuba/body_butter",
    "обновляющий скраб для тела renewal": "occuba/body_butter",
    "питательное молочко для тела nourishing": "occuba/body_butter",
    "насыщенный крем-баттер для тела": "occuba/body_butter",
    "крем для рук softening": "occuba/body_butter",
    "крем для ног": "occuba/body_butter",

    # Biome
    "biome eye cream": "occuba/biome_eye_cream",
    "biome serum": "occuba/biome_serum",
    "biome 2 in 1 face cream": "occuba/biome_face_cream",

    # 3D SLIM cosmetics
    "скраб моделирующий shaping": "3d_slim/3d_slim",
    "средства с термоэффектами": "3d_slim/3d_slim",
    "сыворотка от растяжек": "3d_slim/3d_slim",

    # BL Sun Cream
    "для лица 50 spf": "occuba/_collection",
    "для тела 50 spf": "occuba/_collection",

    # The Lab мужское
    "универсальный бальзам the lab": "occuba/thelab_face_gel",
    "гель для умывания the lab": "occuba/thelab_face_gel",
    "гель для душа и шампунь 2 в 1 the lab": "occuba/thelab_shower_2in1",
    "гель для бритья the lab": "occuba/thelab_shave_gel",
    "дезодорант мужской the lab": "occuba/thelab_deodorant",

    # Standalone
    "smartum max": "greenflash/no_yoyo_effect",
    "жидкие патчи с гуминами": "greenflash/no_yoyo_effect",
    "жидкие патчи bl be smart": "greenflash/no_yoyo_effect",
    "жидкие патчи anti-dark circles": "occuba/patches_anti_dark",
    "жидкие патчи shine & antistress": "occuba/patches_anti_dark",
    "дезодорант crispento silver": "occuba/thelab_deodorant",

    # Sklaer зубные пасты
    "sensitive": "occuba/_collection",
    "white": "occuba/_collection",
    "protect": "occuba/_collection",

    # Липосомальные БАДы
    "5-нтр liposomal": "greenflash/no_yoyo_effect",
    "5-htp liposomal": "greenflash/no_yoyo_effect",
    "vitamin c liposomal": "greenflash/no_yoyo_effect",
    "metabrain liposomal": "greenflash/no_yoyo_effect",
    "neuromedium liposomal": "greenflash/no_yoyo_effect",

    # DrainEffect
    "green low carb": "greenflash/draineffect",
    "red low carb": "greenflash/draineffect",
    "green": "greenflash/draineffect",

    # Адресные БАДы
    "metaboost": "greenflash/metaboost",
    "collagentrinity": "collagen/collagen_peptides",
    "collagen peptides дойпак (лимитка)": "collagen/collagen_peptides",
    "вишня": "collagen/collagen_peptides",
    "зеленый чай": "collagen/collagen_peptides",
    "biosetting": "biotuning/biotuning",
    "be best male": "greenflash/no_yoyo_effect",
    "be best female": "greenflash/no_yoyo_effect",
    "pro-indole": "greenflash/no_yoyo_effect",
    "lactoferra": "greenflash/lactoferra",
    "detox sorb": "greenflash/soft_sorb",
    "soft sorb": "greenflash/soft_sorb",
    "gelm cleanse": "greenflash/gelm_cleanse",
    "collagen peptides": "collagen/collagen_peptides",
    "collagen peptides вишня": "collagen/collagen_peptides",
    "vitamin k2+d3": "vitamin_d",
    "в9в12": "greenflash/no_yoyo_effect",
    "metabiotic": "biotuning/metabiotic",
    "magnesium marine": "omega/magnesium_marine",
    "омега-3 1300мг": "omega/omega",
    "zinс (zn) и iron (fe)": "greenflash/no_yoyo_effect",
    "zinc (zn) и iron (fe)": "greenflash/no_yoyo_effect",
    "marine collagen": "collagen/collagen_peptides",
    "d3 2000 me": "vitamin_d",
    "calcium marine": "calcium",
    "detox plus": "greenflash/no_yoyo_effect",
    "white tea": "beloved/white_tea",

    # Чаи и напитки
    "горячий напиток «малина»": "energy_diet/_collection",
    "lux": "enerwood/herbal_tea",
    "liverpool": "enerwood/herbal_tea",
    "vodoley": "enerwood/herbal_tea",
    "prana": "enerwood/herbal_tea",
    "valery": "enerwood/herbal_tea",
    "gentleman": "enerwood/herbal_tea",
    "donna bella": "enerwood/herbal_tea",
    "черный индийский": "enerwood/_collection",
    "зеленый китайский": "enerwood/green_tea",
    "красный с малиной": "enerwood/_collection",
    "черный цейлонский": "enerwood/_collection",
    "чайное ассорти": "enerwood/_collection",
    "beauty blend": "energy_diet/_collection",

    # Energy Life батончики
    "шоколад-кокос": "sport/energy_pro",
    "шоколад-малина": "sport/energy_pro",
    "шоколад-банан": "sport/energy_pro",
    "протеин": "sport/energy_pro",
    "вафельные протеиновые батончики": "sport/energy_pro",
    "протеиновые батончики": "sport/energy_pro",
    "протеиновый батончик": "sport/energy_pro",

    # Energy Pro
    "шоколад": "sport/energy_pro",
    "ваниль": "sport/energy_pro",
    "energy pro протеин": "sport/energy_pro",

    # ED Smart 5.0
    "ягодная панна-котта": "energy_diet/ed_smart",
    "шоколадный брауни": "energy_diet/ed_smart",
    "вишневый брауни": "energy_diet/ed_smart",
    "лимонное печенье": "energy_diet/ed_smart",
    "бельгийский шоколад": "energy_diet/ed_smart",
    "грушевый тарт": "energy_diet/ed_smart",
    "суп «курица»": "energy_diet/ed_smart",
    "суп курица": "energy_diet/ed_smart",

    # ED Smart 4.0 / Milky
    "банановый сплит": "energy_diet/ed_smart",
    "ванильный пломбир": "energy_diet/ed_smart",
    "кофе": "energy_diet/ed_smart",
    "черничный йогурт": "energy_diet/ed_smart",
    "фисташковое мороженое": "energy_diet/ed_smart",
    "арахис в карамели": "energy_diet/ed_smart",
    "кофе с молоком": "energy_diet/ed_smart",

    # ED HD
    "double chocolate": "energy_diet/ed_smart",
    "salted caramel": "energy_diet/ed_smart",
    "mango passion fruit": "energy_diet/ed_smart",
    "cinnamon bun": "energy_diet/ed_smart",
    "vanilla cream": "energy_diet/ed_smart",
    "banana split": "energy_diet/ed_smart",
    "strawberry cream": "energy_diet/ed_smart",

    # 3D Slim program
    "3d slim": "greenflash/draineffect",

    # Адаптогены
    "ph balance stones": "enerwood/_collection",
    "biotuning": "biotuning/biotuning",
    "biodrone": "biodrone/biodrone",

    # NLka Baby
    "средство для купания 3 в 1": "nlka/_collection",
    "детское молочко для тела": "nlka/_collection",
    "детский крем с пантенолом": "nlka/_collection",

    # NLka Kids
    "детский шампунь": "nlka/_collection",
    "детский гель для душа": "nlka/_collection",
    "детская зубная паста": "nlka/_collection",

    # Детские БАДы
    "happy smile": "nlka/happy_smile",
    "omega-3 dha": "nlka/omega3_dha",
    "liquid ca": "nlka/liquid_ca",
    "liquid ca+": "nlka/liquid_ca",
    "vision lecithin": "nlka/vision_lecithin",
    "prohelper": "prohelper/prohelper",

    # Imperial Herb
    "lymph gyan": "greenflash/lymph_gyan",
    "lux gyan": "enerwood/imperial_herb",
    "uri gyan": "enerwood/imperial_herb",
    "livo gyan": "enerwood/imperial_herb",
    "gut vigyan": "greenflash/gut_vigyan",

    # Enerwood Every (чай)
    "every black": "beloved/every_black",
    "every deep black": "beloved/every_deep_black",
    "every green": "beloved/every_green",
    "every red": "beloved/every_red",
    "every mix": "beloved/every_mix",

    # ED Smart дополнительные
    "соленая карамель и арахис": "energy_diet/ed_smart",
    "фисташковый тарт": "energy_diet/ed_smart",
    "печенье с суфле": "energy_diet/ed_smart",
    "smart 5.0 курица": "energy_diet/ed_smart",
    "smart 5.0 имбирный пряник": "energy_diet/ed_smart",
    "клубника": "energy_diet/ed_smart",
    "фисташка": "energy_diet/ed_smart",
    "банан": "energy_diet/ed_smart",
    "грибы": "energy_diet/ed_smart",
    # ED Smart specific full labels (prevent false matches to sport)
    "smart 5.0 classic кофе": "energy_diet/ed_smart",
    "smart 5.0 classic ванильный пломбир": "energy_diet/ed_smart",
    "smart 5.0 classic шоколадный брауни": "energy_diet/ed_smart",
    "smart classic 5.0 ягодная панна-котта": "energy_diet/ed_smart",
    "ed smart milky фисташковое мороженое": "energy_diet/ed_smart",
    "ed smart 4.0 лимонное печенье": "energy_diet/ed_smart",
    "ed smart 4.0 грушевый тарт": "energy_diet/ed_smart",
    "ed smart 4.0 бельгийский шоколад": "energy_diet/ed_smart",
    "ed smart 4.0 ваниль": "energy_diet/ed_smart",
    "ed smart 4.0 вишневый брауни": "energy_diet/ed_smart",
    "ed smart 4.0 черничный йогурт": "energy_diet/ed_smart",
    "ed smart 4.0 банановый сплит": "energy_diet/ed_smart",
    "ed smart milky арахис в карамели": "energy_diet/ed_smart",
    "ed smart milky кофе с молоком": "energy_diet/ed_smart",
    "соленая карамель": "energy_diet/ed_smart",

    # Коллекции
    "коллекция": "occuba/_collection",

    # Бабл-пудра (Cyrillic-safe)
    "бабл пудра": "occuba/bubble_powder",

    # Cyrillic variants (Н=Latin look-alike)
    "5 нтр liposomal": "greenflash/no_yoyo_effect",
    "omega 3 dha": "nlka/omega3_dha",
    "омега 3 1300мг": "omega/omega",
    "омега 3 1300 мг": "omega/omega",

    # Zinc/Iron with mixed Cyrillic
    "zinс zn и iron fe": "greenflash/no_yoyo_effect",
    "zinc zn и iron fe": "greenflash/no_yoyo_effect",
    "zinc zn iron fe": "greenflash/no_yoyo_effect",
}


def clean_label(text: str) -> str:
    """Remove emoji, special chars, normalize whitespace."""
    text = EMOJI_PATTERN.sub("", text)
    # Remove common decoration characters
    text = text.replace("▫️", "").replace("◾", "").replace("◽", "")
    text = re.sub(r"^\s*[🆘✨🌀🌸💦☁️👄💧🤍💆🧴🌿🧬💊🍵🔥🏋💪🥤🧒👶🌱🎽🌀♻️🧹🧼🌊🫧💎🌈🌟🌼]+\s*", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize(text: str) -> str:
    """Lowercase, remove special chars for matching."""
    text = clean_label(text).lower()
    text = re.sub(r"[—–\-\"\'\«\»\(\)\.,!?:;/\\]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_export(result_json: Path) -> list:
    """Parse Telegram export into groups of (labels, photos).

    KEY FIX: Reset labels after each photo group so they don't accumulate.
    """
    with open(result_json, encoding="utf-8") as f:
        data = json.load(f)

    messages = data.get("messages", [])
    groups = []
    current_labels = []

    for msg in messages:
        if msg.get("type") == "service":
            continue

        text = msg.get("text", "")
        if isinstance(text, list):
            # Telegram export sometimes has text as array of entities
            text = "".join(
                t["text"] if isinstance(t, dict) else str(t) for t in text
            )
        text = text.strip()
        photo = msg.get("photo", "")
        file_path = msg.get("file", "")

        # Treat PNG files as photos too
        is_photo = bool(photo) or (file_path and file_path.lower().endswith(".png"))
        photo_path = photo or file_path

        if is_photo:
            # Photo message - create/extend group
            if groups and not current_labels:
                # No new labels since last photo - add to same group
                groups[-1]["photos"].append(photo_path)
            else:
                # New group with current labels
                groups.append({
                    "labels": list(current_labels) if current_labels else ["(без подписи)"],
                    "photos": [photo_path],
                })
                current_labels = []  # RESET after creating group
        elif text:
            # Text message - add to labels
            cleaned = clean_label(text)
            if cleaned:
                current_labels.append(cleaned)

    return groups


def find_manual_match(label: str) -> str:
    """Try to find a manual mapping for the label."""
    norm = normalize(label)
    # Exact match (normalize both sides)
    for key, folder in MANUAL_LABEL_TO_FOLDER.items():
        norm_key = normalize(key)
        if norm == norm_key:
            return folder
    # Partial match
    for key, folder in MANUAL_LABEL_TO_FOLDER.items():
        norm_key = normalize(key)
        if len(norm_key) >= 4 and (norm_key in norm or norm in norm_key):
            return folder
    return ""


def load_products(db_path: Path) -> list:
    """Load all products from database."""
    with open(db_path, encoding="utf-8") as f:
        data = json.load(f)

    products = []
    for cat_products in data.get("categories", {}).values():
        for p in cat_products:
            products.append(p)
    return products


def match_label_to_product(label: str, products: list) -> tuple:
    """Try to match a text label to a product. Returns (product, score)."""
    norm_label = normalize(label)
    if not norm_label or len(norm_label) < 3:
        return None, 0

    best_match = None
    best_score = 0

    for p in products:
        norm_name = normalize(p.get("name", ""))

        if norm_label == norm_name:
            return p, 1.0

        if norm_label in norm_name:
            score = len(norm_label) / len(norm_name) * 0.95
            if score > best_score:
                best_score = score
                best_match = p

        if norm_name in norm_label and len(norm_name) > 5:
            score = len(norm_name) / len(norm_label) * 0.9
            if score > best_score:
                best_score = score
                best_match = p

        ratio = SequenceMatcher(None, norm_label, norm_name).ratio()
        if ratio > 0.65 and ratio * 0.85 > best_score:
            best_score = ratio * 0.85
            best_match = p

    return best_match, best_score


def distribute_photos(groups: list, products: list, dry_run: bool = False) -> dict:
    """Match groups to products and copy photos."""
    stats = {
        "matched": 0,
        "unmatched": 0,
        "copied": 0,
        "already_exists": 0,
        "details": [],
    }

    for i, group in enumerate(groups):
        labels = group["labels"]
        photos = group["photos"]

        if not photos:
            continue

        # Try to match: use last label first (most specific), then others
        target_folder = ""
        matched_label = ""

        # First: try manual mapping (most reliable)
        for label in reversed(labels):
            folder = find_manual_match(label)
            if folder:
                target_folder = folder
                matched_label = label
                break

        # Second: try automatic matching against product names
        if not target_folder:
            for label in reversed(labels):
                product, score = match_label_to_product(label, products)
                if product and score >= 0.5:
                    target_folder = product.get("image_folder", "")
                    matched_label = f"{label} → {product['name']} (auto, score={score:.2f})"
                    break

        if target_folder:
            target_dir = MEDIA_PATH / target_folder / "photos"
            target_file = target_dir / "main.jpg"

            status = ""
            if target_file.exists():
                status = "ALREADY_EXISTS"
                stats["already_exists"] += 1
            elif not dry_run:
                target_dir.mkdir(parents=True, exist_ok=True)
                src = EXPORT_DIR / photos[0]
                if src.exists():
                    shutil.copy2(src, target_file)
                    status = "COPIED"
                    stats["copied"] += 1
                else:
                    status = "SRC_NOT_FOUND"
            else:
                status = "WILL_COPY"

            stats["matched"] += 1
            stats["details"].append({
                "group": i + 1,
                "label": matched_label or labels[-1],
                "folder": target_folder,
                "photos_count": len(photos),
                "status": status,
            })
        else:
            stats["unmatched"] += 1
            stats["details"].append({
                "group": i + 1,
                "label": " → ".join(labels),
                "folder": "",
                "photos_count": len(photos),
                "status": "UNMATCHED",
            })

    return stats


def main():
    print("=" * 70)
    print("  РАСПРЕДЕЛЕНИЕ ФОТОК ИЗ TELEGRAM-ЭКСПОРТА")
    print("=" * 70)

    # Parse export
    groups = parse_export(RESULT_JSON)
    total_photos = sum(len(g["photos"]) for g in groups)
    products = load_products(PRODUCTS_DB)

    print(f"Групп: {len(groups)}, Фоток: {total_photos}, Продуктов: {len(products)}")

    # Dry run
    print(f"\n{'='*70}")
    print("  ПРЕДВАРИТЕЛЬНЫЙ МАТЧИНГ")
    print(f"{'='*70}")
    stats = distribute_photos(groups, products, dry_run=True)

    for d in stats["details"]:
        status = d["status"]
        label = d["label"]
        folder = d["folder"]
        n_photos = d["photos_count"]

        if status == "UNMATCHED":
            print(f"  [MISS] #{d['group']:3d} ({n_photos} фото) {label}")
        else:
            print(f"  [ OK ] #{d['group']:3d} ({n_photos} фото) {label}")
            print(f"          → {folder}")

    print(f"\n--- ИТОГО (dry run) ---")
    print(f"Матчей:     {stats['matched']}")
    print(f"Пропущено:  {stats['unmatched']}")

    # Actual copy
    print(f"\n{'='*70}")
    print("  КОПИРОВАНИЕ")
    print(f"{'='*70}")
    stats = distribute_photos(groups, products, dry_run=False)
    print(f"Скопировано:    {stats['copied']}")
    print(f"Уже было:       {stats['already_exists']}")
    print(f"Матчей:         {stats['matched']}")
    print(f"Пропущено:      {stats['unmatched']}")


if __name__ == "__main__":
    import sys

    output_file = PROJECT_ROOT / "scripts" / "distribute_photos_report.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        old_stdout = sys.stdout
        sys.stdout = f
        main()
        sys.stdout = old_stdout
    print(f"Report: {output_file}")
