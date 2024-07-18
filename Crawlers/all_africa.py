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


SOURCE = 'allAfrica'
current_date = date.today().strftime("%d/%m/%Y").replace('/', '-')
yesterday = date.fromordinal(date.today().toordinal()-1).strftime("%d/%m/%Y").replace('/', '-')

def find_articles(page_num):
    # defines the url based on the given page number
    url = f'https://allafrica.com/sudan/?page={page_num}'
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'lxml')
    # finds all the articles on that page
    articles = soup.find('ul', class_ = 'stories').find_all('li', class_=False)

    return articles

# scraped the article for headlines, url, images, body, and date published
def scrape_article(page_num):
    # stores all the article data
    article_db = []
    # scrapes the article
    for article in find_articles(page_num):
        time.sleep(10)
        # finds the deadline
        headline = article.find('span', class_ ='headline').text

        url = 'https://allafrica.com' + article.find('a')['href']
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'lxml')

        # finds the date published
        date = soup.find('div', class_="publication-date").text.replace('\n', '').strip()

        # creates a list of all the body text
        body_list = [i.text for i in soup.find_all('p', class_ = 'story-body-text')]

        # combines it as one cohesive paragraph
        body = ''
        for i in range(1, len(body_list)):
            body += body_list[i]
            body += ' '
        # Find the image urls
        image_urls = 'None'
        try:
            image_urls = soup.find_all('img',class_= 'figure picture story-header')
            image_urls = [i['src'] for i in image_urls]
        except:
            pass
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

if __name__ == '__main__':
    articles = []
    print(f'Starting {SOURCE} crawler')

    if int(DEPLOYMENT):
        print('Running in deployment mode')
        articles = scrape_article(1)
    else:
        print('Running in initial mode')
        last_page = 7
        for i in range(1, last_page+1):
            print(f'Processing page {i} of {last_page}')
            articles += scrape_article(i)

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

