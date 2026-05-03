import xml.etree.ElementTree as ET
import re
import html as html_lib
import pymorphy3
from playwright.sync_api import sync_playwright

# --- НАСТРОЙКИ И ССЫЛКИ ---
OUTPUT_FILE = "aqvilegia_optimized.xml"
MAX_DESC_LENGTH = 150

# Тексты для фида
OFFER_DESCRIPTION = "Доставка свежих букетов роз в Москве"
COLLECTION_PROMO_TEXT = "Доставка 24/7. Фото перед отправкой. Бесплатные консультации флористов"

# Список ссылок
URLS = [
    "https://aqvilegia.ru/11br", "https://aqvilegia.ru/49mrp", "https://aqvilegia.ru/25mrp",
    "https://aqvilegia.ru/49brp", "https://aqvilegia.ru/25brp", "https://aqvilegia.ru/49krp",
    "https://aqvilegia.ru/101kmr", "https://aqvilegia.ru/101mixkbr", "https://aqvilegia.ru/101mr",
    "https://aqvilegia.ru/101orr", "https://aqvilegia.ru/101zr", "https://aqvilegia.ru/101rj",
    "https://aqvilegia.ru/101or", "https://aqvilegia.ru/101srr", "https://aqvilegia.ru/101br",
    "https://aqvilegia.ru/101kr", "https://aqvilegia.ru/51br", "https://aqvilegia.ru/51pionr",
    "https://aqvilegia.ru/51kremr", "https://aqvilegia.ru/51or", "https://aqvilegia.ru/51mr",
    "https://aqvilegia.ru/51srr", "https://aqvilegia.ru/51rj", "https://aqvilegia.ru/51mixkbr",
    "https://aqvilegia.ru/51kr", "https://aqvilegia.ru/31kremr", "https://aqvilegia.ru/31srr",
    "https://aqvilegia.ru/31or", "https://aqvilegia.ru/31mr", "https://aqvilegia.ru/31br",
    "https://aqvilegia.ru/31nrr", "https://aqvilegia.ru/31kr", "https://aqvilegia.ru/25krp",
    "https://aqvilegia.ru/21kremr", "https://aqvilegia.ru/21srr", "https://aqvilegia.ru/21or",
    "https://aqvilegia.ru/21mr", "https://aqvilegia.ru/21nrr", "https://aqvilegia.ru/21br",
    "https://aqvilegia.ru/21kr", "https://aqvilegia.ru/11nrr", "https://aqvilegia.ru/11ri",
    "https://aqvilegia.ru/11kr",
    "https://aqvilegia.ru/11rose", "https://aqvilegia.ru/21rose", "https://aqvilegia.ru/31rose",
    "https://aqvilegia.ru/51rose", "https://aqvilegia.ru/101rose"
]

URLS = list(dict.fromkeys(URLS))  # Удаляем дубли

morph = pymorphy3.MorphAnalyzer()

# --- СЛОВАРИ И БАЗЫ ДАННЫХ ---
FLOWER_ROOTS = "роз|пион|гипсофил|хризантем|альстромери|гвоздик|георгин|калл|лили|орхиде|ромаш|тюльпан|эустом|маттиол|гортензи|ирис|гербер|ранункулюс|подсолнух|сирен|диантус"

FLOWER_REGEX_MAP = {
    r'\bроз[аыуе]?\b': 'роз', r'\bпион[аыуов]?\b': 'пионов', r'\bгипсофил[аыуе]?\b': 'гипсофил',
    r'\bхризантем[аыуе]?\b': 'хризантем', r'\bальстромери[яиюей]?\b': 'альстромерий',
    r'\bгвоздик[аиуе]?\b': 'гвоздик', r'\bгеоргин[аыуов]?\b': 'георгин', r'\bкалл[аыуе]?\b': 'калл',
    r'\bлили[яиюей]?\b': 'лилий', r'\bорхиде[яиюей]?\b': 'орхидей', r'\bромаш(?:ка|ки|ку|ке|ек)\b': 'ромашек',
    r'\bтюльпан[аыуов]?\b': 'тюльпанов', r'\bэустом[аыуе]?\b': 'эустом', r'\bматтиол[аыуе]?\b': 'маттиол',
    r'\bгортензи[яиюей]?\b': 'гортензий', r'\bирис[аыуов]?\b': 'ирисов', r'\bгербер[аыуе]?\b': 'гербер',
    r'\bподсолнух[аиов]?\b': 'подсолнухов', r'\bсирен[ьяию]?\b': 'сирени', r'\bранункулюс[аыуов]?\b': 'ранункулюсов',
    r'\bдиантус[аыов]?\b': 'диантусов'
}

