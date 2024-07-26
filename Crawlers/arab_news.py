from bs4 import BeautifulSoup
import requests
from datetime import datetime, date
import os
import itertools
from scraping_tools import store_articles, store_most_recent, store_article_analytics
from dotenv import load_dotenv
import sys
import html
import dateparser

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import time


load_dotenv()

DEPLOYMENT = os.getenv('DEPLOYMENT')
if len(sys.argv) > 1:
    if sys.argv[1] == 'initial':
        DEPLOYMENT = False

URL = f'https://www.arabnews.com/tags/sudan'
SOURCE = 'Arab News'
current_date = date.today()

# finds all the articles that relates to the Sudan war, war crimes, violence, etc
def scrape_article():
    chrome_options = Options()
    chrome_options.add_argument('--ignore-certificate-errors')
    chrome_options.add_argument('--ignore-ssl-errors')
    chrome_options.add_argument('--headless')

    driver = webdriver.Chrome(options=chrome_options)
    driver.get("https://www.arabnews.com/tags/sudan") 

    db_list = []
    try:
        driver.get(URL) 

        articles = driver.find_elements(By.CSS_SELECTOR, 'div.article-item-info')

        headlines = []
        urls = []
        dates = []


        for article in articles:
            element = article.find_element(By.TAG_NAME, 'a')
            
            headlines.append(element.text.strip())
            
            urls.append(element.get_attribute('href'))

            times = article.find_element(By.TAG_NAME,'time').text
            timestrings = [str(times)]
            a_date = ''

            for timestring in timestrings:
                dt = dateparser.parse(timestring)
                a_date = dt.strftime("%Y-%m-%d")
                dates.append(a_date)

        img = []
        body_list = []

        for i in urls:
            time.sleep(2)

            new_driver = webdriver.Chrome(options=chrome_options)
            new_driver.get(i)

            try:
                article = new_driver.find_element(By.TAG_NAME,'article')

                big_body = [i.text for i in article.find_elements(By.TAG_NAME, 'p')]
                body = ''
                for i in range(1, len(big_body)):
                    body += big_body[i]
                    body += ' '

                body_list.append(body)

                img.append(article.find_element(By.TAG_NAME,'img').get_attribute('src'))

            except:
                pass
            finally:
                new_driver.quit()
        print(len(headlines),len(urls),len(dates),len(body_list),len(img))
        for i in range(len(headlines)):
            db_data = {'source': SOURCE,
                    'headline': headlines[i],
                    'web_url': urls[i],
                    'date': dates[i],
                    'body': body_list[i],
                    'image_urls': img[i],
                    'archive_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            db_list.append(db_data)
    except:
        pass
    finally:
        driver.quit()

    return db_list

if __name__ == '__main__':
    articles = []
    print(f'Starting {SOURCE} crawler')

    if int(DEPLOYMENT):
        print('Running in deployment mode')
        articles = scrape_article()
    else:
        print('Running in initial mode')
        articles = scrape_article()

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

