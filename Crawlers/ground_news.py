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


SOURCE = 'Ground News'
current_date = date.today()
target_date = date(2023,4,5)

def find_articles():
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
    'battles', 'battle', 'tortured', 'torture', 'assassination', 'artillery', 'famine'
    ]

    # stores all the articles that contains any of the key words in the headline
    relevant_articles = []

    # defines the url based on the given page number
    url = f'https://ground.news/interest/sudan_3f002a'
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'lxml')
    # finds all the articles on that page
    articles = soup.find('div', class_= 'col-span-12 desktop:col-span-9 flex flex-col gap-3_2 desktop:pr-1_6 w-full').find_all('div', class_='group')

    # checks the headline for the key words
    for article in articles:
        article_title = str(article.find('a')['href'][9::]).lower()
        for word in keywords:
            if word in article_title:
                relevant_articles.append(article)
                break

    return relevant_articles

# scraped the article for headlines, url, images, body, and date published
def scrape_article():
    # stores all the article data
    article_db = []
    # scrapes the article
    for article in find_articles():
        time.sleep(2)
        url = 'https://ground.news' + article.find('a')['href']

        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'lxml')

        # finds the deadline
        headline = soup.find('h1', id='titleArticle').text

        # finds the date published
        times = soup.find('span', class_='whitespace-nowrap').text[10::]
        timestrings = [str(times)]
        a_date = ''

        for timestring in timestrings:
            dt = dateparser.parse(timestring)
            a_date = dt.strftime("%Y-%m-%d")

        pub_date = a_date

        # creates a list of all the body text
        body_list = [i.text for i in soup.find_all('p', class_='font-normal text-18 leading-9 break-words')]

        # combines it as one cohesive paragraph
        body = ''
        for i in range(1, len(body_list)):
            body += body_list[i]
            body += ' '
        # Find the image urls
        try:
            image_urls = soup.find_all('img')
            image_urls = [i['src'] for i in image_urls]
        except:
            image_urls = 'None'
        # stores it as a dictionary
        db_data = {'source': SOURCE,
            'headline': headline,
            'web_url': url,
            'date': pub_date,
            'body': html.unescape(str(body)).replace('\xa0', '').replace('\r\n', '').strip(),
            'image_urls': image_urls,
            'archive_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        # stores it into the list    
        article_db.append(db_data)
    return article_db

def init_run():
    chrome_options = Options()
    chrome_options.add_argument('--ignore-certificate-errors')
    chrome_options.add_argument('--ignore-ssl-errors')
    chrome_options.add_argument('--headless')
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36")


    driver = webdriver.Chrome(options=chrome_options)
    driver.get('https://ground.news/interest/sudan_3f002a') 

    db_list = []
    try:
        last_date = current_date
        page = 1
        urls = []
        while target_date < last_date:
            print(f'Loading page {page}')
            try:
                driver.execute_script("window.scrollBy(0, 7000);")
                time.sleep(2)
                button = driver.find_element(By.ID, "more_stories")
                driver.execute_script("arguments[0].click();", button)
            except:
                last_date = date(2022,6,7)

            time.sleep(2)

            articles = driver.find_elements(By.CLASS_NAME, 'group')
            urls += [i.find_element(By.TAG_NAME, 'a').get_attribute('href') for i in articles]

            new_driver = webdriver.Chrome(options=chrome_options)
            new_driver.get(urls[-1]) 

            times = new_driver.find_element(By.CSS_SELECTOR, "span.whitespace-nowrap").text[10::]
            timestrings = [str(times)]
            a_date = ''

            for timestring in timestrings:
                dt = dateparser.parse(timestring)
                a_date = dt.strftime("%Y-%m-%d")
            year = int(a_date[0:4])
            month = int(a_date[5:7])
            day = int(a_date[8:10])

            new_driver.quit() 
            time.sleep(2)
            page += 1 
            if date(year, month, day) == last_date:
                break
    except Exception as e:
        print(e)
        pass
    finally:
        driver.quit()
    for i in range(len(urls)):
        response = requests.get(urls[i])
        soup = BeautifulSoup(response.text, 'lxml')

        # finds the deadline
        headline = soup.find('h1', id='titleArticle').text

        # finds the date published
        times = soup.find('span', class_='whitespace-nowrap').text[10::]
        timestrings = [str(times)]
        a_date = ''

        for timestring in timestrings:
            dt = dateparser.parse(timestring)
            a_date = dt.strftime("%Y-%m-%d")

        pub_date = a_date

        # creates a list of all the body text
        body_list = [i.text for i in soup.find_all('p', class_='font-normal text-18 leading-9 break-words')]

        # combines it as one cohesive paragraph
        body = ''
        for i in range(1, len(body_list)):
            body += body_list[i]
            body += ' '
        # Find the image urls
        try:
            image_urls = soup.find_all('img')
            image_urls = [i['src'] for i in image_urls]
        except:
            image_urls = 'None'
        # stores it as a dictionary
        db_data = {'source': SOURCE,
            'headline': headline,
            'web_url': urls[i],
            'date': pub_date,
            'body': html.unescape(str(body)).replace('\xa0', '').replace('\r\n', '').strip(),
            'image_urls': image_urls,
            'archive_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        # stores it into the list    
        db_list.append(db_data)
    return db_list

print(init_run())        

if __name__ == '__main__':
    articles = []
    print(f'Starting {SOURCE} crawler')

    if int(DEPLOYMENT):
        print('Running in deployment mode')
        articles = scrape_article()
    else:
        print('Running in initial mode')
        articles += init_run()
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