VARIETY_MAP = {
    r'\bсара бернар\b': 'пион', r'\bкорал шарм\b': 'пион', r'\bкорал сансет\b': 'пион',
    r'\bред наоми\b': 'роза', r'\bпинк флойд\b': 'роза', r'\bэксплорер\b': 'роза',
    r'\bаваланш\b': 'роза', r'\bджумилия\b': 'роза', r'\bванда\b': 'орхидея',
    r'\bцинбидиум\b': 'орхидея', r'\bцимбидиум\b': 'орхидея'
}

COLOR_LEMMAS = {
    'красный', 'белый', 'розовый', 'жёлтый', 'желтый', 'синий', 'голубой',
    'фиолетовый', 'оранжевый', 'бордовый', 'кремовый', 'персиковый',
    'малиновый', 'сиреневый', 'зелёный', 'зеленый', 'чёрный', 'черный',
    'разноцветный', 'радужный', 'пурпурный', 'алый', 'коралловый', 'лавандовый'
}

EXCLUDE_WORDS = {'премиум', 'микс', 'vip', 'см', 'мм', 'км', 'шт', 'штук'}
SHORT_PREPS = {'в', 'с', 'и', 'на', 'а', 'к',
               'о', 'у', 'из', 'за', 'от', 'до', 'по', 'без'}


# --- HEADLESS ПАРСЕР С ПОВТОРНЫМИ ПОПЫТКАМИ ---
def fetch_data_with_playwright(urls):
    print("🚀 Запуск Headless-браузера (Playwright)...")
    products = []
    collections = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        for i, url in enumerate(urls):
            print(f"[{i+1}/{len(urls)}] Обработка: {url}")

            # --- СИСТЕМА ПОВТОРНЫХ ПОПЫТОК (RETRIES) ---
            max_retries = 3
            loaded_successfully = False

            for attempt in range(1, max_retries + 1):
                try:
                    # На первой попытке ждем полной загрузки сети (networkidle).
                    # На остальных - просто ждем, пока прогрузится HTML-каркас страницы.
                    wait_cond = "networkidle" if attempt == 1 else "domcontentloaded"
                    page.goto(url, wait_until=wait_cond, timeout=15000)
                    loaded_successfully = True
                    break  # Успех - выходим из цикла попыток
                except Exception as e:
                    print(
                        f"  [!] Попытка {attempt} не удалась. Пробуем снова...")

            if not loaded_successfully:
                print(f"  [❌] Пропуск ссылки. Страница так и не загрузилась.")
                continue

            # Если страница загрузилась, собираем данные
            try:
                is_collection = url.endswith(
                    "rose") or "all-bouquets" in url or "premium" in url
                title = ""

                # 1. ЗАГОЛОВОК ДЛЯ КОЛЛЕКЦИЙ ИЗ H1
                if is_collection:
                    try:
                        h1_text = page.evaluate(
                            "const h1 = document.querySelector('h1.text-field-data') || document.querySelector('h1'); h1 ? h1.textContent : ''")
                        if h1_text:
                            title = h1_text.strip()
                    except:
                        pass

                # 2. ЗАГОЛОВОК ИЗ OG
                if not title:
                    title = page.evaluate(
                        "document.querySelector('meta[property=\"og:title\"]')?.content || document.title")
                    if title:
                        stop_words = [
                            ' в москве', ' с доставкой', ' купить', ' заказать',
                            ' недорого', ' дешево', ' цена', ' —', ' - ', '|', ' от '
                        ]
                        lower_title = title.lower()
                        for sw in stop_words:
                            idx = lower_title.find(sw)
                            if idx != -1:
                                title = title[:idx]
                                lower_title = lower_title[:idx]
                        title = title.strip()
                    else:
                        title = "Букет"

                # СОХРАНЕНИЕ КОЛЛЕКЦИИ (КАТЕГОРИИ)
                if is_collection:
                    col_id = "col_" + url.strip('/').split('/')[-1]
                    collections[col_id] = {
                        "id": col_id, "name": title, "url": url, "picture": ""
                    }
                    print(f"  [+] Сохранена категория: {title}")
                    continue

                pid = url.strip('/').split('/')[-1]

                # ПАРСИНГ ЦЕНЫ
                price = "0"
                try:
                    price_text = page.locator(
                        '.product-card__actual-price').first.text_content(timeout=3000)
                    if price_text:
                        clean_price = price_text.replace(
                            '\xa0', '').replace('&nbsp;', '').strip()
                        price = re.sub(r'\D', '', clean_price)
                except Exception:
                    print("  [!] Цена не найдена")

                # ПАРСИНГ КАРТИНОК
                images = []
                try:
                    img_locators = page.locator(
                        '.image-slider__wrapper img').all()
                    for img in img_locators:
                        src = img.get_attribute('src')
                        if src:
                            if src.startswith('//'):
                                src = 'https:' + src
                            if src not in images:
                                images.append(src)
                except Exception:
                    pass

                if not images:
                    og_img = page.evaluate(
                        "document.querySelector('meta[property=\"og:image\"]')?.content")
                    if og_img:
                        images.append(og_img)

                # ПАРСИНГ ВЫСОТЫ БУКЕТА
                heights = []
                try:
                    param_blocks = page.locator('.product-card__param').all()
                    for block in param_blocks:
                        p_name = block.locator(
                            '.param__name').first.text_content()
                        if p_name and 'Высота букета' in p_name:
                            val_spans = block.locator(
                                '.param__value-list label span').all()
                            for span in val_spans:
                                val_text = span.text_content().strip()
                                if val_text and 'см' in val_text and val_text not in heights:
                                    heights.append(val_text)
                except Exception:
                    pass

                print(f"  [+] Имя: {title}")
                print(f"  [+] Цена: {price}")

                products.append({
                    "id": pid,
                    "name": title,
                    "price": price,
                    "images": images,
                    "url": url,
                    "heights": heights
                })

            except Exception as e:
                print(f"  [❌] Ошибка при сборе данных: {e}")

        browser.close()

    print(f"\n✅ Сбор данных завершен!\n")
    return products, collections


