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

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

load_dotenv()

DEPLOYMENT = os.getenv('DEPLOYMENT')
if len(sys.argv) > 1:
    if sys.argv[1] == 'initial':
        DEPLOYMENT = False

SOURCE = 'Xinhua'
current_date = date.today().strftime("%d/%m/%Y").replace('/', '-')
yesterday = date.fromordinal(date.today().toordinal()-1).strftime("%d/%m/%Y").replace('/', '-')

def find_articles(page_num):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        url = f'https://search.news.cn/?keyWordAll=sudan&keyWordIg=south&searchFields=1&sortField=0&lang=en&senSearch=1#search/1/sudan/{page_num}/0'
        driver.get(url)
        relevant_articles = []
        # Wait for the articles to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "item"))
        )

        soup = BeautifulSoup(driver.page_source, 'lxml')
        # finds all the articles on that page
        articles = soup.find_all('div', class_='item')

        # checks the headline for the key words
        for article in articles:
            if article not in relevant_articles:
                relevant_articles.append(article)
    finally:
        driver.quit() 

    return relevant_articles

# scraped the article for headlines, url, images, body, and date published
def scrape_article(page_num):
    # stores all the article data
    article_db = []

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox") 
    chrome_options.add_argument("--disable-gpu") 
    chrome_options.add_argument("--window-size=1920,1080")
    driver = webdriver.Chrome(options=chrome_options)
    # scrapes the article
    try:
        for article in find_articles(page_num):
            # finds the deadline
            headline = article.find('div',class_='title').find('a').text

            # finds the date published
            date = article.find('div', class_='pub-tim').text[0:10]

            url = article.find('div',class_='title').find('a')['href']
            if '/africa/' not in url:
                driver.get(url)
                
                # Wait for the content to be fully loaded
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "detailContent"))
                )
                
                soup = BeautifulSoup(driver.page_source, 'lxml')

                # creates a list of all the body text
                try:
                    body_list = [i.text for i in soup.find('div', id="detailContent").find_all('p')]

                    # combines it as one cohesive paragraph
                    body = ''
                    for i in range(0, len(body_list)):
                        body += body_list[i]
                        body += ' '
                except:
                    pass
                # Find the image urls
                try:
                    image_urls = soup.find_all('img')
                    image_urls = [i['src'] for i in image_urls]
                except:
                    image_urls = 'No Images'

                # stores it as a dictionary
                db_data = {'source': SOURCE,
                    'headline': headline,
                    'web_url': url,
                    'date': date,
                    'body': html.unescape(str(body)).replace('\xa0', '').replace('\r\n', '').replace('&nbsp;',' ').strip(),
                    'image_urls': image_urls,
                    'archive_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                # stores it into the list    
                article_db.append(db_data)
    finally:
        driver.quit()
        
    return article_db

def find_last_relevant_page():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox") 
    chrome_options.add_argument("--disable-gpu") 
    chrome_options.add_argument("--window-size=1920,1080")
    driver = webdriver.Chrome(options=chrome_options)
    
    try:        
        url = f'https://search.news.cn/?keyWordAll=sudan&keyWordIg=south&searchFields=1&sortField=0&lang=en&senSearch=1#search/1/sudan/1/0'
        driver.get(url)

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "item"))
        )

        soup = BeautifulSoup(driver.page_source, 'lxml')

        last_page = int(soup.find('ul', class_='ant-pagination css-1r287do').find_all('li')[-3].text)

        target_date = date(2023,4,5)

        for i in range(1,last_page):
            url = f'https://search.news.cn/?keyWordAll=sudan&keyWordIg=south&searchFields=1&sortField=0&lang=en&senSearch=1#search/1/sudan/{i}/0'

            time.sleep(20)
            newDriver = webdriver.Chrome(options=chrome_options)

            newDriver.get(url)

            WebDriverWait(newDriver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "item"))
            )

            soup = BeautifulSoup(newDriver.page_source, 'lxml')

            last_date = soup.find_all('div', class_='item')[-1].find('div', class_='pub-tim').text[0:10]

            dt = date(int(last_date[0:4]),int(last_date[5:7]),int(last_date[8:10]))

            print(f'Found page {i}')
            if dt < target_date:
                return i

    finally:
        driver.quit()



if __name__ == '__main__':
    articles = []
    print(f'Starting {SOURCE} crawler')

    if int(DEPLOYMENT):
        print('Running in deployment mode')
        articles = scrape_article(1)
    else:
        print('Running in initial mode')
        last_page = 60
        for i in range(1, last_page+1):
            print(f'Processing page {i} of {last_page}')
            articles += scrape_article(i)
            time.sleep(20)

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

