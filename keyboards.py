from tg_bot import get_database_connection
from shop_functions import get_product
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def get_menu_keyboards(strapi_url):
    db = get_database_connection()
    products = get_product(None, strapi_url)
    keyboard = []
    for product in products:
        keyboard.append([
            InlineKeyboardButton(product['attributes']['title'].split(',', 1)[0], callback_data=product['id']),
        ])
    if db.exists('cart_id'):
        keyboard.append([InlineKeyboardButton('Перейти в корзину', callback_data='cart')])
    return InlineKeyboardMarkup(keyboard, resize_keyboard=True)


def get_product_reply_markup():
    db = get_database_connection()
    keyboard = [
            InlineKeyboardButton('Добавить в корзину', callback_data='add_to_cart'),
            InlineKeyboardButton('В меню', callback_data='menu'),
    ]
    if db.exists('cart_id'):
        keyboard.append(InlineKeyboardButton('Перейти в корзину', callback_data='cart'))
    return InlineKeyboardMarkup([keyboard])
