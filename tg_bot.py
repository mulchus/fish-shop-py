"""
Работает с этими модулями:
python-telegram-bot==13.15
redis==3.2.1
"""
# import os
# import logging
import requests
import redis
import json
from urllib.parse import urljoin
from urllib.parse import unquote

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Filters, Updater, CommandHandler, CallbackQueryHandler, CallbackContext, MessageHandler
from environs import Env
from io import BytesIO

env = Env()
env.read_env()

_database = None

cancel_reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton('В меню', callback_data='menu'),]])

STRAPI_TOKEN = env('STRAPI_TOKEN')


def get_product_reply_markup():
    keyboard = [
            InlineKeyboardButton('Добавить в корзину', callback_data='add_to_cart'),
            InlineKeyboardButton('В меню', callback_data='menu'),
    ]
    db = get_database_connection()
    try:
        db.get('cart_id').decode("utf-8")
        keyboard.append(InlineKeyboardButton('Перейти в корзину', callback_data='cart'))
    except AttributeError:
        pass
    return InlineKeyboardMarkup([keyboard])


def get_product(product_id):
    payload = {
            'populate': 'picture',
        }
    url = 'http://localhost:1337/api/products/'
    if product_id:
        url = urljoin(url, str(product_id))
    response = requests.get(url, params=payload)
    response.raise_for_status()
    return response


def get_menu_keyboards():
    db = get_database_connection()
    try:
        cart_id = db.get('cart_id').decode("utf-8")
    except AttributeError:
        cart_id = None
    products = json.loads(get_product(None).text)['data']
    keyboard = []
    for product in products:
        keyboard.append(
            [
                InlineKeyboardButton(product['attributes']['title'].split(',', 1)[0], callback_data=product['id']),
            ]
        )
    if cart_id:
        keyboard.append([InlineKeyboardButton('Перейти в корзину', callback_data='cart')])
    reply_markup = InlineKeyboardMarkup(keyboard, resize_keyboard=True)
    return reply_markup


def echo(update, context):
    """
    Хэндлер для состояния ECHO.

    Бот отвечает пользователю тем же, что пользователь ему написал.
    Оставляет пользователя в состоянии ECHO.
    """
    users_reply = update.message.text
    update.message.reply_text(users_reply)
    return "ECHO"


def find_cart(chat_id):
    url = 'http://localhost:1337/api/carts'
    payload = {'filters[tg_id][$eq]': str(chat_id)}
    response = requests.get(url, params=payload)
    response.raise_for_status()
    return response


def create_cart(chat_id):
    cart_params = {
        "data": {
            "tg_id": str(chat_id),
        }
    }
    url = 'http://localhost:1337/api/carts'
    headers = {
        'Content-Type': 'application/json'
    }
    response = requests.post(url, headers=headers, json=cart_params)
    response.raise_for_status()
    finded_cart = json.loads(response.text)['data']
    return finded_cart['id']


def add_product_to_cart(cart_id, product_id):
    cartproduct_params = {
        "data": {
            "product": product_id,
            "weight": 1,
            "cart": cart_id,
        }
    }
    url = 'http://localhost:1337/api/cartproducts'
    headers = {'Content-Type': 'application/json'}
    response = requests.post(url, headers=headers, json=cartproduct_params)
    response.raise_for_status()


def start(update: Update, context: CallbackContext):
    db = get_database_connection()
    response = find_cart(update.message.chat_id)
    try:
        cart_id = json.loads(response.text)['data'][0]['id']
        db.set('cart_id', cart_id)
    except IndexError:
        pass
    reply_markup = get_menu_keyboards()
    update.message.reply_text('Выберите продукт:', reply_markup=reply_markup)
    return "HANDLE_MENU"


def handle_menu(update: Update, context: CallbackContext):
    query = update.callback_query
    # query.bot.delete_message(query.from_user.id, query.message.message_id)
    # reply_markup = get_menu_keyboards()
    # query.bot.send_message(query.from_user.id, 'Выберите продукт:', reply_markup=reply_markup)
    if query.data == 'cart':
        return "SHOW_CART"
    db = get_database_connection()
    query.bot.delete_message(query.from_user.id, query.message.message_id)

    db.set('product_selected', query.data)
    response = get_product(int(query.data))
    product = json.loads(response.text)['data']
    image_url = urljoin('http://localhost:1337/',
                        product['attributes']['picture']['data']['attributes']['formats']['small']['url'])
    response = requests.get(image_url)
    response.raise_for_status()
    image_data = BytesIO(response.content)
    # query.bot.delete_message(query.from_user.id, query.message.message_id)
    get_product_reply_markup()
    query.bot.send_photo(
        chat_id=query.from_user.id,
        photo=image_data,
        caption=f"{product['attributes']['title']}, цена {product['attributes']['price']} руб.\n"
                f"Описание: {product['attributes']['description']}",
        reply_markup=get_product_reply_markup(),
    )
    return "HANDLE_DESCRIPTION"


