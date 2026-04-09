import requests
import xml.etree.ElementTree as ET
import re
import html
import pymorphy3

# --- НАСТРОЙКИ ---
FEED_URL = "https://87aced7a-b14f-4cd8-9061-7f500aeeaa32.selstorage.ru/2664700-69bfbefdb664f0-41863077.yml"
OUTPUT_FILE = "aqvilegia_optimized.xml"
MAX_DESC_LENGTH = 150  

morph = pymorphy3.MorphAnalyzer()

# --- СЛОВАРИ И БАЗЫ ДАННЫХ ---
FLOWER_REGEX_MAP = {
    r'\bроз[аыуе]?\b': 'роз', r'\bпион[аыуов]?\b': 'пионов', r'\bгипсофил[аыуе]?\b': 'гипсофил',
    r'\bхризантем[аыуе]?\b': 'хризантем', r'\bальстромери[яиюей]?\b': 'альстромерий',
    r'\bгвоздик[аиуе]?\b': 'гвоздик', r'\bгеоргин[аыуов]?\b': 'георгин', r'\bкалл[аыуе]?\b': 'калл',
    r'\bлили[яиюей]?\b': 'лилий', r'\bорхиде[яиюей]?\b': 'орхидей', r'\bромаш(?:ка|ки|ку|ке|ек)\b': 'ромашек',
    r'\bтюльпан[аыуов]?\b': 'тюльпанов', r'\bэустом[аыуе]?\b': 'эустом', r'\bматтиол[аыуе]?\b': 'маттиол',
    r'\bгортензи[яиюей]?\b': 'гортензий', r'\bирис[аыуов]?\b': 'ирисов', r'\bгербер[аыуе]?\b': 'гербер',
    r'\bподсолнух[аиов]?\b': 'подсолнухов', r'\bсирен[ьяию]?\b': 'сирени', r'\bранункулюс[аыуов]?\b': 'ранункулюсов',
    r'\bдиантус[аыов]?\b': 'диантусов' # Добавил диантусы на всякий случай
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
SHORT_PREPS = {'в', 'с', 'и', 'на', 'а', 'к', 'о', 'у', 'из', 'за', 'от', 'до', 'по', 'без'}

SELLING_TRIGGERS = [
    "Гарантия свежести 100%!",
    "Порадуйте любимых!",
    "Идеальный подарок на любой праздник.",
    "Эмоции, которые запомнятся надолго.",
    "Собран профессиональными флористами.",
    "Свежие цветы с бережной доставкой."
]

# --- ФУНКЦИИ ОЧИСТКИ ---
def clean_html(raw_html):
    if not raw_html: return ""
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, ' ', raw_html)
    cleantext = html.unescape(cleantext).strip()
    cleantext = re.sub(r'([.!?])([А-ЯЁA-Z])', r'\1 \2', cleantext)
    cleantext = re.sub(r'([а-яёa-z])([А-ЯЁA-Z])', r'\1. \2', cleantext)
    cleantext = re.sub(r'[^\w\s.,!?-]', '', cleantext)
    cleantext = re.sub(r'\s+', ' ', cleantext).strip()
    return cleantext

def get_first_sentence(text):
    match = re.match(r'(.*?[.!?])(?:\s|$)', text)
    if match: return match.group(1).strip()
    return text.strip()

def smart_truncate(text, max_len=MAX_DESC_LENGTH):
    if len(text) <= max_len: 
        return text, False
    truncated = text[:max_len]
    last_boundary = max(truncated.rfind(' '), truncated.rfind(','))
    if last_boundary > 0:
        truncated = truncated[:last_boundary]
    truncated = re.sub(r'\s+[а-яА-ЯёЁa-zA-Z]{1,3}$', '', truncated)
    return truncated.strip(' ,.-'), True

def extract_flowers(text):
    found = []
    text_lower = text.lower()
    for pattern, replacement in FLOWER_REGEX_MAP.items():
        if re.search(pattern, text_lower) and replacement not in found:
            found.append(replacement)
    return found

def extract_colors(name, desc):
    text = f"{name} {desc}".lower()
    words = re.findall(r'[а-яё]+', text)
    found_colors = set()
    for w in words:
        for p in morph.parse(w):
            if p.normal_form in COLOR_LEMMAS:
                found_colors.add(p.normal_form.capitalize())
                break
    return sorted(list(found_colors))

