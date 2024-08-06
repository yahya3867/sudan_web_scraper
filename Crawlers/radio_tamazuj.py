from bs4 import BeautifulSoup
import requests
from datetime import datetime, date
import os
import itertools
from scraping_tools import store_articles, store_most_recent, store_article_analytics
from dotenv import load_dotenv
import sys
import html

load_dotenv()

DEPLOYMENT = os.getenv('DEPLOYMENT')

if len(sys.argv) > 1:
    if sys.argv[1] == 'initial':
        DEPLOYMENT = False


SOURCE = 'Radio Tamazuj'
current_date = date.today().strftime("%d/%m/%Y").replace('/', '-')
yesterday = date.fromordinal(date.today().toordinal()-1).strftime("%d/%m/%Y").replace('/', '-')

def find_articles(page_num, curr_date, prior_date):
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
    url = f'https://www.radiotamazuj.org/en/news?startdate={prior_date}&enddate={curr_date}&search=sudan&page={page_num}'
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'lxml')
 
    # finds all the articles on that page
    articles = soup.find_all('div', class_='list-item news-item-small')

    # checks the headline for the key words
    for article in articles:
        article_title = article.find('h3',class_='heading-c').find('a').text.lower()
        for word in keywords:
            if word in article_title:
                relevant_articles.append(article)
                break

    return relevant_articles

# scraped the article for headlines, url, images, body, and date published
def scrape_article(page_num, curr_date, prior_date):
    # stores all the article data
    article_db = []
    # scrapes the article
    for article in find_articles(page_num, curr_date, prior_date):
        # finds the deadline
        headline = article.find('h3',class_='heading-c').find('a').text

        url = 'https://www.radiotamazuj.org' + article.find('h3',class_='heading-c').find('a')['href']
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'lxml')

        # finds the date published
        date = soup.find('span', class_='time').text.replace('\n', '').strip()

        # creates a list of all the body text
        body_list = [i.text for i in soup.find('div', class_="body-text").find_all('p')]

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

    url = f'https://www.radiotamazuj.org/en/news?startdate=05-04-2023&enddate={current_date}&search=sudan&page=1'
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'lxml')
    last_page = int(soup.find('ul', class_='pagerfanta pagerfanta-sm').find_all('li')[-2].text)

    return last_page

if __name__ == '__main__':
    articles = []
    print(f'Starting {SOURCE} crawler')

    if int(DEPLOYMENT):
        print('Running in deployment mode')
        articles = scrape_article(1, current_date, yesterday)
    else:
        print('Running in initial mode')
        last_page = find_last_relevant_page()
        last_date = '05-04-2023'
        for i in range(1, last_page+1):
            print(f'Processing page {i} of {last_page}')
            articles += scrape_article(i, current_date, last_date)


    # Remove duplicates
    articles = list(k for k, _ in itertools.groupby(articles)) # Remove duplicates

    found_articles = store_most_recent([article['web_url'] for article in articles], SOURCE)
    articles = [article for article in articles if article['web_url'] not in found_articles]
    
    num_articles = len(articles)

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

