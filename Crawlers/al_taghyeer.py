from bs4 import BeautifulSoup
import requests
from datetime import datetime, date
import os
import itertools
from scraping_tools import store_articles, store_most_recent, store_article_analytics, identify_date_format
from dotenv import load_dotenv
import sys
import html

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

URL = f'https://www.altaghyeer.info/en/?s=sudan'
SOURCE = 'Al Taghyeer'
current_date = date.today()

# finds all the articles that relates to the Sudan war, war crimes, violence, etc
def find_articles():
    # key words that may be included in the headlines of articles related to the Sudan conflict
    keywords = [
    "conflict", "war", "crisis", "clashes", "military", "coup", 
    "violence", "rebels", "humanitarian", "aid", "refugees", "displacement", 
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
    response = requests.get(URL)
    soup = BeautifulSoup(response.text, 'lxml')
 
    # finds all the articles on that page
    articles = soup.find_all('h2',class_='post-title')

    # checks the headline for the key words
    for article in articles:
        article_title = article.find('a').text.lower()
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
        # finds the deadline
        headline = article.find('h2',class_='post-title').find('a').text

        url = article.find('h2',class_='post-title').find('a')['href']

        # finds the date published
        date = url[31:41]

        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'lxml')

        # combines it as one cohesive paragraph
        body_list = [i.text for i in soup.find('div', class_ = 'entry-content entry clearfix').find_all('p')]

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
            'date': identify_date_format(date).strftime('%Y/%m/%d'),
            'body': html.unescape(str(body)).replace('\xa0', '').replace('\r\n', '').strip(),
            'image_urls': image_urls,
            'archive_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        # stores it into the list    
        article_db.append(db_data)
    return article_db


def init_run():
    keywords = [
        "conflict", "war", "crisis", "clashes", "military", "coup", 
        "violence", "rebels", "humanitarian", "aid", "refugees", "displacement", 
        "peacekeeping", "negotiations", "ceasefire", "sanctions", "regional stability", 
        "ethnic violence", "casualties", "troops", "opposition","diplomacy", 
        "instability", "tensions", "talks", "agreements", "resolution", "bloodshed",
        "brutality", "massacre", "fighting", "destruction", "assault", "warfare", "killing", 
        "killed", "kill",'rape', 'physical abuse', 'sexual abuse', 'child soldiers', 
        'child abuse', 'child prostitution', 'torture', 'reconstruction', 'risk', 'landmines',
        'battles', 'battle', 'tortured', 'torture', 'assassination', 'rsf', 'artillery'
        ]
    # Initialize the WebDriver with options to ignore SSL errors
    chrome_options = Options()
    chrome_options.add_argument('--ignore-certificate-errors')
    chrome_options.add_argument('--ignore-ssl-errors')
    chrome_options.add_argument('--headless')

    driver = webdriver.Chrome(options=chrome_options)
    driver.get("https://www.altaghyeer.info/en/?s=sudan")

    db_list = []
    try:
        driver.get(URL)


        target_date = date(2023, 4, 5)
        artcl_date = current_date

        while target_date < artcl_date:
            
            driver.execute_script("window.scrollBy(0, 8000);")

            
            time.sleep(10)

            
            WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "h2.post-title"))
            )

            
            post_titles = driver.find_elements(By.CSS_SELECTOR, "h2.post-title")
            links = []
            
            for post_title in post_titles:
                links.append(post_title.find_element(By.TAG_NAME, "a").get_attribute('href'))
            year = int(links[-1][31:35])
            month = int(links[-1][36:38])
            day = int(links[-1][39:41])
            artcl_date = date(year, month, day)
        

        
        titles = [i.text for i in driver.find_elements(By.CLASS_NAME, "post-title")]
        post_titles = driver.find_elements(By.CSS_SELECTOR, "h2.post-title")
        links = []
        
        for post_title in post_titles:
            links.append(post_title.find_element(By.TAG_NAME, "a").get_attribute('href'))
        dates = [i[31:41] for i in links]
        body_list = []
        img = []

        for i in links:
            time.sleep(2)
            response = requests.get(i)
            soup = BeautifulSoup(response.text, 'lxml')

            big_body = [i.text for i in soup.find('div', class_ = 'entry-content entry clearfix').find_all('p')]

            body = ''
            for i in range(1, len(big_body)):
                body += big_body[i]
                body += ' '

            body_list.append(body)

            img.append(soup.find('img')['src'])

        i = 0
        while i < len(titles):
            relevant_article = False
            for j in keywords:
                if j in titles[i]:
                    relevant_article = True
            if not relevant_article:
                titles.pop(i)
                links.pop(i)
                dates.pop(i)
                body_list.pop(i)
                img.pop(i)
            i+=1

        for i in range(len(titles)):
            db_data = {'source': SOURCE,
                    'headline': titles[i],
                    'web_url': links[i],
                    'date': dates[i],
                    'body': body_list[i],
                    'image_urls': img[i],
                    'archive_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            db_list.append(db_data)

    except Exception as e:
        print(f"An error occurred: {e}")

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
        articles = init_run()

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