# --- ФУНКЦИИ ГЕНЕРАЦИИ ---
def decline_phrase(num_str, words_part):
    num = int(num_str)
    words_part = re.sub(r'\b(хит|хиты|акция|топ|скидка)\b', '', words_part, flags=re.IGNORECASE)
    words_part = re.sub(r'\s+', ' ', words_part).strip()
    
    brackets_match = re.search(r'(\(.*?\))', words_part)
    brackets_str = brackets_match.group(1) if brackets_match else ""
    clean_words = re.sub(r'\(.*?\)', '', words_part).split()
    
    target_number = 'sing' if (num % 10 == 1 and num % 100 != 11) else 'plur'
    
    main_gender = None
    for w in clean_words:
        if w.isdigit() or w.lower() in EXCLUDE_WORDS or w.lower() in SHORT_PREPS: continue
        parses = morph.parse(w)
        p = next((p for p in parses if 'NOUN' in p.tag), parses[0])
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
        if w.lower() in SHORT_PREPS:
            p = parses[0]
        else:
            p = next((p for p in parses if 'NOUN' in p.tag), parses[0])
        
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
            clean_orig = original_name.replace('"', "'")
            qty_match = re.search(r'\b(\d+)\s*шт\.?\b', clean_orig, re.IGNORECASE)
            if qty_match:
                qty = qty_match.group(1)
                clean_orig = re.sub(r'\b\d+\s*шт\.?\b', '', clean_orig, flags=re.IGNORECASE).strip()
                clean_orig = re.sub(r'\s+', ' ', clean_orig).strip()
                declined = decline_phrase(qty, flower_base)
                return f'Букет из {declined} "{clean_orig}"'
                
            parsed = morph.parse(flower_base)[0]
            inflected = parsed.inflect({'plur', 'gent'})
            plural_genitive = inflected.word if inflected else flower_base
            return f'Букет из {plural_genitive} "{clean_orig}"'
    return None

def extract_composition_from_desc(text, original_name):
    clean_orig = original_name.replace('"', "'")
    hyphen_match = re.search(r'[-—]\s*(\d+)\s+(.*?)(?:[.!?;]|$)', text)
    if hyphen_match:
        num_str = hyphen_match.group(1)
        words_part = hyphen_match.group(2).strip()
        # Проверяем, есть ли там цветы по СТРОГОМУ словарю
        if extract_flowers(words_part):
            declined = decline_phrase(num_str, words_part)
            return f'Букет из {declined} "{clean_orig}"'
            
    pattern = r'(\d+)\s+((?:[а-яА-ЯёЁa-zA-Z\-]+\s+){0,4}[а-яА-ЯёЁ]*(?:\s+(?:с|и|в|без|из)\s+(?:[а-яА-ЯёЁ\-]+\s*){1,4})?)'
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        num_str = match.group(1)
        words_part = match.group(2).strip()
        if extract_flowers(words_part):
            declined = decline_phrase(num_str, words_part)
            return f'Букет из {declined} "{clean_orig}"'
    return None

def process_numeric_bouquet(original_name):
    original_name = original_name.strip()
    pipe_match = re.search(r'^(.*?)\s*\|\s*(\d+)\s+(.*?)$', original_name)
    if pipe_match:
        artistic_name = pipe_match.group(1).replace('"', "'").strip()
        declined_phrase = decline_phrase(pipe_match.group(2), pipe_match.group(3))
        return f'Букет из {declined_phrase} "{artistic_name}"'
        
    pipe_match_rev = re.search(r'^(\d+)\s+(.*?)\s*\|\s*(.*?)$', original_name)
    if pipe_match_rev:
        artistic_name = pipe_match_rev.group(3).replace('"', "'").strip()
        declined_phrase = decline_phrase(pipe_match_rev.group(1), pipe_match_rev.group(2))
        return f'Букет из {declined_phrase} "{artistic_name}"'

    qty_end_match = re.search(r'^(.*?)\s+(\d+)\s*шт\.?$', original_name, re.IGNORECASE)
    if qty_end_match:
        artistic_name = qty_end_match.group(1).replace('"', "'").strip()
        num_str = qty_end_match.group(2)
        variety_base = next((base for pat, base in VARIETY_MAP.items() if re.search(pat, artistic_name.lower())), None)
        if variety_base:
            declined = decline_phrase(num_str, variety_base)
            return f'Букет из {declined} "{artistic_name}"'
        else:
            if extract_flowers(artistic_name):
                declined = decline_phrase(num_str, artistic_name)
                return f'Букет из {declined}'

    match = re.match(r'^(\d+)\s+(.+)$', original_name, re.IGNORECASE)
    if match:
        num_str = match.group(1)
        words_part = match.group(2)
        
        has_flower = bool(extract_flowers(words_part))
        variety_base = next((base for pat, base in VARIETY_MAP.items() if re.search(pat, words_part.lower())), None)
        
        if not has_flower and not variety_base:
            return None 
            
        if variety_base and not has_flower:
            declined = decline_phrase(num_str, variety_base)
            clean_artistic = words_part.replace('"', "'").strip()
            return f'Букет из {declined} "{clean_artistic}"'
            
        quote_match = re.search(r'^(.*?)\s*["«](.*?)["»]\s*$', words_part)
        if quote_match:
            declined_phrase = decline_phrase(num_str, quote_match.group(1).strip())
            return f'Букет из {declined_phrase} "{quote_match.group(2).strip()}"'
            
        declined_phrase = decline_phrase(num_str, words_part)
        return f'Букет из {declined_phrase}'

    return None