# --- ФУНКЦИИ NLP ---
def extract_flowers(text):
    found = []
    text_lower = text.lower()
    for pattern, replacement in FLOWER_REGEX_MAP.items():
        if re.search(pattern, text_lower) and replacement not in found:
            found.append(replacement)
    return found


def extract_colors(name):
    words = re.findall(r'[а-яё]+', name.lower())
    found_colors = set()
    for w in words:
        for p in morph.parse(w):
            if p.normal_form in COLOR_LEMMAS:
                found_colors.add(p.normal_form.capitalize())
                break
    return sorted(list(found_colors))


def decline_phrase(num_str, words_part):
    num = int(num_str)
    words_part = re.sub(r'\b(хит|хиты|акция|топ|скидка)\b',
                        '', words_part, flags=re.IGNORECASE)
    words_part = re.sub(r'\s+', ' ', words_part).strip()

    brackets_match = re.search(r'(\(.*?\))', words_part)
    brackets_str = brackets_match.group(1) if brackets_match else ""
    clean_words = re.sub(r'\(.*?\)', '', words_part).split()

    target_number = 'sing' if (num % 10 == 1 and num % 100 != 11) else 'plur'

    main_gender = None
    for w in clean_words:
        if w.isdigit() or w.lower() in EXCLUDE_WORDS or w.lower() in SHORT_PREPS:
            continue
        p = next((p for p in morph.parse(w) if 'NOUN' in p.tag),
                 morph.parse(w)[0])
        if 'NOUN' in p.tag:
            main_gender = p.tag.gender
            break

    result_words = []
    skip_rest = False

    for w in clean_words:
        if skip_rest:
            result_words.append(w)
            continue
        if w.isdigit() or w.lower() in EXCLUDE_WORDS:
            result_words.append(w)
            skip_rest = w.isdigit()
            continue

        parses = morph.parse(w)
        p = parses[0] if w.lower() in SHORT_PREPS else next(
            (p for p in parses if 'NOUN' in p.tag), parses[0])

        if any(tag in p.tag for tag in ['PREP', 'CONJ', 'PRCL', 'INTJ']):
            result_words.append(w)
            skip_rest = True
            continue

        tags_to_apply = {'gent', target_number}
        if target_number == 'sing' and main_gender and any(tag in p.tag for tag in ['ADJF', 'ADJS', 'PRTF']):
            tags_to_apply.add(main_gender)

        inflected = p.inflect(tags_to_apply)
        result_words.append(inflected.word if inflected else w)

    result_phrase = " ".join([num_str] + result_words)
    if brackets_str:
        result_phrase += " " + brackets_str
    return result_phrase.strip()


