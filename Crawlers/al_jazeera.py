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


SOURCE = 'Al Jazeera'
current_date = date.today()
target_date = date(2024,8,5)
URL = f'https://www.aljazeera.com/where/sudan/'

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
        dates = article.find('div', class_='date-simple css-1yjq2zp').find_all('span')[-1].text.replace('\n', '').strip()

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
            'date': identify_date_format(dates).strftime('%Y/%m/%d'),
            'body': html.unescape(str(body)).replace('\xa0', '').replace('\r\n', '').strip(),
            'image_urls': image_urls,
            'archive_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        print(db_data['image_urls'])
        print()
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
    driver.get(URL) 

    driver.find_element(By.ID, 'onetrust-accept-btn-handler').click()

    db_list = []
    try:
        last_date = current_date
        page = 1
        while target_date < last_date:
            driver.execute_script("window.scrollBy(0, 10000);")
            time.sleep(3)
            section = driver.find_element(By.TAG_NAME, 'section')

            button = driver.find_element(By.CSS_SELECTOR,'.show-more-button.big-margin')
            driver.execute_script("arguments[0].click();", button)

            a_time = section.find_elements(By.TAG_NAME, 'article')[-1].find_element(By.CLASS_NAME, 'date-simple').find_elements(By.TAG_NAME, 'span')[-1].text
            timestrings = [str(a_time)]
            a_date = ''
            for timestring in timestrings:
                dt = dateparser.parse(timestring)
                a_date = dt.strftime("%Y-%m-%d")
            year = int(a_date[0:4])
            month = int(a_date[5:7])
            day = int(a_date[8::])
            last_date = date(year, month, day)

            print(f'Found page {page}')
            page += 1
        
        urls = []

        url = driver.find_elements(By.CLASS_NAME, 'u-clickable-card__link')
        for i in url:
            urls.append(i.get_attribute('href'))
        

        for i in urls[4::]:
            try:
                url = i
                response = requests.get(url)
                soup = BeautifulSoup(response.text, 'lxml')

                # finds the headline
                headline = soup.find('header',class_='article-header').find('h1').text

                # finds the date published
                a_time = soup.find('div', class_ = 'date-simple css-1yjq2zp').find_all('span')[-1].text
                timestrings = [str(a_time)]
                a_date = ''
                for timestring in timestrings:
                    dt = dateparser.parse(timestring)
                    a_date = dt.strftime("%Y-%m-%d")
                dates = a_date
                # creates a list of all the body text
                body_list = [i.text for i in soup.find('div', class_="wysiwyg wysiwyg--all-content css-ibbk12").find_all('p')]
                # combines it as one cohesive paragraph
                body = ''
                for i in range(0, len(body_list)):
                    body += body_list[i]
                    body += ' '
                # Find the image urls
                try:
                    image_urls = 'https://www.aljazeera.com/' + soup.find('div', class_ = 'responsive-image').find('img')['src']
                except:
                    image_urls = 'None'
                # stores it as a dictionary
                db_data = {'source': SOURCE,
                    'headline': headline,
                    'web_url': url,
                    'date': identify_date_format(dates).strftime('%Y/%m/%d'),
                    'body': html.unescape(str(body)).replace('\xa0', '').replace('\r\n', '').strip(),
                    'image_urls': image_urls,
                    'archive_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                # stores it into the list   
                db_list.append(db_data)
            except:
                pass

    except Exception as e:
        print(e)
    finally:
        driver.quit()

    return db_list            

if __name__ == '__main__':
    articles = []
    print(f'Starting {SOURCE} crawler')

    if int(DEPLOYMENT):
        print('Running in deployment mode')
        articles = scrape_article(URL)
    else:
        print('Running in initial mode')
        articles += init_run()
    
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

