from bs4 import BeautifulSoup
import requests
from datetime import datetime as dt
import os
import itertools
from scraping_tools import store_articles, store_most_recent, store_article_analytics
from dotenv import load_dotenv
import sys
import html

load_dotenv()

DEPLOYMENT = os.getenv('DEPLOYMENT')
if sys.argv[1] == 'initial':
    DEPLOYMENT = False


SOURCE = 'SUNA'

# finds all the articles that relates to the Sudan war, war crimes, violence, etc
def find_articles(page_num):
    # key words that may be included in the headlines of articles related to the Sudan conflict
    keywords = [
    "conflict", "war", "crisis", "clashes", "military", "coup", 
    "violence", "rebels", "humanitarian", "aid", "refugees", "displacement", 
    "peacekeeping", "negotiations", "ceasefire", "sanctions", "regional stability", 
    "ethnic violence", "casualties", "troops", "opposition","diplomacy", 
    "instability", "tensions", "talks", "agreements", "resolution", "bloodshed",
    "brutality", "massacre", "fighting", "destruction", "assault", "warfare", "killing", 
    "killed", "kill",'rape', 'physical abuse', 'sexual abuse', 'child soldiers', 
    'child abuse', 'child prostitution', 'torture',
    ]

    # stores all the articles that contains any of the key words in the headline
    relevant_articles = []

    # defines the url based on the given page number
    url = f'https://suna-sd.net/suna/24/en?page={page_num}'
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'lxml')
 
    # finds all the articles on that page
    articles = soup.find_all('div', class_='news-list-item articles-list')

    # checks the headline for the key words
    for article in articles:
        article_title = article.find('a',class_='title').text.lower()
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
        headline = article.find('a',class_='title').text

        # finds the date published
        date = article.find('li').text
        date = date[date.find('/')-2:date.find('/')+17]

        url = article.find('a',class_='title')['href']
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'lxml')

        # creates a list of all the body text
        body_list = [i.text for i in soup.find('div', class_="post_details_block").find_all('p')]

        # combines it as one cohesive paragraph
        body = ''
        for i in range(1, len(body_list)):
            body += body_list[i]
        # Find the image urls
        image_urls = soup.find('img')['src']

        # stores it as a dictionary
        db_data = {'source': SOURCE,
            'headline': headline,
            'web_url': url,
            'date': date,
            'body': html.unescape(body).replace('\xa0', '').replace('\r\n', '').strip(),
            'image_urls': image_urls,
            'archive_date': dt.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        # stores it into the list    
        article_db.append(db_data)
    return article_db

# finds the last page needed to scrape based on the date
def find_last_relevant_page():
    
    url = f'https://suna-sd.net/suna/24/en?page=1'
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'lxml')
    # grabs the last possible page
    last_page = int(soup.find_all('a', class_='page-link')[-2].text)
    # the earliest relevant date for the articles
    target_date = dt(2023, 4, 5)

    # tries to relevant articles on page i
    for i in range(1,last_page):
        try:
            last_article = find_articles(i)[-1]
        except:
            pass

        # grabs date of the article and converts it to a datetime object
        date_str = str(last_article.find('li').text)
        date_str = date_str[date_str.find('/')-2:date_str.find('/')+17]
        article_year = int(date_str[6:10])
        article_month = int(date_str[3:5])
        article_day = int(date_str[0:2])
        article_date = dt(article_year, article_month, article_day)

        # compares article date to the target date
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
        last_page = find_last_relevant_page()
        for i in range(1, last_page+1):
            print(f'Processing page {i} of {last_page}')
            articles += scrape_article(i)
    
    # Remove duplicates
    found_articles = store_most_recent([article for article in articles], SOURCE)
    articles = [article for article in articles if article not in found_articles]
    
    num_articles = len(articles)
    
    if num_articles == 0:
        print('No new articles found')
        exit()

    # processes articles into the db
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

