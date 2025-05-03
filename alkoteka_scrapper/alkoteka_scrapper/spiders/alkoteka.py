import scrapy
from datetime import datetime
from scrapy import Request
import json
import random

class AlkotekaSpider(scrapy.Spider):
    name = 'alkoteka'  # Имя нашего паука, чтобы запускать его через scrapy crawl
    allowed_domains = ['alkoteka.com']  # Ограничиваем парсинг только этим доменом
    custom_settings = {
        'DOWNLOAD_DELAY': random.uniform(1, 3),  # Задержка между запросами от 1 до 3 секунд, чтобы не нагружать сайт
        'RANDOMIZE_DOWNLOAD_DELAY': True,  # Делаем задержку случайной, чтобы быть похожими на человека
        'DOWNLOADER_MIDDLEWARES': {
            'alkoteka_scrapper.middlewares.AlkotekaScrapperDownloaderMiddleware': 543,  # Подключаем middleware для обработки запросов
        },
    }

    # Список категорий для парсинга (3 категории: бренди, вино, виски)
    START_URLS = [
        {
            "url": "https://alkoteka.com/web-api/v1/product?city_uuid=4a70f9e0-46ae-11e7-83ff-00155d026416&options%5Bcategories%5D[]=konyak-brendi&page=1&per_page=20&root_category_slug=krepkiy-alkogol",
            "category": "brandy"
        },
        {
            "url": "https://alkoteka.com/web-api/v1/product?city_uuid=4a70f9e0-46ae-11e7-83ff-00155d026416&page=1&per_page=20&root_category_slug=vino",
            "category": "vino"
        },
        {
            "url": "https://alkoteka.com/web-api/v1/product?city_uuid=4a70f9e0-46ae-11e7-83ff-00155d026416&options%5Bcategories%5D[]=viski&page=1&per_page=20&root_category_slug=krepkiy-alkogol",
            "category": "whiskey"
        }
    ]

    # Базовый URL для API и ID города Краснодар
    BASE_API_URL = "https://alkoteka.com/web-api/v1/product"
    CITY_UUID = "4a70f9e0-46ae-11e7-83ff-00155d026416"

    def start_requests(self):
        # Запускаем парсинг для каждой категории из списка
        for api_entry in self.START_URLS:
            yield Request(
                url=api_entry["url"],
                callback=self.parse_api,
                meta={'category': api_entry["category"], 'page': 1},
                dont_filter=True
            )

    def parse_api(self, response):
        """Если запрос не прошёл (не 200), просто выходим"""
        if response.status != 200:
            self.logger.error(f"Ошибка {response.status} при запросе {response.url}")
            return

        # Разбираем JSON-ответ
        try:
            data = response.json()
            if not isinstance(data, dict):
                self.logger.error(f"Ожидали словарь, а получили: {type(data)}")
                return
            products = data.get("results", [])
            if not isinstance(products, list):
                self.logger.error(f"Ожидали список товаров, а получили: {type(products)}")
                return
        except json.JSONDecodeError:
            self.logger.error(f"Не удалось разобрать JSON для {response.url}")
            return

        category = response.meta['category']
        page = response.meta['page']
        section = [category.replace("-", " ").capitalize()]  # Формируем раздел из категории

        # Если товаров нет, выходим
        if not products or len(products) == 0:
            return

        # Обрабатываем каждый товар
        for product in products:
            timestamp = int(datetime.utcnow().timestamp())

            product_url = product.get("product_url", "")
            title = product.get("name", "")
            volume = next((label["title"] for label in product.get("filter_labels", []) if label["filter"] == "obem"), "")
            if volume and volume not in title:
                title = f"{title} {volume}".replace("-", " ")

            # Собираем метаданные товара
            metadata = {
                "__description": product.get("description", ""),
                "Объем": volume,
                "Страна": product.get("country", "Не указано"),
                "Код товара": str(product.get("vendor_code", "")),
            }
            for label in product.get("filter_labels", []):
                if label["filter"] != "obem":
                    metadata[label["filter"].capitalize()] = label["title"]

            # Обрабатываем цену и скидку
            current_price = float(product.get("price", 0.0))
            original_price = float(product.get("prev_price", current_price))
            sale_tag = ""
            if original_price > current_price > 0:
                discount_percentage = ((original_price - current_price) / original_price) * 100
                sale_tag = f"Скидка {int(discount_percentage)}%"

            main_image = product.get("image_url", "")
            set_images = []  # Дополнительных изображений нет, оставляем пустым

            in_stock = product.get("available", False)
            stock_count = product.get("quantity_total", 0)

            marketing_tags = [label["title"] for label in product.get("action_labels", [])]

            # Формируем итоговые данные для товара
            yield {
                "timestamp": timestamp,
                "RPC": product.get("uuid", ""),
                "url": product_url,
                "title": title,
                "marketing_tags": marketing_tags,
                "brand": product.get("brand", "Не указано"),
                "section": section,
                "price_data": {
                    "current": current_price,
                    "original": original_price,
                    "sale_tag": sale_tag
                },
                "stock": {
                    "in_stock": in_stock,
                    "count": stock_count
                },
                "assets": {
                    "main_image": main_image,
                    "set_images": set_images,
                    "view360": [],
                    "video": []
                },
                "metadata": metadata,
                "variants": 1
            }

        # Переходим к следующей странице (пагинация)
        next_page = page + 1
        if category == "vino":
            api_url = f"{self.BASE_API_URL}?city_uuid={self.CITY_UUID}&page={next_page}&per_page=20&root_category_slug={category}"
        elif category == "whiskey":
            api_url = f"{self.BASE_API_URL}?city_uuid={self.CITY_UUID}&options%5Bcategories%5D%5B%5D=viski&page={next_page}&per_page=20&root_category_slug=krepkiy-alkogol"
        elif category == "brandy":
            api_url = f"{self.BASE_API_URL}?city_uuid={self.CITY_UUID}&options%5Bcategories%5D%5B%5D=konyak-brendi&page={next_page}&per_page=20&root_category_slug=krepkiy-alkogol"
        else:
            return

        yield Request(
            url=api_url,
            callback=self.parse_api,
            meta={'category': category, 'page': next_page},
            dont_filter=True
        )
