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

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Filters, Updater, CommandHandler, CallbackQueryHandler, CallbackContext, MessageHandler
from environs import Env
from io import BytesIO

env = Env()
env.read_env()

_database = None

cancel_reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton('назад', callback_data='cancel'),]])


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


def start(update: Update, context: CallbackContext, reply_markup):
    update.message.reply_text('Выберите продукт:', reply_markup=reply_markup)
    return "HANDLE_MENU"


def echo(update, context):
    """
    Хэндлер для состояния ECHO.

    Бот отвечает пользователю тем же, что пользователь ему написал.
    Оставляет пользователя в состоянии ECHO.
    """
    users_reply = update.message.text
    update.message.reply_text(users_reply)
    return "ECHO"


def button(update: Update, context: CallbackContext):
    """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query
    # CallbackQueries need to be answered, even if no notification to the user is needed
    # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
    response = get_product(int(query.data))
    product = json.loads(response.text)['data']
    image_url = urljoin('http://localhost:1337/',
                        product['attributes']['picture']['data']['attributes']['formats']['small']['url'])
    response = requests.get(image_url)
    response.raise_for_status()
    image_data = BytesIO(response.content)
    query.bot.delete_message(query.from_user.id, query.message.message_id)
    query.bot.send_photo(
        chat_id=query.from_user.id,
        photo=image_data,
        caption=f"{product['attributes']['title']}, цена {product['attributes']['price']} руб.\n"
                f"Описание: {product['attributes']['description']}",
    )
    return "START"


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

    states_functions = {
        'START': start,
        'HANDLE_MENU': handle_menu,
        'ECHO': echo,
    }
    state_handler = states_functions[user_state]
    # Если вы вдруг не заметите, что python-telegram-bot перехватывает ошибки.
    # Оставляю этот try...except, чтобы код не падал молча.
    # Этот фрагмент можно переписать.
    try:
        next_state = state_handler(update, context)
        db.set(chat_id, next_state)
    except Exception as err:
        print(err)


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
    
    products = json.loads(get_product(None).text)['data']
    
    updater = Updater(token)
    keyboard = []
    for product in products:
        keyboard.append(
            [
                InlineKeyboardButton(product['attributes']['title'].split(',', 1)[0], callback_data=product['id']),
            ]
        )
        reply_markup = InlineKeyboardMarkup(keyboard, resize_keyboard=True)
    
    updater.dispatcher.add_handler(CommandHandler('start', lambda bot, update: start(bot, update, reply_markup)))
    updater.dispatcher.add_handler(CallbackQueryHandler(button))
    updater.dispatcher.add_handler(CommandHandler('help', help_command))
    
    updater.dispatcher.add_handler(MessageHandler(Filters.text, handle_users_reply))
    # updater.dispatcher.add_handler(CallbackQueryHandler(handle_users_reply))
    # updater.dispatcher.add_handler(CommandHandler('start', handle_users_reply))

    # Start the Bot
    updater.start_polling()

    # Run the bot until the user presses Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT
    updater.idle()
    

if __name__ == '__main__':
    main()