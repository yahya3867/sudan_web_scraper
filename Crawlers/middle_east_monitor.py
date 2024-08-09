from bs4 import BeautifulSoup
import requests
from datetime import datetime, date
import os
import itertools
from scraping_tools import store_articles, store_most_recent, store_article_analytics, identify_date_format
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


SOURCE = 'Middle East Monitor'
current_date = date.today()
target_date = date(2023,4,5)

# finds all the articles that relates to the Sudan war, war crimes, violence, etc
def scrape_articles(page_num):
    chrome_options = Options()
    chrome_options.add_argument('--ignore-certificate-errors')
    chrome_options.add_argument('--ignore-ssl-errors')
    chrome_options.add_argument('--headless')
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36")


    driver = webdriver.Chrome(options=chrome_options)

    db_list = []
    try:
        driver.get(f'https://www.middleeastmonitor.com/category/region/africa-2/sudan/page/{page_num}/') 
        time.sleep(3)

        articles = driver.find_elements(By.CLASS_NAME, "memo-news-item-wrap")

        headlines = []
        urls = []
        dates = []

        for article in articles:            
            headlines.append(article.find_element(By.CLASS_NAME,'memo-news-title').find_element(By.TAG_NAME, 'a').text.strip())
            
            urls.append(article.find_element(By.CLASS_NAME,'memo-news-title').find_element(By.TAG_NAME, 'a').get_attribute('href'))

            times = article.find_element(By.CLASS_NAME,'memo-author-date-wrap').find_element(By.TAG_NAME, 'li').text.strip()
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

            time.sleep(3)
            try:
                img.append(new_driver.find_element(By.CLASS_NAME, 'memo-single-news-featured-img').find_element(By.TAG_NAME,'img').get_attribute('src'))
            except:
                img.append('None')
            body = ''
            container = new_driver.find_element(By.XPATH, "/html/body/div[3]/div/section[2]/div/div[4]/div[1]/div[2]")
            big_body = [i.text for i in container.find_elements(By.TAG_NAME, 'p')]
            for i in range(0, len(big_body)):
                body += big_body[i]
                body += ' '  
            body_list.append(body)

            new_driver.quit()
        for i in range(len(headlines)):
            db_data = {'source': SOURCE,
                    'headline': headlines[i],
                    'web_url': urls[i],
                    'date': identify_date_format(dates[i]).strftime('%Y/%m/%d'),
                    'body': body_list[i],
                    'image_urls': img[i],
                    'archive_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            db_list.append(db_data)
    except Exception as e:
        pass
    finally:
        driver.quit()

    return db_list


def find_last_relevant_page():
    chrome_options = Options()
    chrome_options.add_argument('--ignore-certificate-errors')
    chrome_options.add_argument('--ignore-ssl-errors')
    chrome_options.add_argument('--headless')
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36")

    page = 1
    last_date = current_date
    while last_date > target_date:
        time.sleep(2)
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(f'https://www.middleeastmonitor.com/category/region/africa-2/sudan/page/{page}/') 
        time.sleep(2)
        print(f'Found Page {page}')

        article = driver.find_elements(By.CLASS_NAME, "memo-news-item-wrap")[-1]

        times = article.find_element(By.CLASS_NAME,'memo-author-date-wrap').find_element(By.TAG_NAME, 'li').text.strip()
        timestrings = [str(times)]
        a_date = ''

        for timestring in timestrings:
            dt = dateparser.parse(timestring)
            a_date = dt.strftime("%Y-%m-%d")
        year = int(a_date[0:4])
        month = int(a_date[5:7])
        day = int(a_date[8:10])
        last_date = date(year, month, day)
        page += 1

    
        driver.quit()

    return page

        
if __name__ == '__main__':
    articles = []
    print(f'Starting {SOURCE} crawler')

    if int(DEPLOYMENT):
        print('Running in deployment mode')
        articles = scrape_articles(1)
    else:
      print('Running in initial mode')
      last_page = find_last_relevant_page()
      i = 1
      while i <= last_page:
          try:
            time.sleep(2)
            print(f'Processing page {i} of {last_page}')
            articles += scrape_articles(i)
            i+=1
          except Exception as e:
              print(e)
              time.sleep(5)

    # Remove duplicates
    articles = list(k for k, _ in itertools.groupby(articles)) # Remove duplicates

    found_articles = store_most_recent([article['web_url'] for article in articles], SOURCE)
    articles = [article for article in articles if article['web_url'] not in found_articles]
    
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
