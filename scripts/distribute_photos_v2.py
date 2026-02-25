"""
Distribute photos from Telegram export to product-key-based folders (v2)

Changes from v1:
- Maps each export group to a SPECIFIC product key (not shared folder)
- Creates unique folder per product: unified_products/{product_key}/photos/
- Saves ALL photos (1.jpg, 2.jpg, 3.jpg) — not just main.jpg
- Deletes old content before copying
- Updates image_folder in products_database.json
"""
import json
import re
import shutil
from pathlib import Path
from difflib import SequenceMatcher


# === PATHS ===
PROJECT_ROOT = Path(__file__).parent.parent
EXPORT_DIR = Path(r"C:\Users\mafio\Downloads\Telegram Desktop") / "'rcgjhn yjdsq"
EXPORT_JSON = EXPORT_DIR / "result.json"
EXPORT_PHOTOS = EXPORT_DIR / "photos"
DB_PATH = PROJECT_ROOT / "content" / "products_database.json"
MEDIA_PATH = PROJECT_ROOT / "content" / "unified_products"

EMOJI_PATTERN = re.compile(
    "[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF"
    "\U0001F900-\U0001F9FF\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF"
    "\U00002702-\U000027B0\U0000FE00-\U0000FE0F\U0000200D\U00002640"
    "\U00002642\U00002600-\U000026FF\U00002700-\U000027BF]+",
    flags=re.UNICODE,
)