def generate_selling_description(offer_id, composition, original_desc, colors):
    numeric_id = int(re.sub(r'\D', '', str(offer_id)) or 0)
    trigger = SELLING_TRIGGERS[numeric_id % len(SELLING_TRIGGERS)]
    
    if composition:
        color_prefix = f"{'-'.join([c.lower() for c in colors])} " if 0 < len(colors) <= 2 else ""
        template = f"Роскошный {color_prefix}букет из {composition}. {trigger}"
        if len(template) <= MAX_DESC_LENGTH:
            return template

    safe_length = MAX_DESC_LENGTH - len(trigger) - 4
    short_orig, is_truncated = smart_truncate(original_desc, max_len=safe_length)
    
    if not short_orig:
        return trigger
        
    if is_truncated:
        return f"{short_orig}... {trigger}"
    else:
        return f"{short_orig.rstrip('. ')}. {trigger}"

def indent(elem, level=0):
    i = "\n" + level * "  "
    if len(elem):
        if not elem.text or not elem.text.strip(): elem.text = i + "  "
        if not elem.tail or not elem.tail.strip(): elem.tail = i
        for elem in elem: indent(elem, level + 1)
        if not elem.tail or not elem.tail.strip(): elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()): elem.tail = i

# --- ОСНОВНОЙ ПАРСЕР ---
def process_feed():
    print("📥 Скачиваем оригинальный фид...")
    response = requests.get(FEED_URL)
    response.raise_for_status()
    
    print("⚙️ Парсим и оптимизируем XML...")
    root = ET.fromstring(response.content)
    shop = root.find('shop')
    
    categories_dict = {cat.get('id'): cat.text for cat in shop.find('categories').findall('category')}
    collections_data = {} 
    offers = shop.find('offers')
    
    for offer in offers.findall('offer'):
        name_el = offer.find('name')
        original_name = name_el.text if name_el is not None else ""
        
        desc_el = offer.find('description')
        full_desc_clean = clean_html(desc_el.text) if desc_el is not None else ""
        
        search_context = f"{original_name} {full_desc_clean}"
        
        # --- 🔴 ЖЕСТКИЙ ФИЛЬТР С ИСПОЛЬЗОВАНИЕМ СТРОГОГО СЛОВАРЯ ---
        # Теперь ищет цветы только как существительные с соблюдением границ слов
        found_flowers = extract_flowers(search_context)
        has_variety = any(re.search(pat, search_context.lower()) for pat in VARIETY_MAP.keys())
        
        if not found_flowers and not has_variety:
            # Полностью удаляем оффер, если в нем нет цветов
            offers.remove(offer)
            continue
            
        # --- 1. URL ---
        url_el = offer.find('url')
        base_url_for_col = ""
        if url_el is not None and url_el.text:
            base_url_for_col = url_el.text.strip()
            url_el.text = base_url_for_col
            
        first_sentence = get_first_sentence(full_desc_clean)
        
        # --- 2. ГЕНЕРАЦИЯ УМНОГО НАЗВАНИЯ ---
        new_name = process_numeric_bouquet(original_name)
        if not new_name and full_desc_clean:
            new_name = extract_composition_from_desc(first_sentence, original_name)
        if not new_name:
            new_name = check_variety(search_context, original_name)
        if not new_name:
            # Ищем цветы ВО ВСЕМ ОПИСАНИИ, а не только в первом предложении
            name_has_flowers = bool(extract_flowers(original_name))
            if not name_has_flowers and full_desc_clean:
                found_in_desc = extract_flowers(full_desc_clean)
                if found_in_desc:
                    joined = found_in_desc[0] if len(found_in_desc) == 1 else ", ".join(found_in_desc[:-1]) + " и " + found_in_desc[-1]
                    clean_orig = original_name.replace('"', "'")
                    new_name = f'Букет из {joined} "{clean_orig}"'
                    
        if not new_name:
            if not original_name.lower().startswith('букет'):
                clean_orig = original_name.replace('"', "'")
                new_name = f'Букет "{clean_orig}"'
            else:
                new_name = original_name
                    
        final_name = new_name if new_name else original_name
        if name_el is not None:
            name_el.text = final_name
            
        # --- 3. ИЗВЛЕЧЕНИЕ ПАРАМЕТРОВ (ЦВЕТА) ---
        short_desc, _ = smart_truncate(first_sentence)
        all_params = []
        for p_elem in offer.findall('param'):
            all_params.append(p_elem)
            offer.remove(p_elem)
            
        colors_found = extract_colors(final_name, short_desc)
        for color in colors_found:
            color_param = ET.Element('param', name="Цвет")
            color_param.text = color
            all_params.append(color_param)
            
        for p_elem in all_params:
            offer.append(p_elem)

        # --- 4. ПРОДАЮЩЕЕ ОПИСАНИЕ ---
        composition_only = ""
        if new_name and "Букет из" in new_name:
            comp_match = re.search(r'Букет из (.*?) (?:["«]|$)', new_name)
            if comp_match:
                composition_only = comp_match.group(1).strip()

        selling_desc = generate_selling_description(
            offer_id=offer.get('id'), 
            composition=composition_only, 
            original_desc=first_sentence, 
            colors=colors_found
        )
        
        if desc_el is not None:
            desc_el.text = f"__CDATA_START__{selling_desc}__CDATA_END__"
            
        # --- 5. SALES NOTES ---
        sales_notes = offer.find('sales_notes')
        if sales_notes is None: 
            sales_notes = ET.Element('sales_notes')
            offer.append(sales_notes)
        sales_notes.text = "Бесплатные консультации флористов. Доставка 24/7"
        
        # --- 6. КАРТИНКИ И КОЛЛЕКЦИИ ---
        for pic_el in offer.findall('picture'):
            if pic_el.text:
                pic_el.text = pic_el.text.replace('__CDATA_START__', '').replace('__CDATA_END__', '')

        cat_elements = offer.findall('categoryId')
        if len(cat_elements) > 0:
            for extra_cat in cat_elements[1:]:
                cat_id = extra_cat.text
                offer.remove(extra_cat)
                col_id = f"col_{cat_id}"
                
                col_el = ET.Element('collectionId')
                col_el.text = col_id
                offer.append(col_el)
                
                if col_id not in collections_data:
                    pic = offer.find('picture')
                    collections_data[col_id] = {
                        "name": categories_dict.get(cat_id, "Коллекция"),
                        "picture": pic.text if pic is not None else "",
                        "url": base_url_for_col 
                    }

    if collections_data:
        collections_el = ET.SubElement(shop, 'collections')
        for col_id, data in collections_data.items():
            c_el = ET.SubElement(collections_el, 'collection', id=col_id)
            ET.SubElement(c_el, 'name').text = data['name']
            ET.SubElement(c_el, 'url').text = data['url']
            if data['picture']: ET.SubElement(c_el, 'picture').text = data['picture']

    print("💾 Форматируем и сохраняем фид...")
    indent(root)
    rough_string = ET.tostring(root, encoding='utf-8').decode('utf-8')
    
    def unescape_cdata(match):
        text = match.group(1).replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        return f"<![CDATA[{text}]]>"

    rough_string = rough_string.replace('__CDATA_START__', '<![CDATA[').replace('__CDATA_END__', ']]>')
    rough_string = re.sub(r'<!\[CDATA\[(.*?)\]\]>', unescape_cdata, rough_string, flags=re.DOTALL)
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write('<?xml version="1.0" encoding="utf-8"?>\n' + rough_string)
        
    print(f"✅ Успех! Чистый и продающий смарт-фид сохранен в {OUTPUT_FILE}")

if __name__ == "__main__":
    process_feed()