def check_variety(text, original_name):
    text_lower = text.lower()
    for pattern, flower_base in VARIETY_MAP.items():
        if re.search(pattern, text_lower):
            clean_orig = original_name.replace(
                '"', '').replace("'", "").strip()
            qty_match = re.search(r'\b(\d+)\s*шт\.?\b',
                                  clean_orig, re.IGNORECASE)
            if qty_match:
                qty = qty_match.group(1)
                clean_orig = re.sub(r'\b\d+\s*шт\.?\b', '',
                                    clean_orig, flags=re.IGNORECASE).strip()
                clean_orig = re.sub(r'\s+', ' ', clean_orig).strip()
                declined = decline_phrase(qty, flower_base)
                return f'Букет из {declined} {clean_orig}'.strip()

            inflected = morph.parse(flower_base)[0].inflect({'plur', 'gent'})
            return f'Букет из {inflected.word if inflected else flower_base} {clean_orig}'.strip()
    return None


def process_numeric_bouquet(original_name):
    original_name = original_name.strip()

    for pat in [r'^(.*?)\s*\|\s*(\d+)\s+(.*?)$', r'^(\d+)\s+(.*?)\s*\|\s*(.*?)$']:
        match = re.search(pat, original_name)
        if match:
            art_name = (match.group(1) if pat.startswith(
                '^(.*?)') else match.group(3)).replace('"', '').replace("'", "").strip()
            num_str = match.group(2) if pat.startswith(
                '^(.*?)') else match.group(1)
            words = match.group(3) if pat.startswith(
                '^(.*?)') else match.group(2)
            return f'Букет из {decline_phrase(num_str, words)} {art_name}'.strip()

    qty_end_match = re.search(
        r'^(.*?)\s+(\d+)\s*шт\.?$', original_name, re.IGNORECASE)
    if qty_end_match:
        art_name = qty_end_match.group(1).replace(
            '"', '').replace("'", "").strip()
        num_str = qty_end_match.group(2)
        variety_base = next((b for p, b in VARIETY_MAP.items()
                            if re.search(p, art_name.lower())), None)
        if variety_base:
            return f'Букет из {decline_phrase(num_str, variety_base)} {art_name}'.strip()
        if extract_flowers(art_name):
            return f'Букет из {decline_phrase(num_str, art_name)}'

    match = re.match(r'^(\d+)\s+(.+)$', original_name, re.IGNORECASE)
    if match:
        num_str, words_part = match.group(1), match.group(2)
        has_flower = bool(extract_flowers(words_part))
        variety_base = next((b for p, b in VARIETY_MAP.items()
                            if re.search(p, words_part.lower())), None)

        if not has_flower and not variety_base:
            return None
        if variety_base and not has_flower:
            clean_words = words_part.replace('"', '').replace("'", "").strip()
            return f'Букет из {decline_phrase(num_str, variety_base)} {clean_words}'.strip()

        quote_match = re.search(r'^(.*?)\s*["«](.*?)["»]\s*$', words_part)
        if quote_match:
            clean_quote = quote_match.group(2).replace(
                '"', '').replace("'", "").strip()
            return f'Букет из {decline_phrase(num_str, quote_match.group(1).strip())} {clean_quote}'.strip()

        return f'Букет из {decline_phrase(num_str, words_part)}'

    return None