# === MANUAL OVERRIDES ===
# label (lowercase, cleaned) -> product_key
# Only for ambiguous cases where fuzzy matching would fail
MANUAL_OVERRIDES = {
    # Generic flavor names -> ED Smart cocktails (not Energy Pro)
    "банан": "коктейль_банан",
    "клубника": "коктейль_клубника",
    "фисташка": "коктейль_фисташка",
    "соленая карамель": "коктейль_соленая_карамель",
    "грибы": "суп_грибы",
    # These look like Energy Pro but we don't have Energy Pro in DB
    # Map to ED Smart cocktails instead
    "шоколад": "коктейль_шоколад",
    "ваниль": "коктейль_ваниль",
    # ED Smart specific
    "smart 5.0 курица": "ed_smart_soup_курица_15_порций",
    "smart 5.0 имбирный пряник": None,  # No match in DB (no имбирный пряник product)
    "smart 5.0 classic кофе": "ed_smart_classic_кофе_15_порций",
    "smart 5.0 classic ванильный пломбир": "ed_smart_classic_ванильный_пломбир_15_порций",
    "smart 5.0 classic шоколадный брауни": "ed_smart_classic_шоколадный_брауни_15_порций",
    "smart classic 5.0 ягодная панна-котта": "ed_smart_classic_ягодная_паннакотта_15_порций",
    'ed smart milky "фисташковое мороженое"': "ed_smart_milky_фисташковое_мороженое_15_порций",
    "ed smart milky фисташковое мороженое": "ed_smart_milky_фисташковое_мороженое_15_порций",
    "ed smart 4.0 лимонное печенье": "ed_smart_classic_лимонное_печенье_15_порций",
    "ed smart 4.0 грушевый тарт": "ed_smart_classic_грушевый_тарт_15_порций",
    "ed smart 4.0 бельгийский шоколад": "ed_smart_classic_бельгийский_шоколад_15_порций",
    "ed smart 4.0 ваниль": "ed_smart_classic_ваниль_15_порций",
    "ed smart 4.0 вишневый брауни": "ed_smart_classic_вишневый_брауни_15_порций",
    "ed smart 4.0 черничный йогурт": "ed_smart_classic_черничный_йогурт_15_порций",
    "ed smart 4.0 банановый сплит": "ed_smart_classic_банановый_сплит_15_порций",
    "ed smart milky арахис в карамели": "ed_smart_milky_арахис_в_карамели_15_порций",
    "ed smart milky кофе с молоком": None,  # No milky кофе in DB
    # Snacks
    "шоколадный брауни": "трюфели",  # closest snack match
    "соленая карамель и арахис": "молочный_шоколад",  # closest snack match
    "фисташковый тарт": None,  # No фисташковый тарт snack
    "печенье с суфле": "микс_протеинового_печенья_nl_с_суфле",
    "beauty blend": "beauty_blend_бьюти_бленд",
    # Teas - by name
    "lux": "nl_lux_фиточай_люкс_фиточай",
    "liverpool": "nl_liverpool_фиточай_ливерпуль_фиточай",
    "vodoley": "nl_vodoley_фиточай_водолей_фиточай",
    "prana": "nl_prana_фиточай_прана_фиточай",
    "valery": "nl_valery_фиточай_валери_фиточай",
    "gentleman": "nl_gentleman_фиточай_джентльмен_фиточай",
    "donna bella": "nl_donna_bella_фиточай_донна_белла_фиточай",
    "every black": "черный_индийский_чай_с_душистыми_травами",
    "every deep black": "черный_цейлонский_чай",
    "every green": "зеленый_китайский_чай_с_мятой_и_лимоном",
    "every red": "красный_чай_с_малиной_и_шиповником",
    "every mix": "чайное_ассорти",
    "white tea": "white_tea_slimdose_белый_чай",
    # BADs
    "5-нтр liposomal": "5htp_liposomal_5гидрокситриптофан_липосомальный",
    "5 нтр liposomal": "5htp_liposomal_5гидрокситриптофан_липосомальный",
    "vitamin c liposomal": "vitamin_c_liposomal_витамин_с_липосомальный",
    "metabrain liposomal": "metabrain_liposomal_метабрейн_липосомальный",
    "neuromedium liposomal": "neuromedium_liposomal_нейромедиум_липосомальный",
    "be best male": "be_best_male_би_бест_мужской",
    "be best female": "be_best_female_би_бест_женский",
    "pro-indole": "proindole_проиндол",
    "lactoferra": "lactoferra_лактоферра",
    "soft sorb": "природный_сорбент_soft_sorb_софт_сорб",
    "gelm cleanse": "фитокомплекс_gelm_cleanse_гельм_клинз",
    "metaboost": "жиросжигатель_metaboost_метабуст",
    "biosetting": "протектор_biosetting_биосеттинг",
    "biotuning": "biotuning_биотюнинг",
    "biodrone": "иммуноактиватор_biodrone_биодрон",
    "metabiotic": "metabiotic_метабиотик",
    "collagentrinity": "collagentrinity_коллагентринити_со_вкусом_вишни",
    "collagen peptides вишня": "collagen_peptides_коллаген_пептидс_со_вкусом_вишни",
    "collagen peptides": "collagen_peptides_коллаген_пептидс_со_вкусом_зелён",
    "зеленый чай": "collagen_peptides_коллаген_пептидс_со_вкусом_зелён",
    "вишня": "collagen_peptides_коллаген_пептидс_со_вкусом_вишни",
    "marine collagen": "marine_collagen_морской_коллаген",
    "vitamin k2+d3": "vitamin_k2+d3_витамин_k2+d3",
    "в9в12": "vitamin_в9+в12_витамин_в9+в12",
    "d3 2000 me": "vitamin_d3_2000_me_витамин_d3",
    "magnesium marine": "marine_magnesium_морской_магний",
    "омега-3 1300мг": "omega3_1300_мг_омега3_1300_мг",
    "омега 3 1300мг": "omega3_1300_мг_омега3_1300_мг",
    "calcium marine": "calcium_marine_морской_кальций",
    "detox plus": "detox_step_1_plus_формула_очищения_кишечника",
    "ph balance stones": "картридж_для_регуляции_pн_воды_ph_balance_stones",
    # Zinc + Iron — special: assign to zinc
    "zinс (zn) и iron (fe)": "__SPLIT_ZINC_IRON__",
    "zinc (zn) и iron (fe)": "__SPLIT_ZINC_IRON__",
    # Cosmetics
    "smartum max": "восстанавливающий_гель_smartum_max",
    "сыворотка active serum": "occuba_сыворотка_против_выпадения_волос_active_ser",
    "маска мгновенного действия": "маска_мгновенного_действия_woweffect",
    "филлер-термозащита master hair": "филлертермозащита_master_hair",
    "спрей-кондиционер для волос 3-in-1": "спрейкондиционер_3in1",
    "шампунь восстанавливающий": "шампунь_восстанавливающий_silky_hair_repair",
    "кондиционер восстанавливающий": "кондиционер_восстанавливающий_silky_hair_repair",
    "маска восстанавливающая": "маска_восстанавливающая_silky_hair_repair",
    "шампунь объем и сила": "шампунь_объем_и_сила_volume_&_strength",
    "кондиционер объем и сила": "кондиционер_объем_и_сила_volume_&_strength",
    "шампунь балансирующий": "шампунь_балансирующий_shine_balance",
    "кондиционер балансирующий": "кондиционер_балансирующий_shine_balance",
    "гидрофильный бальзам": "гидрофильный_бальзам_для_снятия_макияжа_cleansing_",
    "бабл-пудра": "баблпудра_для_очищения_кожи_creamy_bubble_сleanser",
    "бабл пудра": "баблпудра_для_очищения_кожи_creamy_bubble_сleanser",
    "ночная увлажняющая маска": "ночная_маска_для_лица_deep_moisturizing_sleeping_m",
    "патчи magic glitter": "гидрогелевые_патчи_hydrogel_eye_patches_magic_glit",
    "сыворотка vitalize moisturizing serum": "увлажняющая_сыворотка_vitalize_moisturizing_serum",
    "патчи pink glow": "гидрогелевые_патчи_hydrogel_eye_patches_pink_glow",
    "пенка для умывания": "увлажняющая_пенка_для_умывания_hyaluronic_cleansin",
    "диски для очищения": "диски_для_лица_обновляющие_black_exfoliating_pads",
    "увлажняющий мист": "увлажняющий_мист_для_лица_hyaluronic_mist",
    "гидрофильное масло": "гидрофильное_масло_для_умывания_hyaluronic_cleansi",
    "очищающая маска cleansing glow mask": "очищающая_маска_для_сияния_кожи_cleansing_glow_mas",
    "гидрогелевая маска detox hydrogel mask": "гидрогелевая_маска_detox_hydrogel_mask",
    "cc dull cream": "корректирующий_крем_для_лица_cc_dull_cream",
    "легкий увлажняющий крем-гель": "легкий_увлажняющий_кремгель_light_hydrating_day_ge",
    "обогащенный ночной крем": None,  # Not in DB
    "восстанавливающий крем для контура глаз": "восстанавливающий_крем_для_контура_глаз_revitalizi",
    "восстанавливающая ночная сыворотка для лица": "восстанавливающая_ночная_сыворотка_для_лица_renewa",
    "расслабляющий крем-гель для душа relaxing": "расслабляющий_кремгель_для_душа_relaxing",
    "увлажняющий гель для душа moisturizing": "увлажняющий_гель_для_душа_moisturizing",
    "обновляющий скраб для тела renewal": "обновляющий_скраб_для_тела_renewal",
    "питательное молочко для тела nourishing": "питательное_молочко_для_тела_nourishing",
    "насыщенный крем-баттер для тела": "насыщенный_крембаттер_для_тела_rich",
    "крем для рук softening": "смягчающий_крем_для_рук_softening_100_мл",
    "крем для ног": "ухаживающий_крем_для_ног_сare",
    "biome eye cream": "крем_для_ухода_за_кожей_вокруг_глаз_biome_eye_crea",
    "biome serum": "cыворотка_для_лица_biome_serum",
    "biome 2 in 1 face cream": "двухфазный_крем_для_лица_biome_2_in_1_face_cream",
    "скраб моделирующий shaping": "скраб_моделирующий_shaping",
    "сыворотка от растяжек": "сыворотка_lifting_для_профилактики_растяжек",
    "средства с термоэффектами": "охлаждающий_антицеллюлитный_кремгель_cold",
    "для лица 50 spf": "крем_солнцезащитный_для_лица_50_spf",
    "для тела 50 spf": "крем_солнцезащитный_для_тела_50_spf",
    "универсальный бальзам the lab": "универсальный_бальзам_the_lab",
    "гель для умывания the lab": "гель_для_умывания_the_lab",
    "гель для душа и шампунь 2 в 1 the lab": "гель_для_душа_и_шампунь_2_в_1_the_lab",
    "гель для бритья the lab": "гель_для_бритья_the_lab",
    "дезодорант мужской the lab": None,  # No "дезодорант The Lab" in DB, closest is дезодоранткристалл
    "дезодорант crispento silver": "дезодоранткристалл_для_тела_silver",
    # Toothpastes
    "sensitive": "зубная_паста_для_чувствительных_зубов_и_десен_sens",
    "white": "зубная_паста_отбеливающая_white",
    "protect": "зубная_паста_реминерализующая_protect",
    # 3D Slim
    "green low carb": "draineffect_green_low_carb_дрейнэффект_грин_низкоу",
    "red low carb": "draineffect_red_low_carb_дрейнэффект_рэд_низкоугле",
    "3d slim program": None,  # Collection/program shot
    "green": "draineffect_green_low_carb_дрейнэффект_грин_низкоу",  # duplicate
    # Kids
    "happy smile": "пастилки_happy_smile_витаминизированные_60_шт",
    "средство для купания 3 в 1, 0+": "средство_для_купания_3_в_1_0+",
    "нежное детское молочко для тела, 0+": "нежное_детское_молочко_для_тела_0+",
    "детский крем с пантенолом, 0+": "детский_крем_с_пантенолом_0+",
    "мягкий детский гель для душа, 3+": "мягкий_детский_гель_для_душа_3+",
    "заботливый детский шампунь, 3+": "заботливый_детский_шампунь_3+",
    "детская зубная паста, 2+": "детская_зубная_паста_2+",
    "liquid ca+ for kids": "liquid_ca+_for_kids_кальций_для_детей",
    "omega-3 dha": "omega3_dha_омега3_дгк",
    "omega 3 dha": "omega3_dha_омега3_дгк",
    "vision lecithin — детское зрение": "vision_lecithin_детское_зрение",
    "vision lecithin детское зрение": "vision_lecithin_детское_зрение",
    "prohelper": "prohelper_прохелпер_мультивитаминный_комплекс",
    "prohelper - прохелпер - мультивитаминный комплекс": "prohelper_прохелпер_мультивитаминный_комплекс",
    "mg+b6 kids - магний для детей": "mg+b6_kids_магний_+_b6_для_детей",
    "mg+b6 kids": "mg+b6_kids_магний_+_b6_для_детей",
    # Imperial Herb
    "lymph gyan": "lymph_gyan_лимф_гян_лимфодренаж",
    "lux gyan": "lux_gyan_люкс_гян_очищение_кишечника",
    "uri gyan": "uri_gyan_ури_гян_поддержка_почек",
    "livo gyan": "livo_gyan_ливо_гян_поддержка_печени",
    "gut vigyan": "gut_vigyan_гат_вигян_восстановление_кишечника",
    # Misc
    "горячий напиток малина": "горячий_напиток_малина",
    'горячий напиток "малина"': "горячий_напиток_малина",
    # Not in DB — skip
    "fineffect textile": None,
    "японская аквапудра": None,
    "концентраты для стирки": None,
    "гель для мытья посуды gloss power": None,
    "fineffect уборка": None,
    "мыло-пенка для рук": None,
    "коллекция": None,  # Generic collection shot
    "energy pro": None,  # Not in DB
    "протеин energy pro": None,  # Not in DB
    # Жидкие патчи — not in DB as products
    "жидкие патчи с гуминами": None,
    "жидкие патчи anti-dark circles": None,
    "жидкие патчи shine & antistress": None,
}


