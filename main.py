import requests
from environs import Env

env = Env()
env.read_env()

STRAPI_TOKEN = env.str('STRAPI_TOKEN')
# DEBUG = env.bool('DEBUG', True)


def get_products(url):
    headers = {
        'Authorization ': f'bearer {STRAPI_TOKEN}',
    }
    # payload = {
    #     'key1': 'value1',
    #     'key2': 'value2'
    # }
    response = requests.get(url)
    # response = requests.get(url, headers=headers)
    print(response.url)
    # response = requests.get(images_url, params=payload)
    response.raise_for_status()
    return response


def main():
    url = 'http://localhost:1337/api/products'
    products = get_products(url)
    print(products.content.decode('utf8'))


if __name__ == '__main__':
    main()
