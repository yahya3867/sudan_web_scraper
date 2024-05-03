from bs4 import BeautifulSoup
import requests
import os
import itertools
from datetime import datetime
from scraping_tools import store_articles, store_most_recent, store_article_analytics
import json

# Selenium imports
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options

# List to dict -> ['some headline', 'some url', 'some date'] -> {'headline': 'some headline', 'web-url': 'some url', 'date': 'some date'}
# https://sudantribune.com/post_tag-sitemap.xml -- categories found here
TAGS = ['arbitrary-detention', 'darfur-conflict', 'darfur-conflicthumanitarian',
'darfur-groups', 'darfur-peacekeeping-mission-unamid', 'human-rights', 'humanitarian',
'kidnapping', 'rsf']
DEPLOYMENT = os.getenv('DEPLOYMENT')
SOURCE = 'Sudan Tribune'

def get_articles_from_page(soup) -> list:
    post_items = soup.find_all('div', class_='post-item col-md-4')
    articles = []

    for post in post_items:
        headline = post.find('h3', 'entry__title').text.replace('\n', '')
        web_url = post.find('a')['href']
        date = post.find('li', 'entry__meta-date').text
        article_data = [headline, web_url, date]
        articles.append(article_data)

    return articles

# Used to speed up the initial run wont be used in deployment
def get_articles_by_tag(tag) -> list:
    articles = []

    url = f'https://sudantribune.com/articletag/{tag}'
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    articles = get_articles_from_page(soup) # Get articles from first page if only one page we just return
    
    # Check if navbar exists
    nav_bar = soup.find('nav', class_='pages-numbers pagination') # Identifies if there are multiple pages
    
    if nav_bar is not None: # Multiple pages
        last_button = nav_bar.find('a', class_='pagination__page pagination__page--last')

        if last_button is None:
            last_page = int(nav_bar.find_all('a')[-2].text)

        else: # Many pages
            last_page = nav_bar.find_all('a')[-1]['href'].split('/')[-2]
            
        for i in range(2, int(last_page) + 1):
            url = f'https://sudantribune.com/articletag/{tag}/page/{i}'
            response = requests.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            articles += get_articles_from_page(soup)

    return articles

def remove_non_relevant_articles(articles) -> list:
    relevant_date = datetime(2023, 4, 15)

    date_format = ' %d %B  %Y'

    for article in articles:
        article_date = datetime.strptime(article[2], date_format)

        if article_date < relevant_date:
            articles.remove(article)
            
    return articles

def scrape_image(url):
    # Setup the driver
    options = Options()
    options.add_argument("--headless=new")
    driver = webdriver.Chrome(options=options)
    locator = (By.CSS_SELECTOR, '.attachment-str-singular.size-str-singular.lazy-img.wp-post-image')
    placeholder_src = 'https://sudantribune.com/wp-content/themes/sudantribune/images/no-image.jpg'
    driver.get(url)

    try:
        # Wait until the src attribute of the image is not the placeholder's src
        WebDriverWait(driver, 10).until(
            lambda driver: driver.find_element(*locator).get_attribute('src') != placeholder_src
        )
        image_url = driver.find_element(*locator).get_attribute('src')
    finally:
        driver.quit()

    return image_url

def scrape_article(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    body = soup.find('div', class_='wp_content') # changeto whatever tag the body is
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
            image_url = scrape_image(url)

    except TypeError:
        image_url = None

    return [raw_text, image_url]

if __name__ == '__main__':
    articles = []
    print(f'Starting {SOURCE} crawler')

    if int(DEPLOYMENT):
        for tag in TAGS:
            url = f'https://sudantribune.com/articletag/{tag}'
            response = requests.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')

            articles += get_articles_from_page(soup)

    else:
        for i in range(len(TAGS)):
            print(f'Processing tag {i + 1} of {len(TAGS)}')
            articles += get_articles_by_tag(TAGS[i])

    print('unfiltered articles:', len(articles))

    # Remove duplicates and articles that are not relevant by date
    articles.sort()
    articles = list(k for k, _ in itertools.groupby(articles)) # Remove duplicates
    articles = remove_non_relevant_articles(articles) # Remove articles that are not relevant by date

    found_articles = store_most_recent([article[1] for article in articles], SOURCE)
    articles = [article for article in articles if article[1] not in found_articles]
    num_articles = len(articles)
    print('filtered articles:', num_articles)
    
    if num_articles == 0:
        print('No new articles found')
        exit()

    # Now that we have our valid list of articles, we can start processing them
    for i in range(len(articles)):
        print('Processing:', articles[i][1], f'{i + 1}/{num_articles}')
        article_data = scrape_article(articles[i][1])
        articles[i] += article_data

    db_articles = []

    for article in articles:
        headline = article[0]
        web_url = article[1]
        date = article[2]
        body = article[3]
        image_urls = article[4]
        
        db_data = {'source': SOURCE,
            'headline': headline,
            'web_url': web_url,
            'date': date,
            'body': body,
            'image_urls': image_urls,
            'archive_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        db_articles.append(db_data)
    
    try:
        store_articles(db_articles) # Store articles in MongoDB
        store_article_analytics(len(articles), SOURCE) # Store article analytics

    except Exception as e:
        with open("sudantribune.json", "w") as outfile: 
            json.dump(db_articles, outfile)
