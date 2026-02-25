"""
Import product photos from Telegram chat export into unified_products.
Uses MANUAL mapping (export name → product key) for 100% accuracy.
Also cleans catalog: deletes Energy Diet, products without photos, empty categories.
"""
import json
import shutil
import re
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
EXPORT_DIR = Path(r"C:\Users\mafio\Downloads\Telegram Desktop") / "'rcgjhn yjdsq"
EXPORT_JSON = EXPORT_DIR / "result.json"
PRODUCTS_DB = PROJECT_ROOT / "content" / "products_database.json"
UNIFIED_PRODUCTS = PROJECT_ROOT / "content" / "unified_products"

# ============================================================
# MANUAL MAPPING: export product name → catalog product key
# None = skip (not in catalog / will be deleted)
# ============================================================
EXPORT_TO_CATALOG = {
    # === ED Smart 5.0 ===
    '🫐 Smart Classic 5.0 Ягодная панна-котта': 'ed_smart_classic_ягодная_паннакотта_15_порций',
    '☕️ Smart 5.0 Classic Кофе': 'ed_smart_classic_кофе_15_порций',
    '🍫 Smart 5.0 Classic Шоколадный брауни': 'ed_smart_classic_шоколадный_брауни_15_порций',
    '🍨 Smart 5.0 Classic Ванильный пломбир': 'ed_smart_classic_ванильный_пломбир_15_порций',
    '🐤 Smart 5.0 Курица': 'ed_smart_soup_курица_15_порций',
    '🍪 Smart 5.0 Имбирный пряник': 'ed_smart_classic_имбирный_пряник_15_порций',

    # === ED Smart 4.0 ===
    '🍋 ED Smart 4.0 «Лимонное печенье»': 'ed_smart_classic_лимонное_печенье_15_порций',
    '🍌 ED Smart 4.0 «Банановый сплит»': 'ed_smart_classic_банановый_сплит_15_порций',
    '🍐 ED Smart 4.0 «Грушевый тарт»': 'ed_smart_classic_грушевый_тарт_15_порций',
    '🍒 ED Smart 4.0 «Вишневый брауни»': 'ed_smart_classic_вишневый_брауни_15_порций',
    '🍫 ED Smart 4.0 «Бельгийский шоколад»': 'ed_smart_classic_бельгийский_шоколад_15_порций',
    '🫐 ED Smart 4.0 «Черничный йогурт»': 'ed_smart_classic_черничный_йогурт_15_порций',
    '🧁️ ED Smart 4.0 «Ваниль»': 'ed_smart_classic_ваниль_15_порций',
    '🍦 ED Smart Milky "Фисташковое мороженое"': 'ed_smart_milky_фисташковое_мороженое_15_порций',
    '🥜 ED Smart Milky «Арахис в карамели»': 'ed_smart_milky_арахис_в_карамели_15_порций',
    '☕️ ED Smart Milky «Кофе с молоком»': None,  # Not in catalog

    # === Energy Diet (SKIP — will be deleted) ===
    '💚Фисташка': None,
    '🧡Соленая карамель': None,
    '🍌Банан': None,
    '🍨Ваниль': None,
    '🍓Клубника': None,
    '🍫Шоколад': None,
    '🍄Грибы': None,

    # === Перекусы ===
    '🍪 Печенье с суфле': 'микс_протеинового_печенья_nl_с_суфле',
    '🏆 Батончики Energy Pro': None,  # Not in catalog
    '💪 Протеин Energy Pro': None,  # Not in catalog
    '🥧 Фисташковый тарт': None,  # Not in catalog
    '🍫 Шоколадный брауни': None,  # Snack bar, not ED Smart
    '🥜 Соленая карамель и арахис': None,  # Snack bar
    '🥥 Кокосовый раф': None,  # Not in catalog
    '🤍 Коллекция': None,  # Unclear product

    # === БАДы — Адаптогены ===
    '🚁 BioDrone': 'иммуноактиватор_biodrone_биодрон',
    '🧬BioTuning': 'biotuning_биотюнинг',
    '💟 Biosetting': 'протектор_biosetting_биосеттинг',
    '🧊PH Balance Stones': 'картридж_для_регуляции_pн_воды_ph_balance_stones',

    # === БАДы — Коллаген ===
    '🔺 CollagenTrinity': 'collagentrinity_коллагентринити_со_вкусом_вишни',
    '🧬Collagen Peptides': None,  # Ambiguous — cherry or green tea? Skip.
    '🍒 Collagen Peptides Вишня': 'collagen_peptides_коллаген_пептидс_со_вкусом_вишни',
    '🍒 Вишня': None,  # Duplicate of above, skip
    '🫧 Marine Collagen': 'marine_collagen_морской_коллаген',

    # === БАДы — Be Best ===
    '♂️ Be Best Male': 'be_best_male_би_бест_мужской',
    '♀️ Be Best Female': 'be_best_female_би_бест_женский',

    # === БАДы — Витамины и минералы ===
    '🤍 Magnesium Marine': 'marine_magnesium_морской_магний',
    '🐟D3 2000 ME': 'vitamin_d3_2000_me_витамин_d3',
    '💛Омега-3 1300мг': 'omega3_1300_мг_омега3_1300_мг',
    '▫️▫️Vitamin K2+D3': 'vitamin_k2+d3_витамин_k2+d3',
    '▪️Zinс (Zn) и Iron (Fe)': 'zinc_(zn)_цинк',  # 2 photos — also copy to Iron
    '▫️В9В12': 'vitamin_в9+в12_витамин_в9+в12',
    '🐚Calcium Marine': 'calcium_marine_морской_кальций',

    # === БАДы — Greenflash ===
    '🥦Pro-indole': 'proindole_проиндол',
    '☁️Metabiotic': 'metabiotic_метабиотик',
    '🥛Lactoferra': 'lactoferra_лактоферра',
    'Soft Sorb': 'природный_сорбент_soft_sorb_софт_сорб',
    'Gelm Cleanse': 'фитокомплекс_gelm_cleanse_гельм_клинз',
    '🥤Beauty blend': 'beauty_blend_бьюти_бленд',
    '🍊MetaBoost': 'жиросжигатель_metaboost_метабуст',

    # === БАДы — Липосомальные ===
    '🌟5-НТР liposomal': '5htp_liposomal_5гидрокситриптофан_липосомальный',
    '🌟Neuromedium liposomal': 'neuromedium_liposomal_нейромедиум_липосомальный',
    '🌟Vitamin C liposomal': 'vitamin_c_liposomal_витамин_с_липосомальный',
    '🌟Metabrain liposomal': 'metabrain_liposomal_метабрейн_липосомальный',

    # === БАДы — Detox ===
    'Detox PLUS🌿': 'detox_step_1_plus_формула_очищения_кишечника',

    # === Красота — Occuba для волос ===
    'Шампунь восстанавливающий': 'шампунь_восстанавливающий_silky_hair_repair',
    'Шампунь объем и сила': 'шампунь_объем_и_сила_volume_&_strength',
    'Шампунь балансирующий': 'шампунь_балансирующий_shine_balance',
    'Кондиционер восстанавливающий': 'кондиционер_восстанавливающий_silky_hair_repair',
    'Кондиционер объем и сила': 'кондиционер_объем_и_сила_volume_&_strength',
    'Кондиционер балансирующий': 'кондиционер_балансирующий_shine_balance',
    'Спрей-кондиционер для волос 3-in-1': 'спрейкондиционер_3in1',
    'Маска восстанавливающая': 'маска_восстанавливающая_silky_hair_repair',
    'Маска мгновенного действия': 'маска_мгновенного_действия_woweffect',
    'Сыворотка Active Serum': 'occuba_сыворотка_против_выпадения_волос_active_ser',
    'Филлер-термозащита Master Hair': 'филлертермозащита_master_hair',

    # === Красота — Косметика BL для тела ===
    '💕 Увлажняющий гель для душа Moisturizing': 'увлажняющий_гель_для_душа_moisturizing',
    '💟 Питательное молочко для тела Nourishing': 'питательное_молочко_для_тела_nourishing',
    '💟✨ Обновляющий скраб для тела Renewal': 'обновляющий_скраб_для_тела_renewal',
    '⌛️Скраб моделирующий Shaping': 'скраб_моделирующий_shaping',
    '💠Дезодорант Crispento Silver': 'дезодоранткристалл_для_тела_silver',
    '💞 Расслабляющий крем-гель для душа Relaxing': 'расслабляющий_кремгель_для_душа_relaxing',
    '✨ Насыщенный крем-баттер для тела': 'насыщенный_крембаттер_для_тела_rich',
    '🩴 Крем для ног': 'ухаживающий_крем_для_ног_сare',
    '💞 Крем для рук Softening': 'смягчающий_крем_для_рук_softening_100_мл',
    '🧴Сыворотка от растяжек': 'сыворотка_lifting_для_профилактики_растяжек',
    # Термоэффекты: 3 фото в экспорте (Cold, Hot, пара). Фото разделены вручную:
    # photo_51 -> Cold/1.jpg, photo_52 -> Hot/1.jpg, photo_53 -> Cold/2.jpg
    '❤️‍🔥 Средства с термоэффектами': 'охлаждающий_антицеллюлитный_кремгель_cold',

    # === Красота — BL Oriental ===
    '🌸Гидрогелевая маска Detox hydrogel mask': 'гидрогелевая_маска_detox_hydrogel_mask',
    '🌸 Бабл-пудра': 'баблпудра_для_очищения_кожи_creamy_bubble_сleanser',
    '🌸Диски для очищения': 'диски_для_лица_обновляющие_black_exfoliating_pads',
    '🌸Восстанавливающий крем для контура глаз': 'восстанавливающий_крем_для_контура_глаз_revitalizi',
    '🌸Легкий увлажняющий крем-гель': 'легкий_увлажняющий_кремгель_light_hydrating_day_ge',
    '🌸CC dull cream': 'корректирующий_крем_для_лица_cc_dull_cream',
    '🌸Сыворотка Vitalize moisturizing serum': 'увлажняющая_сыворотка_vitalize_moisturizing_serum',
    '🌸Восстанавливающая ночная сыворотка для лица': 'восстанавливающая_ночная_сыворотка_для_лица_renewa',
    '🌸 Ночная увлажняющая маска': 'ночная_маска_для_лица_deep_moisturizing_sleeping_m',
    '🌸Очищающая маска Cleansing Glow Mask': 'очищающая_маска_для_сияния_кожи_cleansing_glow_mas',
    '🌸Гидрофильное масло': 'гидрофильное_масло_для_умывания_hyaluronic_cleansi',
    '🌸 Гидрофильный бальзам': 'гидрофильный_бальзам_для_снятия_макияжа_cleansing_',
    '🌸Увлажняющий мист': 'увлажняющий_мист_для_лица_hyaluronic_mist',
    '🌸Пенка для умывания': 'увлажняющая_пенка_для_умывания_hyaluronic_cleansin',
    '🌸 Патчи Magic Glitter': 'гидрогелевые_патчи_hydrogel_eye_patches_magic_glit',
    '🌸 Патчи Pink Glow': 'гидрогелевые_патчи_hydrogel_eye_patches_pink_glow',
    '🌸Обогащенный ночной крем': None,  # Not in catalog
    '🌸 Японская аквапудра': None,  # Not in catalog
    '✨ Жидкие патчи Anti-Dark circles': None,  # Not in catalog
    '✨ Жидкие патчи Shine & Antistress': None,  # Not in catalog
    '🪭 Жидкие патчи с гуминами': None,  # Not in catalog

    # === Красота — Biome ===
    'Biome 2 in 1 Face Cream': 'двухфазный_крем_для_лица_biome_2_in_1_face_cream',
    'Biome Eye cream': 'крем_для_ухода_за_кожей_вокруг_глаз_biome_eye_crea',
    'Biome Serum': 'cыворотка_для_лица_biome_serum',

    # === Красота — BL Sun ===
    '☀️Для лица 50 SPF': 'крем_солнцезащитный_для_лица_50_spf',
    '☀️Для тела 50 SPF': 'крем_солнцезащитный_для_тела_50_spf',

    # === Красота — The Lab ===
    'Гель для бритья The LAB': 'гель_для_бритья_the_lab',
    'Гель для душа и шампунь 2 в 1 The LAB': 'гель_для_душа_и_шампунь_2_в_1_the_lab',
    'Гель для умывания The LAB': 'гель_для_умывания_the_lab',
    'Дезодорант мужской The LAB': 'дезодорант_мужской_the_lab',
    'Универсальный бальзам The LAB': 'универсальный_бальзам_the_lab',

    # === Красота — Другое ===
    '🆘 Smartum MAX': 'восстанавливающий_гель_smartum_max',

    # === Красота — Sklaer ===
    'White': 'зубная_паста_отбеливающая_white',
    'Protect': 'зубная_паста_реминерализующая_protect',
    'Sensitive': 'зубная_паста_для_чувствительных_зубов_и_десен_sens',

    # === 3D Slim ===
    '🟢 Green Low Carb': 'draineffect_green_low_carb_дрейнэффект_грин_низкоу',
    '🔴 RED Low Carb': 'draineffect_red_low_carb_дрейнэффект_рэд_низкоугле',
    '🌱White Tea': 'white_tea_slimdose_белый_чай',
    '👯3D Slim program': None,  # Not a separate product

    # === Для детей ===
    'Заботливый детский шампунь, 3+': 'заботливый_детский_шампунь_3+',
    'Нежное детское молочко для тела, 0+': 'нежное_детское_молочко_для_тела_0+',
    'Мягкий детский гель для душа, 3+': 'мягкий_детский_гель_для_душа_3+',
    'Omega-3 DHA': 'omega3_dha_омега3_дгк',
    '🍊Happy Smile': 'пастилки_happy_smile_витаминизированные_60_шт',
    'Детская зубная паста, 2+': 'детская_зубная_паста_2+',
    'Mg+B6 Kids - Магний для детей': 'mg+b6_kids_магний_+_b6_для_детей',
    'PROHELPER - ПРОХЕЛПЕР - Мультивитаминный комплекс': 'prohelper_прохелпер_мультивитаминный_комплекс',
    'Liquid Ca+ for kids': 'liquid_ca+_for_kids_кальций_для_детей',
    'Vision Lecithin — детское зрение': 'vision_lecithin_детское_зрение',
    'Детский крем с пантенолом, 0+': 'детский_крем_с_пантенолом_0+',
    'Средство для купания 3 в 1, 0+': 'средство_для_купания_3_в_1_0+',

    # === Чай и напитки ===
    '🍵 Зеленый чай': None,  # This is Collagen Peptides green tea flavor, NOT Enerwood tea
    'Горячий напиток «Малина»': 'горячий_напиток_малина',
    'Lux': 'nl_lux_фиточай_люкс_фиточай',
    'Vodoley': 'nl_vodoley_фиточай_водолей_фиточай',
    'Liverpool': 'nl_liverpool_фиточай_ливерпуль_фиточай',
    'Prana': 'nl_prana_фиточай_прана_фиточай',
    'Valery': 'nl_valery_фиточай_валери_фиточай',
    'Gentleman': 'nl_gentleman_фиточай_джентльмен_фиточай',
    'Donna Bella': 'nl_donna_bella_фиточай_донна_белла_фиточай',

    # === Imperial Herb ===
    'GUT VIGYAN': 'gut_vigyan_гат_вигян_восстановление_кишечника',
    'LYMPH GYAN': 'lymph_gyan_лимф_гян_лимфодренаж',
    'LIVO GYAN': 'livo_gyan_ливо_гян_поддержка_печени',
    'URI GYAN': 'uri_gyan_ури_гян_поддержка_почек',
    'LUX GYAN': 'lux_gyan_люкс_гян_очищение_кишечника',

    # === Парфюмерия Every (not in catalog) ===
    'Every Black': None,
    'Every Deep Black': None,
    'Every Green': None,
    'Every Mix': None,
    'Every Red': None,

    # === Для дома (category removed) ===
    'Fineffect Textile ✨': None,
    '▫️Fineffect Уборка': None,
    '🎽Концентраты для стирки': None,
    '💦Гель для мытья посуды Gloss Power': None,
    '☁️Мыло-пенка для рук': None,

    # === Масло для душа (separate from гидрофильное масло!) ===
    # Not in export directly — масло_для_душа keeps its existing photo

    # === Collagen green tea ===
    '🟢Green': 'collagen_peptides_коллаген_пептидс_со_вкусом_зелён',
}

