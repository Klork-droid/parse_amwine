from datetime import datetime
import json

info_props = 'info_props.json'

headers = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
    "accept-language": "ru,en;q=0.9",
    "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
    "sec-ch-ua": "\"Chromium\";v=\"94\", \"Yandex\";v=\"21\", \";Not A Brand\";v=\"99\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "\"Windows\"",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "x-requested-with": "XMLHttpRequest"}
form_data = {'json': 'y',
             'params[IBLOCK_TYPE]': 'catalog',
             'params[IBLOCK_ID]': '2',
             'params[CACHE_TYPE]': 'Y',
             'params[CACHE_TIME]': '3600',
             # 'params[SECTION_ID]': '28',
             'params[PRICE_CODE]': 'MOSCOW',
             'params[NO_INDEX_NO_FOLLOW]': 'Y',
             'current_filter[PROPERTY_STORE][]': 'store',
             # Фильтр наличия товара в магазине, неизвестно откуда страница получает это значение
             # 'current_filter[>CATALOG_STORE_AMOUNT_1391]': '0',
             'params[FILTER_NAME]': 'arrFilterCatalog',
             'current_filter[ACTIVE]': 'Y',
             'current_filter[INCLUDE_SUBSECTIONS]': 'Y'}
shop_id = {'AMWINE__shop_id': '943',
           'IS_ADULT': 'Y'}

dict_for_section = {'igristoe_vino_i_shampanskoe': 'Игристое вино и шампанское',
                    'igristoe_vino': 'Игристое вино',
                    'shampanskoe': 'Шампанское',
                    'bezalkogolnoe_igristoe_vino': 'Безалкогольное игристое вино',
                    'vino': 'Вино',
                    'bezalkogolnoe_vino': 'Безалкогольное вино',
                    'vinnye_napitki': 'Винные напитки',
                    'kagor': 'Кагор',
                    'portveyn': 'Портвейн',
                    'kheres': 'Херес',
                    'krepkie_napitki': 'Крепкие напитки',
                    'rom': 'Ром',
                    'liker': 'Ликер',
                    'dzhin': 'Джин',
                    'tekila_i_meskal': 'Текила',
                    'balzamy_i_nastoyki': 'Бальзамы и настойки',
                    'absent': 'Абсент',
                    'aperetiv': 'Аперитив',
                    'armanyak': 'Арманьяк',
                    'brendi': 'Бренди',
                    'grappa': 'Граппа',
                    'kalvados': 'Кальвадос',
                    'kashasa': 'Кашаса',
                    'samogon': 'Самогон',
                    'chacha': 'Чача',
                    'viski': 'Виски',
                    'konyak': 'Коньяк',
                    'vodka': 'Водка',
                    'pivo': 'Пиво'
                    }


def timestamp():
    dt = datetime.now()
    ts = datetime.timestamp(dt)
    return ts


def create_products_list_of_dict(data, base_url):
    """
    Присваиваем данные полученные с api
    """
    with open(info_props, 'r', encoding='utf-8') as file:
        # info - расшифровка данных с api
        info = json.loads(file.read())
        products_dict = []
        for product in data['products']:
            raw_brand = product['props'].get('brand')
            if product.get('store') and product.get('store') == 'y':
                in_stock = True
            else:
                in_stock = False
            if product['props'].get('old_price_77'):
                original_price = product['props']['old_price_77']
                if product['props'].get('middle_price_77') and original_price > product['props'][
                    'middle_price_77'] != 0:
                    current_price = product['props']['middle_price_77']
                else:
                    current_price = 0
            else:
                current_price = 0
                original_price = 0
            tmp_section = product['link'].split('/')
            section = []
            for i in tmp_section:
                if i in dict_for_section.keys():
                    section.append(dict_for_section[i])
            if product.get('sale'):
                sale = f'Скидка {(original_price / current_price - 1) * 100}%'
            else:
                sale = ''
            try:
                product_dict = {'timestamp': timestamp(),
                                'RPC': str(product['id']),
                                'url': str(base_url + product['link']),
                                'title': str(product['name']),
                                'marketing_tags': ['Товар из коллекции AM', ] if product['props'].get(
                                    'exclusive') else None,
                                'brand': str(info['brand']['values'][str(raw_brand)]['value']) if raw_brand else None,
                                'section': section,
                                'price_data': {
                                    'current': float(current_price),
                                    'original': float(original_price),
                                    'sale_tag': sale},
                                'stock': {'in_stock': in_stock,
                                          'count': int(product['available_quantity'])},
                                'assets': {'main_image': str(base_url + product['preview_picture']),
                                           'set_image': [str(base_url + product['preview_picture']), ],
                                           'view360': [],
                                           'video': []},
                                'metadata': {'__description': None,
                                             'АРТИКУЛ': product['props']['article'] if product['props'].get(
                                                 'article') else None,

                                             },
                                'variants': 1}
            except Exception as e:
                print('Exception', e)
                print(type(e))
                print(product)
            for key in info.keys():
                if product['props'].get(key):
                    if 'type' in key:
                        # значением whisky_type является словарь, достаем ключ без значения
                        for i in product['props'].get(key).keys():
                            raw_key = i
                    else:
                        raw_key = product['props'][key] if type(product['props'][key]) == list else str(
                            product['props'][key])
                    try:
                        if type(raw_key) == list:
                            res = ''
                            for i in raw_key:
                                i = str(i)
                                res = res + info[key]['values'][i]['value'] + ' '
                            product_dict['metadata'][info[key]['NAME'].upper()] = res
                        else:
                            product_dict['metadata'][info[key]['NAME'].upper()] = info[key]['values'][raw_key][
                                'value'] if \
                                info[key]['values'][raw_key]['value'] else None
                    except Exception as e:
                        # встречаются не расшифрованные в javascript значения у виски 11,12
                        print('Exception:', e)
            products_dict.append(product_dict)
    return products_dict
