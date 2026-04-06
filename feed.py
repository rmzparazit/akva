import requests
import xml.etree.ElementTree as ET
import re
import html
import os

# --- НАСТРОЙКИ ---
FEED_URL = "https://87aced7a-b14f-4cd8-9061-7f500aeeaa32.selstorage.ru/2664700-69bfbefdb664f0-41863077.yml"
OUTPUT_FILE = "aqvilegia_optimized.xml"
UTM_TAGS = "utm_source=yandex&utm_medium=cpc&utm_campaign=smart_banners"

def clean_html(raw_html):
    """Удаляет HTML-теги и расшифровывает спецсимволы"""
    if not raw_html: 
        return ""
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, '', raw_html)
    cleantext = html.unescape(cleantext).strip()
    return cleantext

def indent(elem, level=0):
    """Функция для красивого форматирования XML (отступы и переносы строк)"""
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
        # --- 1. Безопасная обработка URL и UTM ---
        url_el = offer.find('url')
        base_url_for_col = ""
        if url_el is not None and url_el.text:
            original_url = url_el.text.strip()
            base_url_for_col = original_url
            
            # Аккуратно приклеиваем UTM
            if '?' in original_url:
                new_url = f"{original_url}&{UTM_TAGS}"
            else:
                new_url = f"{original_url}?{UTM_TAGS}"
                
            url_el.text = f"__CDATA_START__{new_url}__CDATA_END__"
            
        # --- 2. Чистка Description ---
        desc_el = offer.find('description')
        if desc_el is not None:
            cleaned_text = clean_html(desc_el.text)
            desc_el.text = f"__CDATA_START__{cleaned_text}__CDATA_END__"
            
        # --- 3. Добавление Sales Notes ---
        sales_notes = offer.find('sales_notes')
        if sales_notes is None:
            sales_notes = ET.SubElement(offer, 'sales_notes')
        sales_notes.text = "Бесплатные консультации флористов. Доставка 24/7"
        
        # --- 4. Защита картинок ---
        for pic_el in offer.findall('picture'):
            if pic_el.text and not pic_el.text.startswith('__CDATA'):
                pic_el.text = f"__CDATA_START__{pic_el.text}__CDATA_END__"

        # --- 5. Логика Категорий и Коллекций ---
        cat_elements = offer.findall('categoryId')
        if len(cat_elements) > 0:
            # Оставляем только первый тег как главную физическую категорию
            for extra_cat in cat_elements[1:]:
                cat_id = extra_cat.text
                offer.remove(extra_cat)
                
                col_id = f"col_{cat_id}"
                col_el = ET.SubElement(offer, 'collectionId')
                col_el.text = col_id
                
                if col_id not in collections_data:
                    pic = offer.find('picture')
                    pic_url = pic.text.replace('__CDATA_START__', '').replace('__CDATA_END__', '') if pic is not None else ""
                    
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
            ET.SubElement(c_el, 'url').text = f"__CDATA_START__{data['url']}__CDATA_END__"
            if data['picture']:
                ET.SubElement(c_el, 'picture').text = f"__CDATA_START__{data['picture']}__CDATA_END__"

    print("💾 Форматируем и сохраняем фид...")
    
    # Применяем красивые отступы
    indent(root)
    
    rough_string = ET.tostring(root, encoding='utf-8').decode('utf-8')
    
    # Жестко фиксим CDATA и декодируем амперсанды внутри них
    def unescape_cdata(match):
        text = match.group(1)
        # Возвращаем нормальные амперсанды для UTM-меток
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