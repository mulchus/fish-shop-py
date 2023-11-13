import requests

from urllib.parse import urljoin


def get_product(product_id, strapi_url):
    payload = {
            'populate': 'picture',
        }
    url = f'{strapi_url}api/products/'
    if product_id:
        url = urljoin(url, str(product_id))
    response = requests.get(url, params=payload)
    response.raise_for_status()
    return response.json()['data']


def find_user(user_email, strapi_url):
    url = f'{strapi_url}api/users'
    payload = {'filters[email][$eq]': user_email}
    response = requests.get(url, params=payload)
    response.raise_for_status()
    return response.json()


def find_cart(chat_id, strapi_url):
    url = f'{strapi_url}api/carts'
    payload = {'filters[tg_id][$eq]': str(chat_id)}
    response = requests.get(url, params=payload)
    response.raise_for_status()
    return response


def create_cart(chat_id, strapi_url):
    cart_params = {
        "data": {
            "tg_id": str(chat_id),
        }
    }
    url = f'{strapi_url}api/carts'
    headers = {
        'Content-Type': 'application/json'
    }
    response = requests.post(url, headers=headers, json=cart_params)
    response.raise_for_status()
    return response.json()['data']['id']


def add_user(cart_id, user_email, strapi_url):
    user_params = {
        "username": user_email,
        "email": user_email,
        "cart": cart_id,
        "password": "111111",
        "role": 0,
        "confirmed": "True",
        }
    url = f'{strapi_url}api/users'
    headers = {'Content-Type': 'application/json'}
    response = requests.post(url, headers=headers, json=user_params)
    response.raise_for_status()
    return response.json()['id']


def add_product_to_cart(cart_id, product_id, strapi_url):
    cartproduct_params = {
        "data": {
            "product": product_id,
            "weight": 1,
            "cart": cart_id,
        }
    }
    url = f'{strapi_url}api/cartproducts'
    headers = {'Content-Type': 'application/json'}
    response = requests.post(url, headers=headers, json=cartproduct_params)
    response.raise_for_status()
