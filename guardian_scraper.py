from dotenv import dotenv_values
import requests
from bs4 import BeautifulSoup
import pandas as pd
import openpyxl

config = dotenv_values(".env")

URL = f'https://content.guardianapis.com/search?from-date=2023-04-10&tag=world/sudan,global-development/conflict-and-development&api-key={config["GUARDIAN_API_KEY"]}'

initial_response = requests.get(URL)

num_articles = initial_response.json()['response']['total']

articles = []

def page_articles(url, params):
    response_items = []

    response = requests.get(url, params=params)
    for i in range(len(response.json()['response']['results'])):
        api_url = response.json()['response']['results'][i]['apiUrl'] + '?api-key=' + config['GUARDIAN_API_KEY']
        web_url = response.json()['response']['results'][i]['webUrl']
        headline = response.json()['response']['results'][i]['webTitle']
        date = response.json()['response']['results'][i]['webPublicationDate']
        body = response.json()['response']['results'][i]['fields']['body']
        response_items.append({
            'api_url': api_url,
            'web_url': web_url,
            'headline': headline,
            'date': date,
            'body': body
        })

    return response_items

def get_articles():
    if num_articles <= 200:
        params = {
            'from-date': '2023-04-10',
            'page-size': num_articles,
            'tag': 'world/sudan,global-development/conflict-and-development',
            'api-key': config['GUARDIAN_API_KEY'],
            'show-fields': 'body'
        }

        url = 'https://content.guardianapis.com/search'
        
        articles = page_articles(url, params)

        return articles

    else:
        num_full_pages = num_articles // 200
        final_page_length = num_articles % 200

        URL = f'https://content.guardianapis.com/search?from-date=2023-04-10&page-' \
            f'size=200&tag=world/sudan,global-development/conflict-and-development&api-key={config["GUARDIAN_API_KEY"]}'
        for i in range(num_full_pages):
            
            articles += page_articles(URL)

        URL = f'https://content.guardianapis.com/search?from-date=2023-04-10&page-' \
            f'size={final_page_length}&tag=world/sudan,global-development/conflict-and-development&api-key={config["GUARDIAN_API_KEY"]}'
        
        articles += page_articles(URL)

        return articles

articles = get_articles()
df = pd.DataFrame(articles)
excel_writer = pd.ExcelWriter('file.xlsx')
df.to_excel('guardian_articles.xlsx')