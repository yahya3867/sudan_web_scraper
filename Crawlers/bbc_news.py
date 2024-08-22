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

URL = 'https://www.bbc.com/news/topics/cq23pdgvgm8t'


SOURCE = 'BBC News'
current_date = date.today().strftime("%d/%m/%Y").replace('/', '-')
yesterday = date.fromordinal(date.today().toordinal()-1).strftime("%d/%m/%Y").replace('/', '-')

def find_articles():
    # defines the url based on the given page number
    response = requests.get(URL)
    soup = BeautifulSoup(response.text, 'lxml')
 
    # finds all the articles on that page
    articles = soup.find('div', class_= "sc-93223220-0 sc-da05643e-1 fiJvSm djXsFQ").find_all('div', class_ = False)

    return articles

# scraped the article for headlines, url, images, body, and date published
def scrape_article():
    # stores all the article data
    article_db = []
    # scrapes the article
    for article in find_articles():
        try:
            headline = article.find('h2',class_='sc-4fedabc7-3 bvDsJq').text

            url = 'https://www.bbc.com' + article.find('a',class_='sc-2e6baa30-0 gILusN')['href']
            response = requests.get(url)
            soup = BeautifulSoup(response.text, 'lxml')

            # finds the date published
            time = soup.find('time', class_='sc-1d2e900b-10 WPunI').text
            timestrings = [str(time)]
            a_date = ''

            for timestring in timestrings:
                dt = dateparser.parse(timestring)
                a_date = dt.strftime("%Y-%m-%d")

            # creates a list of all the body text
            body_list = [i.text for i in soup.find_all('p', class_ = 'sc-eb7bd5f6-0 fYAfXe')]

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
                'date': a_date,
                'body': html.unescape(str(body)).replace('\xa0', '').replace('\r\n', '').strip(),
                'image_urls': image_urls,
                'archive_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            # stores it into the list    
            article_db.append(db_data)
        except Exception as e:
            print(e)
            
    return article_db

def init_run():
    
    # Initialize the WebDriver with options to ignore SSL errors
    chrome_options = Options()
    chrome_options.add_argument('--ignore-certificate-errors')
    chrome_options.add_argument('--ignore-ssl-errors')
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('window-size=1920x1080')  

    driver = webdriver.Chrome(options=chrome_options)
    driver.get("https://www.bbc.com/news/topics/cq23pdgvgm8t") 

    db_list = []
    try:
        driver.get(URL) 


        target_date = date(2023, 4, 5)
        artcl_date = date.today()

        page = 0

        while target_date < artcl_date:
            # Scroll the button into view if necessary
            driver.execute_script("window.scrollBy(0, 8000);")

            
            time.sleep(10)

            urls = []
            links = driver.find_elements(By.CSS_SELECTOR, 'div[data-testid="alaska-grid"] a[data-testid="internal-link"]')
            for link in links:
                urls.append(link.get_attribute('href'))

            for i in urls:
                try:

                    url = i
                    response = requests.get(url)
                    soup = BeautifulSoup(response.text, 'lxml')

                    headline = soup.find('h1', class_ = 'sc-518485e5-0 bWszMR').text
                    a_time = soup.find('time', class_='sc-1d2e900b-10 WPunI').text
                    timestrings = [str(a_time)]
                    a_date = ''

                    for timestring in timestrings:
                        dt = dateparser.parse(timestring)
                        a_date = dt.strftime('%Y/%m/%d')

                    # creates a list of all the body text
                    body_list = [i.text for i in soup.find_all('p', class_ = 'sc-eb7bd5f6-0 fYAfXe')]


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
                        'date': a_date,
                        'body': html.unescape(str(body)).replace('\xa0', '').replace('\r\n', '').strip(),
                        'image_urls': image_urls,
                        'archive_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    # stores it into the list    
                    db_list.append(db_data)
                except:
                    pass


            last_date = db_list[-1]['date']
            year = int(last_date[0:4])
            month = int(last_date[5:7])
            day = int(last_date[8:10])

            artcl_date = date(year, month, day)

            time.sleep(10)

            next_button = driver.find_element(By.CSS_SELECTOR, '[data-testid="pagination-next-button"]')
            driver.execute_script("arguments[0].click();", next_button)

            page += 1
            print(f'Found page {page}')

            

    except Exception as e:
        print(f"An error occurred: {e}")

    
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