def handle_description(update: Update, context: CallbackContext):
    db = get_database_connection()
    query = update.callback_query
    response = find_cart(query.from_user.id)
    try:
        cart_id = json.loads(response.text)['data'][0]['id']
    except IndexError:
        # и если не находим - создаем корзину
        cart_id = create_cart(query.from_user.id)
    db.set('cart_id', cart_id)

    # создаем объект CartProduct в корзине cart_id
    add_product_to_cart(cart_id, db.get('product_selected').decode("utf-8"))
    reply_markup = get_menu_keyboards()
    query.bot.send_message(
        query.from_user.id,
        'Продукт добавлен. Можете добавить еще один продукт или оформить заказ через корзину.',
        reply_markup=reply_markup)
    return "HANDLE_MENU"


def show_cart(update: Update, context: CallbackContext):
    query = update.callback_query
    query.bot.delete_message(query.from_user.id, query.message.message_id)

    url = urljoin('http://localhost:1337/api/carts/', str(db.get('cart_id').decode("utf-8")))
    payload = {
        'fields[0]': 'tg_id',
        'populate[cartproducts][fields][0]': 'weight',
        'populate[cartproducts][populate][product][fields][0]': 'title',
        'populate[cartproducts][populate][product][fields][1]': 'price',
        'populate[cartproducts][populate][product][fields][2]': 'description',
    }
    response = requests.get(url, params=payload)
    response.raise_for_status()
    cartproducts = json.loads(response.text)['data']['attributes']['cartproducts']['data']
    message = ''
    for num, cartproduct in enumerate(cartproducts):
        message += (f"{num+1}. "
                    f"{cartproduct['attributes']['product']['data']['attributes']['title']}, "
                    f"{cartproduct['attributes']['weight']} кг, "
                    f"на сумму {cartproduct['attributes']['weight'] * cartproduct['attributes']['product']['data']['attributes']['price']} руб. \n")
    query.bot.delete_message(query.from_user.id, query.message.message_id)
    query.bot.send_message(query.from_user.id, message, reply_markup=cancel_reply_markup)
    return "HANDLE_MENU"


def button(update: Update, context: CallbackContext):
    """Parses the CallbackQuery and updates the message text."""
    db = get_database_connection()
    query = update.callback_query
    reply_markup = get_menu_keyboards()
    
    if query.data == 'menu':
    #     query.bot.delete_message(query.from_user.id, query.message.message_id)
    #     query.bot.send_message(query.from_user.id, 'Выберите продукт:', reply_markup=reply_markup)
        return "HANDLE_MENU"
    
    if query.data == 'add_to_cart':
        return "HANDLE_DESCRIPTION"
    #     query.bot.delete_message(query.from_user.id, query.message.message_id)
    #
    #     response = find_cart(query.from_user.id)
    #     try:
    #         cart_id = json.loads(response.text)['data'][0]['id']
    #     except IndexError:
    #         # и если не находим - создаем корзину
    #         cart_id = create_cart(query.from_user.id)
    #     db.set('cart_id', cart_id)
    #
    #     # создаем объект CartProduct в корзине cart_id
    #     add_product_to_cart(cart_id, db.get('product_selected').decode("utf-8"))
    #     reply_markup = get_menu_keyboards()
    #     query.bot.send_message(
    #         query.from_user.id,
    #         'Продукт добавлен. Можете добавить еще один продукт или оформить заказ:',
    #         reply_markup=reply_markup)
    #     return "HANDLE_MENU"
    
    if query.data == 'cart':
    #     url = urljoin('http://localhost:1337/api/carts/', str(db.get('cart_id').decode("utf-8")))
    #     payload = {
    #         'fields[0]': 'tg_id',
    #         'populate[cartproducts][fields][0]': 'weight',
    #         'populate[cartproducts][populate][product][fields][0]': 'title',
    #         'populate[cartproducts][populate][product][fields][1]': 'price',
    #         'populate[cartproducts][populate][product][fields][2]': 'description',
    #     }
    #     response = requests.get(url, params=payload)
    #     response.raise_for_status()
    #     cartproducts = json.loads(response.text)['data']['attributes']['cartproducts']['data']
    #     message = ''
    #     for num, cartproduct in enumerate(cartproducts):
    #         message += (f"{num+1}. "
    #                     f"{cartproduct['attributes']['product']['data']['attributes']['title']}, "
    #                     f"{cartproduct['attributes']['weight']} кг, "
    #                     f"на сумму {cartproduct['attributes']['weight'] * cartproduct['attributes']['product']['data']['attributes']['price']} руб. \n")
    #     query.bot.delete_message(query.from_user.id, query.message.message_id)
    #     query.bot.send_message(query.from_user.id, message, reply_markup=cancel_reply_markup)
        return "SHOW_CART"
        
    # если нажаты другие кнопки...
    # CallbackQueries need to be answered, even if no notification to the user is needed
    # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
    db.set('product_selected', query.data)
    response = get_product(int(query.data))
    product = json.loads(response.text)['data']
    image_url = urljoin('http://localhost:1337/',
                        product['attributes']['picture']['data']['attributes']['formats']['small']['url'])
    response = requests.get(image_url)
    response.raise_for_status()
    image_data = BytesIO(response.content)
    query.bot.delete_message(query.from_user.id, query.message.message_id)
    get_product_reply_markup()
    query.bot.send_photo(
        chat_id=query.from_user.id,
        photo=image_data,
        caption=f"{product['attributes']['title']}, цена {product['attributes']['price']} руб.\n"
                f"Описание: {product['attributes']['description']}",
        reply_markup=get_product_reply_markup(),
    )
    # return "HANDLE_DESCRIPTION"