def clean_label(text: str) -> str:
    """Remove emoji, special chars, normalize whitespace."""
    text = EMOJI_PATTERN.sub("", text)
    text = text.replace("▫️", "").replace("◾", "").replace("◽", "")
    text = text.replace("«", "").replace("»", "").replace('"', "").replace("'", "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize(text: str) -> str:
    """Lowercase + strip punctuation for comparison."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s+]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_text(msg) -> str:
    """Extract text from a Telegram message."""
    text_parts = msg.get("text", "")
    if isinstance(text_parts, list):
        text_parts = "".join(
            p if isinstance(p, str) else p.get("text", "")
            for p in text_parts
        )
    return clean_label(str(text_parts))


def parse_export(json_path: Path):
    """Parse Telegram export into groups of (labels, photo_paths).

    Logic: text messages accumulate as labels. When a photo arrives:
    - If we have accumulated labels -> start new group
    - If no labels accumulated -> continue last group (album photo)
    """
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    groups = []
    current_labels = []

    for msg in data.get("messages", []):
        if msg.get("type") != "message":
            continue

        has_photo = "photo" in msg and msg["photo"]

        if not has_photo:
            # Text message = label
            text = extract_text(msg)
            if text and len(text) > 1:
                current_labels.append(text)
        else:
            # Photo message
            photo_path = msg["photo"]
            caption = extract_text(msg)
            if caption and len(caption) > 1:
                current_labels.append(caption)

            if current_labels:
                # We have new labels -> start new group
                groups.append({
                    "labels": list(current_labels),
                    "photos": [photo_path],
                })
                current_labels = []
            elif groups:
                # No new labels -> album photo, add to last group
                groups[-1]["photos"].append(photo_path)
            else:
                # Very first photo with no labels
                groups.append({
                    "labels": [],
                    "photos": [photo_path],
                })

    return groups


def load_products(db_path: Path) -> dict:
    """Load products DB, return {key: product_data}."""
    with open(db_path, encoding="utf-8") as f:
        data = json.load(f)
    products = {}
    for cat_name, cat_products in data.get("categories", {}).items():
        for p in cat_products:
            key = p.get("key", "")
            if key:
                products[key] = p
    return products


def find_match(labels: list[str], products: dict) -> str | None:
    """Find best matching product key for a group's labels."""
    # Try manual overrides first (check all labels)
    for label in labels:
        norm = normalize(label)
        # Direct match
        if norm in MANUAL_OVERRIDES:
            return MANUAL_OVERRIDES[norm]
        # Check with quotes removed
        norm_noquote = norm.replace('"', '').replace("'", "")
        if norm_noquote in MANUAL_OVERRIDES:
            return MANUAL_OVERRIDES[norm_noquote]

    # Fuzzy match against product names
    best_key = None
    best_score = 0.0

    for label in labels:
        norm_label = normalize(label)
        for key, product in products.items():
            name = normalize(product["name"])
            # SequenceMatcher similarity
            score = SequenceMatcher(None, norm_label, name).ratio()
            # Bonus if label words are subset of name words
            label_words = set(norm_label.split())
            name_words = set(name.split())
            if label_words and label_words.issubset(name_words):
                score = max(score, 0.85)
            if score > best_score and score >= 0.5:
                best_score = score
                best_key = key

    return best_key


def main():
    import sys
    dry_run = "--dry-run" in sys.argv

    print("=" * 70)
    print(f"  DISTRIBUTE PHOTOS v2 — Product Key Based {'(DRY RUN)' if dry_run else ''}")
    print("=" * 70)

    # Load data
    groups = parse_export(EXPORT_JSON)
    products = load_products(DB_PATH)
    print(f"\nExport groups: {len(groups)}")
    print(f"Total photos: {sum(len(g['photos']) for g in groups)}")
    print(f"Products in DB: {len(products)}")

    # Match groups to product keys
    matches = []  # (group_idx, product_key, labels, photos)
    skipped = []
    split_zinc_iron = []

    for i, group in enumerate(groups):
        labels = group["labels"]
        photos = group["photos"]
        label_str = labels[0] if labels else f"(no label, group {i})"

        key = find_match(labels, products)

        if key == "__SPLIT_ZINC_IRON__":
            # Special: copy to both zinc and iron
            split_zinc_iron.append((i, labels, photos))
            matches.append((i, "zinc_(zn)_цинк", labels, photos))
            matches.append((i, "iron_(fe)_железо", labels, photos))
            print(f"  [SPLIT] #{i+1:3d} ({len(photos)} фото) {label_str}")
            print(f"           -> zinc_(zn)_цинк + iron_(fe)_железо")
        elif key is None:
            skipped.append((i, labels, photos))
            print(f"  [SKIP ] #{i+1:3d} ({len(photos)} фото) {label_str}")
        elif key not in products:
            skipped.append((i, labels, photos))
            print(f"  [MISS ] #{i+1:3d} ({len(photos)} фото) {label_str} -> key not in DB: {key}")
        else:
            matches.append((i, key, labels, photos))
            print(f"  [ OK  ] #{i+1:3d} ({len(photos)} фото) {label_str}")
            print(f"           -> {key}")

    print(f"\n--- ИТОГО ---")
    print(f"Матчей:     {len(matches)}")
    print(f"Пропущено:  {len(skipped)}")
    total_photos_matched = sum(len(photos) for _, _, _, photos in matches)
    total_photos_skipped = sum(len(photos) for _, _, photos in skipped)
    print(f"Фоток сматчено: {total_photos_matched}")
    print(f"Фоток пропущено: {total_photos_skipped}")

    if skipped:
        print(f"\nПропущенные группы:")
        for i, labels, photos in skipped:
            print(f"  #{i+1}: {labels[0] if labels else '(no label)'} ({len(photos)} фото)")

    if dry_run:
        print("\n--- DRY RUN: без копирования и удаления ---")
        return

    # Auto-proceed (no interactive confirmation needed)

    # Delete old content
    print(f"\n{'='*70}")
    print(f"  УДАЛЕНИЕ СТАРОГО КОНТЕНТА")
    print(f"{'='*70}")
    if MEDIA_PATH.exists():
        for item in MEDIA_PATH.iterdir():
            if item.is_dir():
                shutil.rmtree(item, ignore_errors=True)
                print(f"  Удалено: {item.name}/")
        print(f"  Старые папки удалены")
    else:
        MEDIA_PATH.mkdir(parents=True)
        print(f"  Создана папка: {MEDIA_PATH}")

    # Copy photos
    print(f"\n{'='*70}")
    print(f"  КОПИРОВАНИЕ ФОТОК")
    print(f"{'='*70}")
    copied = 0
    errors = 0
    products_with_photos = set()

    for group_idx, key, labels, photos in matches:
        dest_dir = MEDIA_PATH / key / "photos"
        dest_dir.mkdir(parents=True, exist_ok=True)

        for photo_idx, photo_rel in enumerate(photos):
            src = EXPORT_DIR / photo_rel
            if not src.exists():
                print(f"  [ERR] Файл не найден: {src}")
                errors += 1
                continue

            dest = dest_dir / f"{photo_idx + 1}.jpg"
            shutil.copy2(src, dest)
            copied += 1

        products_with_photos.add(key)

    print(f"\nСкопировано: {copied} фоток")
    print(f"Ошибок: {errors}")
    print(f"Продуктов с фотками: {len(products_with_photos)}")

    # Update products_database.json
    print(f"\n{'='*70}")
    print(f"  ОБНОВЛЕНИЕ products_database.json")
    print(f"{'='*70}")
    with open(DB_PATH, encoding="utf-8") as f:
        db = json.load(f)

    updated = 0
    for cat_name, cat_products in db.get("categories", {}).items():
        for product in cat_products:
            key = product.get("key", "")
            if key in products_with_photos:
                product["image_folder"] = key
                photos_dir = MEDIA_PATH / key / "photos"
                photo_count = len(list(photos_dir.glob("*.jpg")))
                product["image_count"] = photo_count
                updated += 1
            else:
                product["image_folder"] = None
                product["image_count"] = 0

    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

    print(f"Обновлено продуктов: {updated}")
    print(f"Без фоток: {len(products) - len(products_with_photos)}")

    print(f"\n{'='*70}")
    print(f"  ГОТОВО!")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
