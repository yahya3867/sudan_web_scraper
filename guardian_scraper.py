import requests
import pandas as pd
from scraping_tools import parse_articles, store_to_mongo
import os
from datetime import datetime, timedelta

DEPLOYMENT = os.getenv('DEPLOYMENT')
API_KEY = os.getenv('GUARDIAN_API_KEY')
CATEGORIES = ['war crimes', 'war', 'conflict', 'violence', 'military', 'rebel', 'insurgency', 'ceasefires', 'humanitarian crises',
              'rape', 'physical abuse', 'sexual abuse', 'child soldiers', 'child abuse', 'child prostitution', 'torture',
              'bombings', 'weapons & arms', 'gender-based violence']

# Retrieves articles from a single page with given url and parameters
def page_articles(url, params):
    # List to store articles
    response_items = []
    response = requests.get(url, params=params).json()

    # Get articles from response
    for i in range(len(response['response']['results'])):
        result = response['response']['results'][i]

        api_url = result['apiUrl'] + '?api-key=' + API_KEY
        web_url = result['webUrl']
        headline = result['webTitle']
        date = result['webPublicationDate']
        body = result['fields']['body']

        # Gets image urls
        image_urls = []
        try:
            for asset in result['elements'][0]['assets']:
                image_urls.append(asset['typeData']['secureFile'])
        except KeyError:
            pass

        response_items.append({
            'source': 'The Guardian',
            'api_url': api_url,
            'web_url': web_url,
            'headline': headline,
            'date': date,
            'body': body,
            'image_urls': image_urls,
        })

    return response_items

# Formats api urls and calls 'page_articles' to get articles
def get_articles(num_articles, date = '2023-04-10'):
    # Checks if num articles is less than or equal to 200
    if num_articles <= 200:
        params = {
            'from-date': date,
            'page-size': num_articles,
            'q': ','.join(CATEGORIES),
            'tag': 'world/sudan',
            'api-key': API_KEY,
            'show-fields': 'body',
            'show-elements': 'image'
        }

        base_url = 'https://content.guardianapis.com/search'
        
        articles = page_articles(base_url, params)

    # If num articles is greater than 200, get articles in chunks of 200 (max page size)
    else:
        num_full_pages = num_articles // 200
        final_page_length = num_articles % 200

        for i in range(num_full_pages):
            params = {
                'from-date': date,
                'page-size': 200,
                'q': ','.join(CATEGORIES),
                'tag': 'world/sudan',
                'api-key': API_KEY,
                'show-fields': 'body',
                'show-elements': 'image',
                'page': i + 1
            }
            url = 'https://content.guardianapis.com/'
            
            articles += page_articles(url, params)

        params = {
            'from-date': date,
            'page-size': final_page_length,
            'q': ','.join(CATEGORIES),
            'tag': 'world/sudan',
            'api-key': API_KEY,
            'show-fields': 'body',
            'show-elements': 'image',
            'page': num_full_pages + 1
        }
        url = 'https://content.guardianapis.com/'
        
        articles += page_articles(url, params)

    
    return parse_articles(articles)

# Run Program
if __name__ == '__main__':
    # If in deploypemt, get articles from yesterday
    yesterday = datetime.now() - timedelta(days=1) # Yesterday's date
    formatted_yesterday = yesterday.strftime('%Y-%m-%d')

    if int(DEPLOYMENT):
        URL = f'https://content.guardianapis.com/search?q={",".join(CATEGORIES)}&from-date={formatted_yesterday}&tag=world/sudan&api-key={API_KEY}'

        # Get the initial response to get the number of articles
        initial_response = requests.get(URL)
        num_articles = initial_response.json()['response']['total']

        articles = get_articles(num_articles, formatted_yesterday)
    
    # If not in deployment, get articles from 2023-04-10
    else:
        URL = f'https://content.guardianapis.com/search?q={",".join(CATEGORIES)}&from-date=2023-04-10&to-date={formatted_yesterday}&tag=world/sudan&api-key={API_KEY}'

        # Get the initial response to get the number of articles
        initial_response = requests.get(URL)
        num_articles = initial_response.json()['response']['total']

        articles = get_articles(num_articles)

    if len(articles) == 0:
        pass # TODO discuss what should be done in the case of no articles?

    else:
        status = store_to_mongo(articles)

        if status:
            print('Articles stored successfully.')

        else:
            print('Error storing articles.') # we can try to error response here

