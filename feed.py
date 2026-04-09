import requests
import xml.etree.ElementTree as ET
import re
import html
import os

# --- НАСТРОЙКИ ---
FEED_URL = "https://87aced7a-b14f-4cd8-9061-7f500aeeaa32.selstorage.ru/2664700-69bfbefdb664f0-41863077.yml"
OUTPUT_FILE = "aqvilegia_optimized.xml"

def clean_html_and_get_first_sentence(raw_html):
    """Удаляет HTML-теги и забирает только первое предложение"""
    if not raw_html: 
        return ""
    
    # 1. Очищаем от HTML
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, '', raw_html)
    cleantext = html.unescape(cleantext).strip()
    
    # 2. Опционально: чистим эмодзи, если они мешают (оставляем только текст)
    # Если эмодзи нужны - эту строку можно закомментировать
    cleantext = re.sub(r'[^\w\s.,!?-]', '', cleantext)

    # 3. Вытаскиваем первое предложение (до первой точки, ! или ?)
    match = re.match(r'(.*?[.!?])(?:\s|$)', cleantext)
    if match:
        first_sentence = match.group(1).strip()
    else:
        # Если знаков препинания нет вообще, берем текст целиком
        first_sentence = cleantext.strip()
        
    return first_sentence

def indent(elem, level=0):
    """Функция для красивого форматирования XML (отступы и переносы)"""
    i = "\n" + level * "  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indent(elem, level + 1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i

def process_feed():
    print("📥 Скачиваем оригинальный фид...")
    response = requests.get(FEED_URL)
    response.raise_for_status()
    
    print("⚙️ Парсим и оптимизируем XML...")
    root = ET.fromstring(response.content)
    shop = root.find('shop')
    
    categories_dict = {}
    for cat in shop.find('categories').findall('category'):
        categories_dict[cat.get('id')] = cat.text

    collections_data = {} 
    offers = shop.find('offers')
    
    for offer in offers.findall('offer'):
        
        # --- 1. URL (Без UTM и без CDATA) ---
        url_el = offer.find('url')
        base_url_for_col = ""
        if url_el is not None and url_el.text:
            original_url = url_el.text.strip()
            base_url_for_col = original_url
            # Оставляем чистую ссылку. ElementTree сам превратит & в &amp; при сохранении
            url_el.text = original_url
            
        # --- 2. Description (Первое предложение + CDATA) ---
        desc_el = offer.find('description')
        if desc_el is not None:
            first_sentence = clean_html_and_get_first_sentence(desc_el.text)
            desc_el.text = f"__CDATA_START__{first_sentence}__CDATA_END__"
            
        # --- 3. Добавление Sales Notes ---
        sales_notes = offer.find('sales_notes')
        if sales_notes is None:
            sales_notes = ET.SubElement(offer, 'sales_notes')
        sales_notes.text = "Бесплатные консультации флористов. Доставка 24/7"
        
        # --- 4. Картинки (Без CDATA) ---
        for pic_el in offer.findall('picture'):
            if pic_el.text:
                # Очищаем от возможных старых заглушек, просто сохраняем чистую ссылку
                clean_pic = pic_el.text.replace('__CDATA_START__', '').replace('__CDATA_END__', '')
                pic_el.text = clean_pic

        # --- 5. Логика Категорий и Коллекций ---
        cat_elements = offer.findall('categoryId')
        if len(cat_elements) > 0:
            # Оставляем только первую (главную) категорию
            for extra_cat in cat_elements[1:]:
                cat_id = extra_cat.text
                offer.remove(extra_cat)
                
                col_id = f"col_{cat_id}"
                col_el = ET.SubElement(offer, 'collectionId')
                col_el.text = col_id
                
                if col_id not in collections_data:
                    pic = offer.find('picture')
                    pic_url = pic.text if pic is not None else ""
                    
                    collections_data[col_id] = {
                        "name": categories_dict.get(cat_id, "Коллекция"),
                        "picture": pic_url,
                        "url": base_url_for_col 
                    }

    # Создаем блок <collections> в самом низу
    if collections_data:
        collections_el = ET.SubElement(shop, 'collections')
        for col_id, data in collections_data.items():
            c_el = ET.SubElement(collections_el, 'collection', id=col_id)
            ET.SubElement(c_el, 'name').text = data['name']
            
            # В коллекциях URL и Картинка тоже идут без CDATA
            ET.SubElement(c_el, 'url').text = data['url']
            if data['picture']:
                ET.SubElement(c_el, 'picture').text = data['picture']

    print("💾 Форматируем и сохраняем фид...")
    
    # Применяем красивые отступы
    indent(root)
    
    rough_string = ET.tostring(root, encoding='utf-8').decode('utf-8')
    
    # Жестко фиксим CDATA (только те, что мы добавили в description)
    def unescape_cdata(match):
        text = match.group(1)
        # Внутри CDATA амперсанды не должны быть заэкранированы
        text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        return f"<![CDATA[{text}]]>"

    rough_string = rough_string.replace('__CDATA_START__', '<![CDATA[')
    rough_string = rough_string.replace('__CDATA_END__', ']]>')
    rough_string = re.sub(r'<!\[CDATA\[(.*?)\]\]>', unescape_cdata, rough_string, flags=re.DOTALL)
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write('<?xml version="1.0" encoding="utf-8"?>\n' + rough_string)
        
    print(f"✅ Успех! Идеальный фид сохранен в {OUTPUT_FILE}")

if __name__ == "__main__":
    process_feed()
