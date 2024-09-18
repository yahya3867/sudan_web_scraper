import pandas as pd
import sys
import os
from bs4 import BeautifulSoup
import requests
from datetime import datetime
from pymongo import MongoClient
from dotenv import load_dotenv
import sys
import time
import dateparser
import html

load_dotenv()

# Selenium imports
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options

NUM_ARTICLES = 1

# Get command line arguments
if len(sys.argv) > 1:
    if sys.argv[1] == 'full':
        NUM_ARTICLES = 500

# Connect to MongoDB
def connect_to_mongo():
    # Connection details
    username = os.getenv('MONGO_USERNAME')
    password = os.getenv('MONGO_PASSWORD')
    database_name = os.getenv('MONGO_DB')

    # Create a connection URI
    uri = f"mongodb://{username}:{password}@localhost:27017/{database_name}?authSource={database_name}"

    # Connect to the database
    client = MongoClient(uri)
    db = client[database_name]

    return db

# Stores the time taken to scrape articles
def store_times(documents: list):
    # Attempt to connect to MongoDB
    try:
        db = connect_to_mongo()

    except Exception as e:
        print('Error connecting to MongoDB:', e)
        return False
    
    # Attempt to store articles
    try:
        time_collection = db[os.getenv('MONGO_SCRAPING_TIME_COLLECTION')]
        time_collection.insert_many(documents)

    except Exception as e:
        print('Error storing documents:', e)
        return False
    
    return True

# Scrapes static articles
def static_scrape_article(url):
    article_db = []

    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    # Finds the date published
    date = soup.find('span', class_='item-metadata posts-date').text.replace('\n', '').strip()
    timestrings = [str(date)]
    a_date = ''

    for timestring in timestrings:
        dt = dateparser.parse(timestring)
        a_date = dt.strftime("%Y-%m-%d")
        date = a_date

    # Creates a list of all the body text
    body_list = [i.text for i in soup.find('div', class_="entry-content").find_all('p')]

    # Combines it as one cohesive paragraph
    body = ''

    for i in range(1, len(body_list)):
        body += body_list[i]
        body += ' '

    # Find the image urls
    image_urls = soup.find('div', class_ = 'post-thumbnail full-width-image').find('img')['src']

    # Stores it as a dictionary
    db_data = {'source': 'Radio Tamazuj',
        'headline': 'headline',
        'web_url': url,
        'date': date,
        'body': html.unescape(str(body)).replace('\xa0', '').replace('\r\n', '').strip(),
        'image_urls': image_urls,
        'archive_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    # Stores it into the list    
    article_db.append(db_data)

    return article_db

# Static crawler
def static_crawler(articles, trial):
    error_articles = []
    source = 'Static'
    times = []

    # Process article list
    for i in range(len(articles)):
        try:
            start_time = time.time()

            print('Processing:', articles[i], f'{i + 1}/{NUM_ARTICLES}')
            static_scrape_article(articles[i])

            end_time = time.time()
            duration = end_time - start_time
            times.append(duration)

        except Exception as e:
            print('Error processing article:', e)
            error_articles.append(articles[i])

    documents = []

    for duration in times:
        document = {
            'source': source,
            'duration': duration,
            'trial_number': trial,
        }

        documents.append(document)
    
    # Store the times
    store_times(documents)

# Scrapes dynamic articles
def dynamic_scrape_article(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    body = soup.find('div', class_='wp_content') # changeto whatever category the body is
    content = body.find_all('p') # changeto possible change here

    text_list = []

    for paragraph in content:
        text_list.append(paragraph.get_text())

    text = '\n'.join(text_list)
    raw_text = text.encode('ascii', 'ignore').decode('ascii').replace('\n', '')

    # Identify if image exists
    try:
        image_exists = soup.find('img', class_='attachment-str-singular size-str-singular lazy-img wp-post-image')['src']

        if image_exists:
            image_url = dynamic_scrape_image(url)

    except TypeError:
        image_url = None

    return [raw_text, image_url]

# Scrapes dynamic images
def dynamic_scrape_image(url):
    try:
        # Setup the driver
        options = Options()
        options.add_argument("--headless=new")
        driver = webdriver.Chrome(options=options)
        locator = (By.CSS_SELECTOR, '.attachment-str-singular.size-str-singular.lazy-img.wp-post-image')
        placeholder_src = 'https://sudantribune.com/wp-content/themes/sudantribune/images/no-image.jpg'
        driver.get(url)

        # Wait until the src attribute of the image is not the placeholder's src
        WebDriverWait(driver, 10).until(
            lambda driver: driver.find_element(*locator).get_attribute('src') != placeholder_src
        )
        image_url = driver.find_element(*locator).get_attribute('src')

    except Exception as e:
        print('Error scraping image:', e)
        image_url = None

    finally:
        driver.quit()

    return image_url

# Dynamic crawler
def dynamic_crawler(articles, trial):
    error_articles = []
    source = 'Dynamic'
    times = []

    # Process article list
    for i in range(len(articles)):
        try:
            start_time = time.time()

            print('Processing:', articles[i], f'{i + 1}/{NUM_ARTICLES}')
            dynamic_scrape_article(articles[i])

            end_time = time.time()
            duration = end_time - start_time
            times.append(duration)

        except Exception as e:
            print('Error processing article:', e)
            error_articles.append(articles[i])

    documents = []

    for duration in times:
        document = {
            'source': source,
            'duration': duration,
            'trial_number': trial,
        }

        documents.append(document)

    # Store the times
    store_times(documents)

def get_lists(num_articles=NUM_ARTICLES):
    dynamic_urls = pd.read_csv('al-taghyeer.csv')
    static_urls = pd.read_csv('radio-dabanga`.csv')

    # Get length of both lists
    dynamic_length = len(dynamic_urls)
    static_length = len(static_urls)

    # Randomly select num_articles number of static and dynamic URLs
    static_urls = static_urls.sample(n={num_articles if num_articles < static_length else static_length})
    dynamic_urls = dynamic_urls.sample(n={num_articles if num_articles < dynamic_length else dynamic_length})

    # Reset the index
    static_urls.reset_index(drop=True, inplace=True)
    dynamic_urls.reset_index(drop=True, inplace=True)

    # Convert web_url column to list
    static_urls = static_urls['web_url'].tolist()
    dynamic_urls = dynamic_urls['web_url'].tolist()

    return static_urls, dynamic_urls

if __name__ == '__main__':
    for i in range(1, 11):
        print('Executing trial:', i, 'of 10...')
        static_urls, dynamic_urls = get_lists()

        # Static crawler
        print('Beginning static crawler...')
        static_crawler(static_urls, i)

        # Dynamic crawler
        print('Beginning dynamic crawler...')
        dynamic_crawler(dynamic_urls, i)

    print('All trials completed...')