# --- ОСНОВНОЙ ПРОЦЕСС ГЕНЕРАЦИИ YML ---
def build_yml_feed(products, collections):
    print("⚙️ Обработка NLP и формирование YML фида...")
    root = ET.Element('yml_catalog', date="2026-04-21T14:00:00+00:00")
    shop = ET.SubElement(root, 'shop')
    ET.SubElement(shop, 'name').text = "Аквилегия"
    ET.SubElement(shop, 'company').text = "Аквилегия"
    ET.SubElement(shop, 'url').text = "https://aqvilegia.ru"

    currencies = ET.SubElement(shop, 'currencies')
    ET.SubElement(currencies, 'currency', id="RUB", rate="1")

    categories = ET.SubElement(shop, 'categories')
    ET.SubElement(categories, 'category', id="1").text = "Букеты"

    offers = ET.SubElement(shop, 'offers')

    valid_count = 0
    offer_collections_data = []  # Список для дублирования офферов в коллекции

    for p in products:
        orig_name = p['name']

        # 🔴 ЖЕСТКИЙ ФИЛЬТР
        if not extract_flowers(orig_name) and not any(re.search(pat, orig_name.lower()) for pat in VARIETY_MAP.keys()):
            print(f"   ❌ Пропущен (нет цветов в названии): {orig_name}")
            continue

        # 1. НАЗВАНИЕ
        clean_orig = orig_name.replace('"', '').replace(
            "'", "").replace("«", "").replace("»", "").strip()

        if clean_orig.lower().startswith('букет из'):
            new_name = clean_orig
        else:
            new_name = process_numeric_bouquet(clean_orig)
            if not new_name:
                new_name = check_variety(clean_orig, clean_orig)
            if not new_name:
                if not clean_orig.lower().startswith('букет'):
                    new_name = f'Букет {clean_orig}'
                else:
                    new_name = clean_orig

        # 2. ЦВЕТА
        colors_found = extract_colors(new_name)

        # 4. XML ОФФЕР
        offer = ET.SubElement(
            offers, 'offer', id=str(p['id']), available="true")
        ET.SubElement(offer, 'name').text = new_name
        ET.SubElement(offer, 'url').text = p['url']

        # Запись цен
        ET.SubElement(offer, 'price').text = str(p['price'])
        if str(p['price']).isdigit() and int(p['price']) > 0:
            oldprice_val = int(p['price']) + 300
            ET.SubElement(offer, 'oldprice').text = str(oldprice_val)

        ET.SubElement(offer, 'categoryId').text = "1"
        ET.SubElement(offer, 'currencyId').text = "RUB"

        # Картинки
        for img_url in p['images']:
            ET.SubElement(offer, 'picture').text = img_url

        for color in colors_found:
            ET.SubElement(offer, 'param', name="Цвет").text = color

        for height in p['heights']:
            ET.SubElement(offer, 'param', name="Высота букета").text = height

        # ОПИСАНИЕ ОФФЕРА
        desc_el = ET.SubElement(offer, 'description')
        desc_el.text = f"__CDATA_START__{OFFER_DESCRIPTION}__CDATA_END__"

        ET.SubElement(offer, 'sales_notes').text = COLLECTION_PROMO_TEXT

        # 5. ПРИВЯЗКА К КАТЕГОРИЯМ
        num_match = re.search(r'/(\d+)[a-z]+$', p['url'])
        if num_match:
            qty = num_match.group(1)
            expected_col_id = f"col_{qty}rose"
            if expected_col_id in collections:
                ET.SubElement(offer, 'collectionId').text = expected_col_id

                if not collections[expected_col_id]["picture"] and p['images']:
                    collections[expected_col_id]["picture"] = p['images'][0]

        # Сохраняем для дублирования в коллекции
        offer_collections_data.append({
            'id': str(p['id']),
            'url': p['url'],
            'name': new_name,
            'picture': p['images'][0] if p['images'] else ""
        })

        valid_count += 1

    # --- 6. БЛОК КАТАЛОГОВ (COLLECTIONS) ---
    if collections or offer_collections_data:
        collections_el = ET.SubElement(shop, 'collections')

        # Оригинальные категории
        for col_id, data in collections.items():
            c_el = ET.SubElement(collections_el, 'collection', id=col_id)
            ET.SubElement(c_el, 'url').text = data['url']
            ET.SubElement(c_el, 'name').text = data['name']
            ET.SubElement(c_el, 'description').text = COLLECTION_PROMO_TEXT
            if data['picture']:
                ET.SubElement(c_el, 'picture').text = data['picture']

        # Офферы-дубликаты (без привязки)
        for item in offer_collections_data:
            c_el = ET.SubElement(collections_el, 'collection', id=item['id'])
            ET.SubElement(c_el, 'url').text = item['url']
            ET.SubElement(c_el, 'name').text = item['name']
            ET.SubElement(c_el, 'description').text = COLLECTION_PROMO_TEXT
            if item['picture']:
                ET.SubElement(c_el, 'picture').text = item['picture']

    print("💾 Сохранение файла...")
    rough_string = ET.tostring(root, encoding='utf-8').decode('utf-8')
    rough_string = rough_string.replace('><', '>\n<')

    def unescape_cdata(match):
        text = match.group(1).replace('&amp;', '&').replace(
            '&lt;', '<').replace('&gt;', '>')
        return f"<![CDATA[{text}]]>"

    rough_string = rough_string.replace(
        '__CDATA_START__', '<![CDATA[').replace('__CDATA_END__', ']]>')
    rough_string = re.sub(r'<!\[CDATA\[(.*?)\]\]>',
                          unescape_cdata, rough_string, flags=re.DOTALL)

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write('<?xml version="1.0" encoding="utf-8"?>\n' + rough_string)

    print(f"✅ Готово! Включено товаров: {valid_count}")


if __name__ == "__main__":
    extracted_products, extracted_collections = fetch_data_with_playwright(
        URLS)
    build_yml_feed(extracted_products, extracted_collections)
