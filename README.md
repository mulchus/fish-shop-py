# Бот "Продаём рыбу в Telegram"
## fish-shop-bot

## Установка

[Установите Python](https://www.python.org/), если этого ещё не сделали.

Проверьте, что `python` установлен и корректно настроен. Запустите его в командной строке:
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

product

cartproduct

relations


## Установка хранилища Redis

Установите хранилище Redis и проверьте его работу согласно [инструкции](https://redis.io/docs/install/install-redis/)  



## Запуск
Запустите скрипт командой 
```shell
python tg_bot.py
```


## Пример работы бота



## Цели проекта

Код написан в учебных целях — это урок в курсе по Python и веб-разработке на сайте [Devman](https://dvmn.org).  
