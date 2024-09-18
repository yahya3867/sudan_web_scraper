import pandas as pd
import sys
import os
from bs4 import BeautifulSoup
import requests
from datetime import datetime, date
from pymongo import MongoClient
from dotenv import load_dotenv
import sys
import time
import dateparser
import html
import numpy as np
import cv2

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

# Check if an image is blank
def image_is_blank(image_url):
    response = requests.get(image_url)
    response.raise_for_status()  # Ensure the request was successful

    # Convert the image to a numpy array
    image_bytes = np.asarray(bytearray(response.content), dtype=np.uint8)
    img = cv2.imdecode(image_bytes, cv2.IMREAD_COLOR)

    # Check if the image is blank
    light_pixels = np.sum(img > 244)
    dark_pixels = np.sum(img < 10)
    white_ratio = light_pixels / img.size
    black_ratio = dark_pixels / img.size

    # Return True if the image is blank
    return True if white_ratio > 0.9 or black_ratio > 0.9 else False

# Scrape static articles
def static_scrape_article(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    content = soup.find('div', class_='entry-content-wrap')
    body_content = soup.find('div', class_='entry-content').find_all('p')#[0:-2]

    # Try to get the image
    try:
        srcset = content.find('img', class_='attachment-covernews-featured size-covernews-featured wp-post-image')['srcset']
        image_url = srcset.split(' ')[0]

        if image_is_blank(image_url):
            image_url = []

    except Exception as e:
        image_url = []

    text_list = []
    
    for paragraph in body_content:
        text_list.append(paragraph.get_text())

    text = '\n'.join(text_list)
    raw_text = text.encode('ascii', 'ignore').decode('ascii').replace('\n', '')

    return [raw_text, image_url]

# Static crawler
def static_crawler(articles, trial):
    error_articles = []
    source = 'Dabanga'
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

# Scrape dynamic articles
def dynamic_scrape_article(url):
    current_date = date.today()

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
        driver.get(url)


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
            db_data = {'source': 'test source',
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

# Dynamic crawler
def dynamic_crawler(articles, trial):
    error_articles = []
    source = 'Taghyeer'
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
    dynamic_urls = pd.read_csv('Performance Analysis/al-taghyeer.csv')
    static_urls = pd.read_csv('Performance Analysis/radio-dabanga.csv')

    # Get length of both lists
    dynamic_length = len(dynamic_urls)
    static_length = len(static_urls)

    print(type(num_articles), type(dynamic_length), type(static_length))

    # Randomly select num_articles number of static and dynamic URLs
    static_urls = static_urls.sample(n=(num_articles if num_articles < static_length else static_length))
    dynamic_urls = dynamic_urls.sample(n=(num_articles if num_articles < dynamic_length else dynamic_length))

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

