import scrapy
import json
from myutils import headers, form_data, shop_id, create_products_list_of_dict, info_props
from pydispatch import dispatcher
from scrapy import signals


def parse_info_props(response):
    """
    Получаем json для расшифровки api
    """
    pattern = 'window.catalogProps = '
    data = response.css('script::text').getall()
    with open(info_props, 'w+', encoding='utf-8') as file:
        for l in data:
            if pattern in l:
                start = l.find('{')
                end = l.find('};')
                result = l[start:end + 1].replace("'", '"')
                file.write(result)


class CatalogSpider(scrapy.Spider):
    custom_settings = {
        'CONCURRENT_REQUESTS': 16,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 16,
        'DOWNLOAD_DELAY': 1,
    }
    name = 'catalog'
    allowed_domains = ['amwine.ru', '.amwine.ru']
    base_url = 'https://amwine.ru'
    api = 'https://amwine.ru/local/components/adinadin/catalog.section.json/ajax_call.php'
    headers = headers
    form_data = form_data
    shop_id = shop_id
    RESULT_LIST = []
    goal = 'viski'  # 'viski' или 'vino'
    goal_dict = {'viski': {'ID': '28',  # params[SECTION_ID] для доступа к определенной категории через api
                           'url': '/krepkie_napitki/viski/'},
                 'vino': {'ID': '16',
                          'url': '/vino/'}}
    url = base_url + '/catalog' + goal_dict[goal]['url']
    form_data['params[SECTION_ID]'] = goal_dict[goal]['ID']

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        dispatcher.connect(self.spider_closed, signals.spider_closed)

    def start_requests(self):
        yield scrapy.Request(url=self.url,
                             headers=self.headers,
                             cookies=self.shop_id,
                             callback=parse_info_props)
        yield scrapy.FormRequest(self.api,
                                 headers=self.headers,
                                 cookies=self.shop_id,
                                 formdata=self.form_data,
                                 callback=self.add_to_form_data_total_count)

    def add_to_form_data_total_count(self, response):
        """
        Делаем запрос к api, возвращает количество товара
        """
        raw_data = response.body
        data = json.loads(raw_data)
        self.form_data['params[PAGE_ELEMENT_COUNT]'] = str(data['productsTotalCount'])
        yield scrapy.FormRequest(self.api,
                                 headers=self.headers,
                                 cookies=self.shop_id,
                                 formdata=self.form_data,
                                 callback=self.parse_product_props)

    def parse_product_props(self, response):
        """
        Повторный запрос к api с максимальным количеством товара
        """
        raw_data = response.body
        data = json.loads(raw_data)
        products_list_of_dict = create_products_list_of_dict(data, self.base_url)
        for product in products_list_of_dict:
            product_url = product['url'] + '#about-drink'
            request = scrapy.Request(url=product_url,
                                     headers=self.headers,
                                     cookies=self.shop_id,
                                     callback=self.parse_description)
            request.meta['product'] = product
            yield request

    def save_to_result_list(self, product, about_wine, requiremets_temp):
        product['metadata']['Рекомендуемая температура подачи'.upper()] = requiremets_temp
        for key, value in about_wine.items():
            key = key.upper()
            if key == 'ОПИСАНИЕ':
                product['metadata']['__description'] = value
            else:
                product['metadata'][key] = value
        self.RESULT_LIST.append(product)
        print(len(self.RESULT_LIST))

    def parse_description(self, response):
        """
        Парсим описание товара
        """
        wine_params = []  # страна, производитель, объем, крепкость и если есть рекомендуемая температура
        first_half_wine_params = response.css('div.about-wine__block_params').css('span.about-wine__param-value').css(
            'a::text').getall()
        for param in first_half_wine_params:
            wine_params.append(param.strip())
        second_half_wine_params = response.css('div.about-wine__block_params').css(
            'span.about-wine__param-value::text').getall()
        for param in second_half_wine_params:
            clear_param = param.strip().replace(' ', '')
            if len(clear_param) > 0:
                wine_params.append(clear_param)
        requiremets_temp = wine_params[-1] if len(wine_params) > 0 and '%' not in wine_params[-1] else None
        about = response.css('div.about-wine-top').css('div.about-wine__block')
        h4 = about.css('div.h4::text').getall()  # заголовок описания(цвет, вкус...)
        p = about.css('p').getall()  # описание
        clear_p = []
        for i in p:
            i = i.replace('\r\n', '').replace('<br>\n', '').replace('""', '').replace('</p>', '').replace('<p>', '')
            clear_p.append(i)
        about_wine = dict(zip(h4, clear_p))
        product = response.meta['product']
        self.save_to_result_list(product, about_wine, requiremets_temp)

    def spider_closed(self):
        en = set()
        for prod in self.RESULT_LIST:
            en.add(prod['RPC'])
        print(len(en))
        with open('parse_result.json', 'w+', encoding='utf-8') as file:
            json.dump(self.RESULT_LIST, file, ensure_ascii=False)