# Extra copies: Zinc/Iron photo goes to both products
EXTRA_COPIES = {
    '▪️Zinс (Zn) и Iron (Fe)': 'iron_(fe)_железо',
}

# Also copy Softening photo to 30ml version
EXTRA_COPIES_2 = {
    '💞 Крем для рук Softening': 'смягчающий_крем_для_рук_softening_30_мл',
}


def parse_export(export_json):
    """Parse result.json and build product_name -> [photo_paths] mapping.
    Keeps raw product names with emojis for manual mapping.
    """
    with open(export_json, 'r', encoding='utf-8') as f:
        data = json.load(f)

    messages = data.get('messages', [])
    product_photos = {}
    last_text = None

    for msg in messages:
        if msg.get('type') != 'message':
            continue

        has_photo = 'photo' in msg and msg['photo']
        text = msg.get('text', '')
        if isinstance(text, list):
            text = ''.join(
                t if isinstance(t, str) else t.get('text', '')
                for t in text
            )
        text = text.strip()

        # Normalize non-breaking spaces to regular spaces
        text = text.replace('\xa0', ' ')

        if has_photo:
            if last_text:
                if last_text not in product_photos:
                    product_photos[last_text] = []
                product_photos[last_text].append(msg['photo'])
        elif text:
            last_text = text

    return product_photos


