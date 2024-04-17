from dotenv import dotenv_values
import requests
import pandas as pd
from scraping_tools import parse_articles

CONFIG = dotenv_values(".env")
CATEGORIES = ['war crimes', 'war', 'conflict', 'violence', 'military', 'rebel', 'insurgency', 'ceasefires', 'humanitarian crises',
              'rape', 'physical abuse', 'sexual abuse', 'child soldiers', 'child abuse', 'child prostitution', 'torture',
              'bombings', 'weapons & arms', 'gender-based violence']
URL = f'https://content.guardianapis.com/search?q={",".join(CATEGORIES)}&from-date=2023-04-10&tag=world/sudan&api-key={CONFIG["GUARDIAN_API_KEY"]}'

initial_response = requests.get(URL)

num_articles = initial_response.json()['response']['total']

articles = []

# Retrieves articles from a single page with given url and parameters
def page_articles(url, params):
    # List to store articles
    response_items = []
    response = requests.get(url, params=params)

    # Get articles from response
    for i in range(len(response.json()['response']['results'])):
        result = response.json()['response']['results'][i]

        api_url = result['apiUrl'] + '?api-key=' + CONFIG['GUARDIAN_API_KEY']
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
def get_articles():
    # Checks if num articles is less than or equal to 200
    if num_articles <= 200:
        params = {
            'from-date': '2023-04-10',
            'page-size': num_articles,
            'q': ','.join(CATEGORIES),
            'tag': 'world/sudan',
            'api-key': CONFIG['GUARDIAN_API_KEY'],
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
                'from-date': '2023-04-10',
                'page-size': 200,
                'q': ','.join(CATEGORIES),
                'tag': 'world/sudan',
                'api-key': CONFIG['GUARDIAN_API_KEY'],
                'show-fields': 'body',
                'show-elements': 'image',
                'page': i + 1
            }
            url = 'https://content.guardianapis.com/'
            
            articles += page_articles(url, params)

        params = {
            'from-date': '2023-04-10',
            'page-size': final_page_length,
            'q': ','.join(CATEGORIES),
            'tag': 'world/sudan',
            'api-key': CONFIG['GUARDIAN_API_KEY'],
            'show-fields': 'body',
            'show-elements': 'image',
            'page': num_full_pages + 1
        }
        url = 'https://content.guardianapis.com/'
        
        articles += page_articles(url, params)

    
    return parse_articles(articles)

# Run Program
if __name__ == '__main__':
    articles = get_articles()

    # Operate on dataframe
    df = pd.DataFrame(articles)
    df['date'] = pd.to_datetime(df['date'])
    df.sort_values(by='date')
    df['date'] = df['date'].dt.tz_localize(None) # Remove timezone info for excel compatibility

    excel_writer = pd.ExcelWriter('News_Articles/guardian_articles.xlsx')
    df.to_excel('News_Articles/guardian_articles.xlsx')