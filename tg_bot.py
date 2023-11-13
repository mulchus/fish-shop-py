"""
Работает с этими модулями:
python-telegram-bot==13.15
redis==3.2.1
"""
import requests
import redis
import json
import time
import keyboards
import functions

from urllib.parse import urljoin


from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Filters, Updater, CommandHandler, CallbackQueryHandler, CallbackContext, MessageHandler
from environs import Env
from io import BytesIO


_database = None
_strapi_url = ''


def start(update: Update, context: CallbackContext):
    db = get_database_connection()
    response = functions.find_cart(update.message.chat_id, _strapi_url)
    try:
        cart_id = response.json()['data'][0]['id']
        db.set('cart_id', cart_id)
    finally:
        update.message.reply_text('Выберите продукт:', reply_markup=keyboards.get_menu_keyboards(_strapi_url))
        return "HANDLE_MENU"


def show_menu(update: Update, context: CallbackContext):
    if update.message:
        update_type = update.message
        chat_id = update.message.chat_id
        update_type.bot.delete_message(chat_id, update_type.message_id)
        update_type.bot.delete_message(chat_id, update_type.message_id-1)
        update_type.bot.delete_message(chat_id, update_type.message_id-2)
    elif update.callback_query:
        update_type = update.callback_query
        chat_id = update.callback_query.message.chat_id
        update_type.bot.delete_message(chat_id, update_type.message.message_id)
    else:
        return "HANDLE_MENU"
    reply_markup = keyboards.get_menu_keyboards(_strapi_url)
    update_type.bot.send_message(chat_id, 'Выберите продукт:', reply_markup=reply_markup)
    return "HANDLE_MENU"


def handle_menu(update: Update, context: CallbackContext):
    global _strapi_url
    db = get_database_connection()
    query = update.callback_query

    if query.data == 'cart':
        return show_cart(update, context)
    
    query.bot.delete_message(query.from_user.id, query.message.message_id)
    db.set('product_selected', query.data)
    response = functions.get_product(int(query.data), _strapi_url)
    product = response.json()['data']
    image_url = urljoin(_strapi_url,
                        product['attributes']['picture']['data']['attributes']['formats']['small']['url'])
    response = requests.get(image_url)
    response.raise_for_status()
    image_data = BytesIO(response.content)
    query.bot.send_photo(
        chat_id=query.from_user.id,
        photo=image_data,
        caption=f"{product['attributes']['title']}, цена {product['attributes']['price']} руб.\n"
                f"Описание: {product['attributes']['description']}",
        reply_markup=keyboards.get_product_reply_markup(),
    )
    return "HANDLE_DESCRIPTION"


def handle_description(update: Update, context: CallbackContext):
    db = get_database_connection()
    query = update.callback_query
    
    if query.data == 'menu':
        return show_menu(update, context)
    
    if query.data == 'cart':
        return show_cart(update, context)
    
    query.bot.delete_message(query.from_user.id, query.message.message_id)
    if db.exists('cart_id'):
        cart_id = db.get('cart_id').decode("utf-8")
    else:
        cart_id = functions.create_cart(query.from_user.id, _strapi_url)
        db.set('cart_id', cart_id)

    # создаем объект CartProduct в корзине cart_id
    functions.add_product_to_cart(cart_id, db.get('product_selected').decode("utf-8"), _strapi_url)
    query.bot.send_message(
        query.from_user.id,
        'Продукт добавлен. Можете добавить еще один продукт или оформить заказ через корзину.',
        reply_markup=keyboards.get_menu_keyboards(_strapi_url))
    return "HANDLE_MENU"


