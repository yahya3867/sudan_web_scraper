from bs4 import BeautifulSoup
import requests
import os
from datetime import datetime
from scraping_tools import store_articles, store_most_recent, store_article_analytics
from time import sleep
from dotenv import load_dotenv
import sys

load_dotenv()

# List to dict -> ['some headline', 'some url', 'some date'] -> {'headline': 'some headline', 'web-url': 'some url', 'date': 'some date'}
# https://sudanwarmonitor.com/sitemap/(year) -- articles found here
DEPLOYMENT = os.getenv('DEPLOYMENT')
if len(sys.argv) > 1:
    if sys.argv[1] == 'initial':
        DEPLOYMENT = False
        
SOURCE = 'Sudan War Monitor'

# Scrapes sitemap for articles
def find_articles(year: int):
    english_alphabet = 'abcdefghijklmnopqrstuvwxyz'
    articles = []
    
    base_url = f'https://sudanwarmonitor.com/sitemap/{year}'
    response = requests.get(base_url)
    soup = BeautifulSoup(response.text, 'html.parser')

    body_content = soup.find_all('a', class_='sitemap-link')

    for article in body_content:
        headline = article.parent.text.strip()

        if headline[0].lower() in english_alphabet:
            articles.append([headline, article['href']])

    return articles

# Used to scrape the article
def scrape_article(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    text_list = []
    image_urls = []

    # We get tiny errors from very few articles, so we need to handle them
    try:
        date = soup.find('div', class_='pencraft pc-reset _color-pub-secondary-text_3axfk_207 _line-height-20_3axfk_95 _font-meta_3axfk_131 _size-11_3axfk_35 _weight-medium_3axfk_162 _transform-uppercase_3axfk_242 _reset_3axfk_1 _meta_3axfk_442').text.strip()

    except Exception as e:
        print('Error getting date:', e)
        date = 'No date found'
        return None
    
    try:
        body_content = soup.find('div', class_='body markup').find_all(['p', 'blockquote'])

    except Exception as e:
        print('Error getting body content:', e)
        return None

    try:
        images = soup.find('div', class_='body markup').find_all('img')

    except Exception as e:
        print('Error getting images:', e)
        images = []

    # Get text
    for paragraph in body_content:
        text_list.append(paragraph.get_text())

    text = '\n'.join(text_list)
    raw_text = text.encode('ascii', 'ignore').decode('ascii').replace('\n', '')

    try:
        # Get image urls
        for image in images:
            image_urls.append(image['src'])
    
    except Exception as e:
        print('Error getting image:', e)

    return [date, raw_text, image_urls]

# Main function
if __name__ == "__main__":
    articles = []

    if int(DEPLOYMENT):
        print('Running in deployment mode')
        articles = find_articles(datetime.now().year)

    else:
        print('Running in initial mode')
        for year in ['2023', '2024']:
            print(f'Processing year {year}')
            articles += find_articles(year)

    found_articles = store_most_recent([article[1] for article in articles], SOURCE)
    articles = [article for article in articles if article[1] not in found_articles]
    num_articles = len(articles)
    print('filtered articles:', num_articles)

    if num_articles == 0:
        print('No new articles found')
        exit()

    # Now that we have our valid list of articles, we can start processing them
    for i in range(len(articles)):
        # Sleep every 10 articles to avoid getting throttled
        if i % 10 == 0 and i != 0:
            print('Sleeping for 5 seconds')
            sleep(5)

        print('Processing:', articles[i][1], f'{i + 1}/{num_articles}')
        article_data = scrape_article(articles[i][1])
        
        if article_data:
            articles[i] += article_data

    db_articles = []

    for article in articles:
        headline = article[0]
        web_url = article[1]
        date = article[2]
        body = article[3]
        image_urls = article[4]
        
        db_data = {'source': SOURCE,
            'headline': headline,
            'web_url': web_url,
            'date': date,
            'body': body,
            'image_urls': image_urls,
            'archive_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        db_articles.append(db_data)
    
    try:
        store_articles(db_articles) # Store articles in MongoDB
        store_article_analytics(len(articles), SOURCE) # Store article analytics
        print('Articles stored successfully')

    except Exception as e:
        print('Error storing articles:', e)
        exit()
