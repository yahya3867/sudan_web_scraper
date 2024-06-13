from bs4 import BeautifulSoup
import requests
from datetime import datetime, date
import os
import itertools
from scraping_tools import store_articles, store_most_recent, store_article_analytics
from dotenv import load_dotenv
import sys
import html

URL = f'https://www.aljazeera.com/where/sudan/'
load_dotenv()

DEPLOYMENT = os.getenv('DEPLOYMENT')

if len(sys.argv) > 1:
    if sys.argv[1] == 'initial':
        DEPLOYMENT = False


SOURCE = 'Al Jazeera'

current_date = date.today().strftime("%d/%m/%Y").replace('/', '-')
yesterday = date.fromordinal(date.today().toordinal()-1).strftime("%d/%m/%Y").replace('/', '-')

def find_articles(url):
    # key words that may be included in the headlines of articles related to the Sudan conflict
    keywords = [
    "conflict", "war", "crisis", "clashes", "military", "coup", 
    "violence", "rebels", "humanitarian", "aid", "refugees", "displacement", 
    "peacekeeping", "negotiations", "ceasefire", "sanctions", "regional stability", 
    "ethnic violence", "casualties", "troops", "opposition","diplomacy", 
    "instability", "tensions", "talks", "agreements", "resolution", "bloodshed",
    "brutality", "massacre", "fighting", "destruction", "assault", "warfare", "killing", 
    "killed", "kill",'rape', 'physical abuse', 'sexual abuse', 'child soldiers', 
    'child abuse', 'child prostitution', 'torture', 'reconstruction', 'risk', 'landmines'
    ]

    # stores all the articles that contains any of the key words in the headline
    relevant_articles = []

    # defines the url based on the given page number

    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'lxml')
 
    # finds all the articles on that page
    articles = soup.find_all('article', class_='gc u-clickable-card gc--type-post gc--list gc--with-image')

    # checks the headline for the key words
    for article in articles:
        article_title = article.find('a',class_='u-clickable-card__link').find('span').text.lower()
        for word in keywords:
            if word in article_title:
                relevant_articles.append(article)
                break

    return relevant_articles

# scraped the article for headlines, url, images, body, and date published
def scrape_article(url):
    # stores all the article data
    article_db = []
    # scrapes the article
    for article in find_articles(url):
        # finds the deadline
        headline = article.find('a',class_='u-clickable-card__link').find('span').text

        # finds the date published
        date = article.find('div', class_='date-simple css-1yjq2zp').find_all('span')[-1].text.replace('\n', '').strip()

        url = 'https://www.aljazeera.com/where/sudan/' + article.find('a',class_='u-clickable-card__link')['href']
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'lxml')

        # creates a list of all the body text
        body_list = [i.text for i in soup.find('div', class_="wysiwyg wysiwyg--all-content css-ibbk12").find_all('p')]

        # combines it as one cohesive paragraph
        body = ''
        for i in range(0, len(body_list)):
            body += body_list[i]
            body += ' '
        # Find the image urls
        image_urls = soup.find_all('img')
        image_urls = [i['src'] for i in image_urls]
        # stores it as a dictionary
        db_data = {'source': SOURCE,
            'headline': headline,
            'web_url': url,
            'date': date,
            'body': html.unescape(str(body)).replace('\xa0', '').replace('\r\n', '').strip(),
            'image_urls': image_urls,
            'archive_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        print(db_data['image_urls'])
        print()
        # stores it into the list    
        article_db.append(db_data)
    return article_db


if __name__ == '__main__':
    articles = []
    print(f'Starting {SOURCE} crawler')

    if int(DEPLOYMENT):
        print('Running in deployment mode')
        articles = scrape_article(URL)
    else:
        print('Running in initial mode')
        articles += scrape_article(URL)
    print('Running in initial mode')
    last_page = find_last_relevant_url()
    last_date = '05-04-2023'
    for i in range(1, last_page+1):
        print(f'Processing page {i} of {last_page}')
        articles += scrape_article(i, current_date, last_date)

    # Remove duplicates
    articles = list(k for k, _ in itertools.groupby(articles)) # Remove duplicates

    found_articles = store_most_recent([article for article in articles], SOURCE)
    articles = [article for article in articles if article not in found_articles]
    
    num_articles = len(articles)
    print(num_articles)

    if num_articles == 0:
        print('No new articles found')
        exit()

    # Now that we have our valid list of articles, we can start processing them
    for i in range(len(articles)):
        print('Processing:', articles[i]['headline'], f'{i + 1}/{num_articles}')

    db_articles = []

    for article in articles:
        db_articles.append(article)
    
    try:
        store_articles(db_articles) # Store articles in MongoDB
        store_article_analytics(len(articles), SOURCE) # Store article analytics
        print('Articles stored successfully')

    except Exception as e:
        print('Error storing articles:', e)
        exit()

