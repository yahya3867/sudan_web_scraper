from bs4 import BeautifulSoup
import requests
from datetime import datetime, date
import os
import itertools
from scraping_tools import store_articles, store_most_recent, store_article_analytics
from dotenv import load_dotenv
import sys
import html
import time

load_dotenv()

DEPLOYMENT = os.getenv('DEPLOYMENT')
if len(sys.argv) > 1:
    if sys.argv[1] == 'initial':
        DEPLOYMENT = False


SOURCE = 'Darfur 24'
current_date = date.today().strftime("%d/%m/%Y").replace('/', '-')
yesterday = date.fromordinal(date.today().toordinal()-1).strftime("%d/%m/%Y").replace('/', '-')

def find_articles(page_num):
    # key words that may be included in the headlines of articles related to the Sudan conflict
    keywords = [
    "conflict", "war", "crisis", "clashes", "military", "coup", 
    "violence", "rebels", "humanitarian", "aid", "displacement", 
    "peacekeeping", "negotiations", "ceasefire", "sanctions", "regional stability", 
    "ethnic violence", "casualties", "troops", "opposition","diplomacy", 
    "instability", "tensions", "talks", "agreements", "resolution", "bloodshed",
    "brutality", "massacre", "fighting", "destruction", "assault", "warfare", "killing", 
    "killed", "kill",'rape', 'physical abuse', 'sexual abuse', 'child soldiers', 
    'child abuse', 'child prostitution', 'torture', 'reconstruction', 'risk', 'landmines',
    'battles', 'battle', 'tortured', 'torture', 'assassination', 'rsf', 'artillery'
    ]

    # stores all the articles that contains any of the key words in the headline
    relevant_articles = []

    # defines the url based on the given page number
    url = f'https://www.darfur24.com/en/category/news-en/page/{page_num}/'
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'lxml')
    # finds all the articles on that page
    articles = soup.find_all('article')

    # checks the headline for the key words
    for article in articles:
        article_title = article.find('h2',itemprop='headline').find('a').text.lower()
        for word in keywords:
            if word in article_title:
                relevant_articles.append(article)
                break

    return relevant_articles

# scraped the article for headlines, url, images, body, and date published
def scrape_article(page_num):
    # stores all the article data
    article_db = []
    # scrapes the article
    for article in find_articles(page_num):
        # finds the deadline
        headline = article.find('h2',itemprop='headline').find('a').text

        # finds the date published
        date = article.find('div', class_='screen-reader-text').text.replace('\n', '').strip()

        url = article.find('h2',itemprop='headline').find('a')['href']
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'lxml')

        # creates a list of all the body text
        body_list = [i.text for i in soup.find('div', class_="entry-the-content").find_all('p')]

        # combines it as one cohesive paragraph
        body = ''
        for i in range(1, len(body_list)):
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
        # stores it into the list    
        article_db.append(db_data)
    return article_db

def find_last_relevant_page():

    url = f'https://www.darfur24.com/en/category/news-en/page/1/'
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'lxml')
    last_page = int(soup.find_all('a', class_='page-numbers')[-2].text)

    target_date = datetime(2023, 4, 5)
    for i in range(1,last_page):
        time.sleep(10)
        try:
            last_article = find_articles(i)[-1]
            print(f'Found page {i}')
        except:
            pass
        date_str = str(last_article.find('div', class_='screen-reader-text').text.replace('\n', '').strip())
        article_year = int(date_str[0:4])
        article_month = int(date_str[5:7])
        article_day = int(date_str[8:10])
        article_date = datetime(article_year, article_month, article_day)

        if article_date < target_date:
            return i
        
if __name__ == '__main__':
    articles = []
    print(f'Starting {SOURCE} crawler')

    if int(DEPLOYMENT):
        print('Running in deployment mode')
        articles = scrape_article(1)
    else:
      print('Running in initial mode')
      last_page = 63
      i = 1
      while i < last_page + 1:
          try:
            time.sleep(10)
            articles += scrape_article(i)
            print(f'Processing page {i} of {last_page}')
            i+=1
            print(i)
          except:
              time.sleep(15)

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
        print('Processing:', articles['headline'], f'{i + 1}/{num_articles}')

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

