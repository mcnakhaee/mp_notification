
import streamlit as st
import pandas as pd
import re
import requests
from bs4 import BeautifulSoup
import httpx
import time
import random
import os

search_terms = [ 'verzemling','lenzen','Hasselblad', 'kowa', 'asahi', 'yashica', 'bronica', 'mamiya', 'pentax',
                'rolleiflex',
                'rolleicord', 'rollei', 'nikon', 'canon', 'zenit', 'takumar', 'topcon', 'primo',
                'nikkormat', 'nicca', 'topcoflex', 'asahiflex', 'miranda', 'pancolar', 'autocord',
                'kalloflex' , 'primoplan', 'exakta', 'krasnogorsk', 'edixa']
#search_terms = ['pentax', 'yashica', 'bronica']
# Replace with your token and chat ID
# Read from environment variables
search_terms_film = [['fuji','kodak','portra','kodak gold','a']]
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

netherlands_bounds = {
    "lat_min": 50.5,
    "lat_max": 53.5,
    "lon_min": 3.4,
    "lon_max": 7.2
}

URL = 'https://www.marktplaats.nl/lrp/api/search'
Item = dict

def get_category_number(input_string):
    pattern = r'\d+'
    match = re.search(pattern, input_string)
    return match.group() if match else None

def get_category(url='https://www.marktplaats.nl/cp/31/audio-tv-en-foto/'):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    elements = soup.find_all(attrs={"data-testid": True})

    categories = {}
    for element in elements:
        data_testid_value = element.get('data-testid')
        numerical_value_id = get_category_number(data_testid_value)
        href_value = element.get('href')
        if data_testid_value:
            categories[href_value] = numerical_value_id
    return categories

def get_items(game: str, cat_1=31, cat_2=480):
    query = {
        "l1CategoryId": cat_1,
        "l2CategoryId": cat_2,
        "limit": 100,
        "offset": 0,
        "query": game,
        "searchInTitleAndDescription": "true",
        "viewOptions": "list-view",
    }
    resp = httpx.get(URL, params=query)
    resp.raise_for_status()
    return resp.json()['listings']

def get_item_title(searched_items):
    data = {
        'item': [],
        'title': [],
        'description': [],
        'img_url': [],
        'product_url': [],
        'latitude': [],
        'longitude': [],
        'price': [],
        'delivery': [],
        'dates': [],
        'extended_attributes': [],
        'seller_names': []
    }

    for item in searched_items:
        data['item'].append(item['itemId'])
        data['product_url'].append(f"https://link.marktplaats.nl/{item['itemId']}")
        data['title'].append(item['title'])
        data['description'].append(item.get('description', ''))
        data['price'].append(item['priceInfo']['priceCents'] / 100)
        data['latitude'].append(item['location']['latitude'])
        data['longitude'].append(item['location']['longitude'])
        data['dates'].append(item['date'])
        data['seller_names'].append(item['sellerInformation']['sellerName'])

        try:
            data['img_url'].append(item['pictures'][0]['mediumUrl'])
        except (KeyError, IndexError):
            data['img_url'].append('https://fotohandeldelfshaven.b-cdn.net/wp-content/uploads/2024/02/52301.jpg')

        try:
            data['delivery'].append(next(attr['value'] for attr in item['attributes'] if attr['key'] == 'delivery'))
        except (KeyError, StopIteration):
            data['delivery'].append('')

        try:
            data['extended_attributes'].append(item['extendedAttributes'][0]['value'])
        except (KeyError, IndexError):
            data['extended_attributes'].append('')

    df = pd.DataFrame(data)

    df_netherlands = df[
        (df['latitude'] >= netherlands_bounds['lat_min']) &
        (df['latitude'] <= netherlands_bounds['lat_max']) &
        (df['longitude'] >= netherlands_bounds['lon_min']) &
        (df['longitude'] <= netherlands_bounds['lon_max'])
    ]
    return df_netherlands
def send_to_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    response = requests.post(url, json=payload)
    return response.json()


def send_to_telegram_df(df):
    # items_today = read_csv('items_today.csv')
    for _, row in df.iterrows():
        message = f"{row['title']}\nPrice: **{row['price']}**\n{row['product_url']}"
        send_to_telegram(message)


def search_and_send_to_telegram(search_terms, cat_1=31, cat_2=480):
    try:
        last_items = pd.read_csv('items_today.csv')
    except FileNotFoundError:
        last_items = pd.DataFrame(columns=['item'])

    results = []
    last_item_ids = set(last_items['item'].values)
    for term in search_terms:
        items = get_items(term, cat_1, cat_2)
        filtered_items = [item for item in items if
                          term.lower() in item['title'].lower() and item['itemId'] not in last_item_ids]
        results.extend(filtered_items)
        time.sleep(random.uniform(20, 35))

    latest_items = get_item_title(results)
    latest_items = latest_items[latest_items['dates'] == 'Vandaag']
    send_to_telegram_df(latest_items)
    df_items = pd.concat([latest_items, last_items])
    df_items.to_csv('items_today.csv', index=False)
    return df_items
def main():
    search_and_send_to_telegram(search_terms=search_terms)
    try:
        search_and_send_to_telegram(search_terms=search_terms_film, cat_1=31, cat_2=1115)
    except:
        print('some error')

# Streamlit app
if __name__ == "__main__":
    main()
