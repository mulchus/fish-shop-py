# Бот "Продаём рыбу в Telegram"
## fish-shop-bot

## Установка

[Установите Python](https://www.python.org/), если этого ещё не сделали.

Проверьте, что `python` установлен и корректно настроен.  
Запустите его в командной строке:
```sh
python --version
```

Скачайте код командой  
```shell
git clone https://github.com/mulchus/fish-shop-py.git
```

В каталоге проекта создайте виртуальное окружение:  
```sh
python -m venv venv
```

Активируйте его. На разных операционных системах это делается разными командами:  
- Windows: `.\venv\Scripts\activate`
- MacOS/Linux: `source venv/bin/activate`

Установите зависимости командой   
```shell
pip install -r requirements.txt
```


## Настройки

Часть настроек проекта берётся из переменных окружения. Чтобы их определить, создайте файл `.env` в корне проекта 
и запишите туда данные в таком формате: `ПЕРЕМЕННАЯ=значение`.

Требуемые переменные:
- `TELEGRAM_TOKEN` - токен Вашего бота от Telegram. [Инструкция, как создать бота.](https://core.telegram.org/bots/features#botfather)  
- `DATABASE_PASSWORD=`
- `DATABASE_HOST=localhost`
- `DATABASE_PORT=6379`


## Установка и создание проекта в Stripe

Установите и создайте проект в Stripe согласно [инструкции](https://docs.strapi.io/dev-docs/installation/cli)  
Запустите проект 
```shell
yarn develop
```
В Content-Type Builder создайте сущности и зависимости между ними согласно следующим скриншотам:  
cart
![cart entity](https://github.com/mulchus/fish-shop-py/assets/111083714/7ca15b3d-c13a-4df6-9200-afa5b7a2b81f)

product
![product entity](https://github.com/mulchus/fish-shop-py/assets/111083714/d58b1de2-59a3-443f-b340-4c205fb015c8)

cartproduct
![cartproduct entity](https://github.com/mulchus/fish-shop-py/assets/111083714/e0fe36a9-af78-4ae3-a3fe-53b94aaab2aa)

relations
![cartproduct relations](https://github.com/mulchus/fish-shop-py/assets/111083714/7e1fc30d-90dd-4336-a508-50b85acacf16)
![cartproduct relations 2](https://github.com/mulchus/fish-shop-py/assets/111083714/89c579a7-12b5-4bbe-b204-551b8a2d1fb2)
![cart relations](https://github.com/mulchus/fish-shop-py/assets/111083714/d1f0f987-5deb-48f2-b61a-416de8216dae)


## Установка хранилища Redis

Установите хранилище Redis и проверьте его работу согласно [инструкции](https://redis.io/docs/install/install-redis/)  



## Запуск
Запустите скрипт командой 
```shell
python tg_bot.py
```


## Пример работы бота
![fish-shop-bot](https://github.com/mulchus/fish-shop-py/assets/111083714/f6ca4305-9f4b-4623-967a-f69af9ad3f19)


## Цели проекта

Код написан в учебных целях — это урок в курсе по Python и веб-разработке на сайте [Devman](https://dvmn.org).  
