# Парсер для Alkoteka.com

   Этот проект — парсер для интернет-магазина Alkoteka.com, написанный на Scrapy. Он собирает данные о товарах из трёх категорий (бренди, вино, виски) с учётом региона Краснодар.
   1. Установите зависимости:
      ```bash
      pip install -r requirements.txt
      ```
   2. Запустите парсер:
      ```bash
      scrapy crawl alkoteka -O result.json
      ```
   3. Результат будет в файле `result.json`.

   ## Структура проекта
   - `alkoteka_scrapper/spiders/alkoteka_spider.py`: Основной код спайдера.
   - `alkoteka_scrapper/middlewares.py`: Middleware для смены User-Agent.
   - `requirements.txt`: Список зависимостей.
   - `result.json`: Выходной файл с данными.

   ## Особенности
   - Собирает данные с учётом региона Краснодар.
   - Использует middleware для смены User-Agent.
   - Поддерживает пагинацию для сбора всех товаров из категории.