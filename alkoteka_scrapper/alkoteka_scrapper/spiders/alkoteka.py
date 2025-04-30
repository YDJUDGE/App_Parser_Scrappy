from datetime import datetime
from typing import Iterable
import scrapy
from scrapy import Request
from urllib.parse import urljoin


class AlkotekaSpider(scrapy.Spider):
    name = "alkoteka"
    allowed_domains = ["alkoteka.com"]
    start_urls = [
        "https://alkoteka.com",
        "https://alkoteka.com/catalog/vino",
        "https://alkoteka.com/catalog/krepkiy-alkogol/options-categories_viski"]  # Минимум 3

    custom_settings = {
        'DOWNLOADED_MIDDLEWARES': {
            'scrapy.downloadermiddlewares.httpproxy.HttpProxyMiddleware': 110,
        },
        'DOWNLOAD_ONLY': 1   # Задержка, для избежания блокировки
    }

    def start_requests(self) -> Iterable[Request]:
        # Через куки устанвливаем регион Краснодар
        for url in self.start_urls:
            yield scrapy.Request(
                url=url,
                cookies={'region': 'krasnodar'},
                callback=self.parse,
            )

    def parse(self, response):
        products = response.css('div.card-product')
        for product in products:
            price_data = product.css('span.text--button-price span::text').get()
            original_price = float(price_data.replace(' ', '').replace('₽', '')) if price_data else 0.0
            sale_price = product.css('span.text--button-price--old span::text').get()
            sale_price = float(sale_price.replace(' ', '').replace('₽', '')) if sale_price else original_price

            # Извлекаем теги скидок
            sale_tag = product.css('div.label--discount::text').get()
            sale_tag = sale_tag.strip() if sale_tag else "Нет тэга скидок"

            # Извлекаем изображения
            images = product.css('div.card-product__img-wrap img::attr(src)').getall()
            images = [urljoin(response.url, img) for img in images]

            # Извлекаем метаданные(характеристики)
            matadata = {}
            characteristics = product.css('div.product-card__features p')
            for char in characteristics:
                key = char.css('span.feature-name::text').get()
                value = char.css('span.feature-value::text').get()
                if key and value:
                    matadata[key.strip()] = value.strip()

            yield {
                'timestamp': int(datetime.now().timestamp()),
                'RPC': product.css('div.card-product::attr(data-product-id)').get(default=""),
                'url': urljoin(response.url, product.css('a::attr(href)').get(default="")),
                'title': product.css('span.title.text--black::text').get(default="").strip(),
                'marketing_tags': product.css('div.label--popular::text').getall(),
                'brand': product.css('div.card-product__brand::text').get(default="").strip(),
                'section': response.css('div.breadcrumbs a::text').getall(),
                'price_data': {
                    'current': sale_price,
                    'original': original_price,
                    'sale_tag': sale_tag,
                },
                'stock': {
                    'in_stock': "в наличии" in product.css('div.card-product__availability::text').get(default="").lower(),
                    'count': 50  # На сайте нет точного количсетва, поэтому использую значение по умолчанию
                },
                'assets': {
                    'main_image': images[0] if images else "Нет фото",
                    'set_images': images,
                    'view360': [],
                },
                'metadata': matadata,
                'variants': 1  # Я не увидел разных вариантов
            }

        # Пагинация
        next_page = response.css('a.pagination__next::attr(href)').get()
        if next_page:
            yield response.follow(
                next_page,
                callback=self.parse,
                cookies={'region': 'krasnodar'},
            )