def help_command(update: Update, context: CallbackContext) -> None:
    """Displays info on how to use the bot."""
    update.message.reply_text("Use /start to test this bot.")
    
    
def handle_users_reply(update, context):
    """
    Функция, которая запускается при любом сообщении от пользователя и решает как его обработать.
    Эта функция запускается в ответ на эти действия пользователя:
        * Нажатие на inline-кнопку в боте
        * Отправка сообщения боту
        * Отправка команды боту
    Она получает стейт пользователя из базы данных и запускает соответствующую функцию-обработчик (хэндлер).
    Функция-обработчик возвращает следующее состояние, которое записывается в базу данных.
    Если пользователь только начал пользоваться ботом, Telegram форсит его написать "/start",
    поэтому по этой фразе выставляется стартовое состояние.
    Если пользователь захочет начать общение с ботом заново, он также может воспользоваться этой командой.
    """
    db = get_database_connection()
    if update.message:
        user_reply = update.message.text
        chat_id = update.message.chat_id
    elif update.callback_query:
        user_reply = update.callback_query.data
        chat_id = update.callback_query.message.chat_id
    else:
        return
    if user_reply == '/start':
        user_state = 'START'
    else:
        user_state = db.get(chat_id).decode("utf-8")
    
    # menu_keyboards = get_menu_keyboards()

    states_functions = {
        'START': start,
        'HANDLE_MENU': handle_menu,
        'HANDLE_DESCRIPTION': handle_description,
        'SHOW_CART': show_cart,
        'ECHO': echo,
    }
    state_handler = states_functions[user_state]
    # Если вы вдруг не заметите, что python-telegram-bot перехватывает ошибки.
    # Оставляю этот try...except, чтобы код не падал молча.
    # Этот фрагмент можно переписать.
    # try:
    next_state = state_handler(update, context)
    print(next_state)
    db.set(chat_id, next_state)
    # except Exception as err:
    #     print(err)


def get_database_connection():
    """
    Возвращает конекшн с базой данных Redis, либо создаёт новый, если он ещё не создан.
    """
    global _database
    if _database is None:
        database_password = env("DATABASE_PASSWORD")
        database_host = env("DATABASE_HOST")
        database_port = env.int("DATABASE_PORT")
        _database = redis.Redis(host=database_host, port=database_port, password=database_password)
    return _database


def main():
    token = env("TELEGRAM_TOKEN")
    updater = Updater(token)
    updater.dispatcher.add_handler(CallbackQueryHandler(handle_users_reply))
    updater.dispatcher.add_handler(MessageHandler(Filters.text, handle_users_reply))
    updater.dispatcher.add_handler(CommandHandler('start', handle_users_reply))

    # Start the Bot
    updater.start_polling()

    # Run the bot until the user presses Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT
    updater.idle()
    

if __name__ == '__main__':
    main()