def show_cart(update: Update, context: CallbackContext):
    global _strapi_url
    db = get_database_connection()
    query = update.callback_query
    query.bot.delete_message(query.from_user.id, query.message.message_id)
    url = urljoin(f'{_strapi_url}api/carts/', str(db.get('cart_id').decode("utf-8")))
    payload = {
        'fields[0]': 'tg_id',
        'populate[cartproducts][fields][0]': 'weight',
        'populate[cartproducts][populate][product][fields][0]': 'title',
        'populate[cartproducts][populate][product][fields][1]': 'price',
        'populate[cartproducts][populate][product][fields][2]': 'description',
    }
    response = requests.get(url, params=payload)
    response.raise_for_status()
    cartproducts = response.json()['data']['attributes']['cartproducts']['data']
    message = ''
    keys_for_delete = []
    ids_for_delete = {}
    pay_button = None
    if cartproducts:
        for num, cartproduct in enumerate(cartproducts):
            message += (f"{num+1}. "
                        f"{cartproduct['attributes']['product']['data']['attributes']['title']}, "
                        f"{cartproduct['attributes']['weight']} кг, "
                        f"на сумму {cartproduct['attributes']['weight'] * cartproduct['attributes']['product']['data']['attributes']['price']} руб. \n")
            keys_for_delete.append(InlineKeyboardButton(str(num+1), callback_data=str(num+1)))
            ids_for_delete[str(num+1)] = str(cartproduct['id'])
        message += f'\nДля удаления продукта из корзины нажмите его порядковый номер:'
        db.set('ids_for_delete', json.dumps(ids_for_delete))
        pay_button = InlineKeyboardButton('Оплатить', callback_data='pay')
    else:
        message = f'В корзине пусто.'
    additional_keyboard = [InlineKeyboardButton('В меню', callback_data='menu')]
    if pay_button:
        additional_keyboard.append(pay_button)
    query.bot.send_message(
        query.from_user.id,
        message,
        reply_markup=InlineKeyboardMarkup([keys_for_delete, additional_keyboard]))
    return "HANDLE_CART"


def handle_cart(update: Update, context: CallbackContext):
    query = update.callback_query
    
    if query.data == 'menu':
        return show_menu(update, context)
    
    if query.data == 'pay':
        query.bot.send_message(query.from_user.id, 'Введите е-майл:')
        return 'WAITING_EMAIL'
    
    db = get_database_connection()
    id_for_delete = json.loads(db.get('ids_for_delete').decode("utf-8"))[query.data]
    url = urljoin(f'{_strapi_url}api/cartproducts/', id_for_delete)
    payload = {
        'fields[0]': 'id',
        'populate[product][fields][0]': 'title',
        'populate[product][fields][1]': 'price',
    }
    response = requests.get(url, params=payload)
    response.raise_for_status()
    delete_product = response.json()['data']['attributes']['product']['data']['attributes']
    response = requests.delete(url)
    response.raise_for_status()
    bot_message = query.bot.send_message(
        query.from_user.id,
        f"Продукт № {query.data}. {delete_product['title']} на сумму {delete_product['price']} удален.")
    time.sleep(4)
    query.bot.delete_message(query.from_user.id, bot_message['message_id'])
    return show_cart(update, context)


def waiting_email(update: Update, context: CallbackContext):
    query = update.message
    # проверка e_mail - необходимо улучшить до регулярного выражения
    if not ('@' and '.') in query.text:
        message = query.bot.send_message(query.from_user.id,
                                         f'E-mail введен с ошибкой. Повторите ввод.')
        time.sleep(5)
        query.bot.delete_message(query.from_user.id, message.message_id)
        return 'WAITING_EMAIL'
        
    # проверка наличия пользователя в БД по e_mail
    response = functions.find_user(query.text, _strapi_url)
    user = response.json()
    if user:
        message = query.bot.send_message(query.from_user.id, f'Оплачено. :)))')
        time.sleep(3)
        query.bot.delete_message(query.from_user.id, message.message_id)
    else:
        # и если не находим - создаем юзера
        db = get_database_connection()
        new_user_id = functions.add_user(db.get('cart_id').decode("utf-8"), query.text, _strapi_url)
        message = query.bot.send_message(
            query.from_user.id,
            f'Пользователь добавлен в базу под ID {new_user_id}. Оплачено :)))')
        time.sleep(3)
        query.bot.delete_message(query.from_user.id, message.message_id)
    return show_menu(update, context)


def help_command(update: Update, context: CallbackContext) -> None:
    """Displays info on how to use the bot."""
    update.message.reply_text("Use /start to start.")
    
    
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
        'SHOW_MENU': show_menu,
        'HANDLE_MENU': handle_menu,
        'HANDLE_DESCRIPTION': handle_description,
        'SHOW_CART': show_cart,
        'HANDLE_CART': handle_cart,
        'WAITING_EMAIL': waiting_email,
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
        env = Env()
        env.read_env()
        database_password = env("DATABASE_PASSWORD")
        database_host = env("DATABASE_HOST")
        database_port = env.int("DATABASE_PORT")
        _database = redis.Redis(host=database_host, port=database_port, password=database_password)
    return _database


def main():
    global _strapi_url
    env = Env()
    env.read_env()
    token = env('TELEGRAM_TOKEN')
    _strapi_url = env('STRAPI_URL', 'http://localhost:1337/')
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