def copy_photos_for_key(product_key, photo_paths, export_dir, unified_dir):
    """Copy photos to unified_products/{key}/photos/."""
    target_dir = unified_dir / product_key / "photos"
    target_dir.mkdir(parents=True, exist_ok=True)

    # Clear old photos first
    for old in target_dir.glob("*.jpg"):
        old.unlink()

    copied = 0
    for i, photo_path in enumerate(photo_paths, 1):
        src = export_dir / photo_path
        dst = target_dir / f"{i}.jpg"
        if src.exists():
            shutil.copy2(src, dst)
            copied += 1
    return copied


def main():
    print("=" * 60)
    print("IMPORT PHOTOS (MANUAL MAPPING) + CLEAN CATALOG")
    print("=" * 60)

    # 1. Parse export
    print(f"\n1. Parsing export...")
    export_map = parse_export(EXPORT_JSON)
    print(f"   Found {len(export_map)} products with photos in export")

    # 2. Load catalog
    print(f"\n2. Loading catalog...")
    with open(PRODUCTS_DB, 'r', encoding='utf-8') as f:
        db = json.load(f)

    # Build key set for validation
    all_keys = set()
    for products in db['categories'].values():
        for p in products:
            all_keys.add(p['key'])

    # 3. Validate mapping
    print(f"\n3. Validating mapping...")
    mapped = 0
    skipped = 0
    unmapped_export = []
    bad_keys = []

    for export_name in export_map:
        if export_name in EXPORT_TO_CATALOG:
            key = EXPORT_TO_CATALOG[export_name]
            if key is None:
                skipped += 1
            elif key in all_keys:
                mapped += 1
            else:
                bad_keys.append((export_name, key))
        else:
            unmapped_export.append(export_name)

    print(f"   Mapped: {mapped}")
    print(f"   Skipped (not in catalog): {skipped}")
    print(f"   Unmapped from export: {len(unmapped_export)}")
    if unmapped_export:
        for name in sorted(unmapped_export):
            print(f"     ? {name} [{len(export_map[name])} photo(s)]")
    if bad_keys:
        print(f"   BAD KEYS (product key not found!):")
        for name, key in bad_keys:
            print(f"     ! {name} -> {key}")
        print("   ABORTING due to bad keys!")
        return

    # 4. Copy photos
    print(f"\n4. Copying photos...")
    total_copied = 0
    matched_keys = set()

    for export_name, photos in export_map.items():
        key = EXPORT_TO_CATALOG.get(export_name)
        if key is None:
            continue

        n = copy_photos_for_key(key, photos, EXPORT_DIR, UNIFIED_PRODUCTS)
        total_copied += n
        matched_keys.add(key)
        print(f"   [{n} photos] {key}")

        # Extra copies (Zinc→Iron, Softening→30ml)
        extra_key = EXTRA_COPIES.get(export_name) or EXTRA_COPIES_2.get(export_name)
        if extra_key and extra_key in all_keys:
            n2 = copy_photos_for_key(extra_key, photos, EXPORT_DIR, UNIFIED_PRODUCTS)
            total_copied += n2
            matched_keys.add(extra_key)
            print(f"   [{n2} photos] {extra_key} (extra copy)")

    print(f"\n   Total copied: {total_copied} photos for {len(matched_keys)} products")

    # 5. Update image_count in DB for matched products
    print(f"\n5. Updating database...")
    for cat_name, products in db['categories'].items():
        for p in products:
            if p['key'] in matched_keys:
                # Count actual photos on disk
                photo_dir = UNIFIED_PRODUCTS / p['key'] / "photos"
                count = len(list(photo_dir.glob("*.jpg"))) if photo_dir.exists() else 0
                p['image_folder'] = p['key']
                p['image_count'] = count

    # 6. Delete Energy Diet products
    print(f"\n6. Deleting Energy Diet products...")
    func_pit = db['categories'].get('Функциональное питание', [])
    energy_diet = [p for p in func_pit if p.get('line') == 'Energy Diet']
    print(f"   Found {len(energy_diet)} Energy Diet products to delete:")
    for p in energy_diet:
        print(f"     - {p['name']}")
    db['categories']['Функциональное питание'] = [
        p for p in func_pit if p.get('line') != 'Energy Diet'
    ]

    # 7. Delete products without photos (image_count == 0)
    print(f"\n7. Deleting products without photos...")
    deleted = []
    for cat_name in list(db['categories'].keys()):
        products = db['categories'][cat_name]
        to_keep = []
        for p in products:
            if p.get('image_count', 0) == 0:
                deleted.append((cat_name, p['name']))
                print(f"     - [{cat_name}] {p['name']}")
            else:
                to_keep.append(p)
        db['categories'][cat_name] = to_keep
    print(f"   Deleted {len(deleted)} products without photos")

    # 8. Delete empty categories
    print(f"\n8. Cleaning empty categories...")
    empty = [cat for cat, prods in db['categories'].items() if len(prods) == 0]
    for cat in empty:
        print(f"     - Deleting empty category: {cat}")
        del db['categories'][cat]

    # 9. Recalculate totals
    total = sum(len(prods) for prods in db['categories'].values())
    db['total_products'] = total
    print(f"\n9. Final catalog: {total} products in {len(db['categories'])} categories")
    for cat_name, products in db['categories'].items():
        print(f"     {cat_name}: {len(products)} products")

    # 10. Save
    with open(PRODUCTS_DB, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, indent=2)
    print(f"\n10. Saved {PRODUCTS_DB}")

    print("\n" + "=" * 60)
    print("DONE!")
    print("=" * 60)


if __name__ == '__main__':
    main()
