from bs4 import BeautifulSoup
import requests
import os
import itertools
from datetime import datetime
from scraping_tools import store_articles, store_most_recent, store_article_analytics
import cv2
import numpy as np
from dotenv import load_dotenv

load_dotenv()

# List to dict -> ['some headline', 'some url', 'some date'] -> {'headline': 'some headline', 'web-url': 'some url', 'date': 'some date'}
# https://www.dabangasudan.org/category-sitemap.xml -- categories found here
TAGS = ['violence', 'sexual-violence', 'refugees-displaced']
DEPLOYMENT = os.getenv('DEPLOYMENT')
SOURCE = 'Radio Dabanga'

# Collects all article urls from a page
def get_articles_from_page(soup) -> list:
    post_item_container = soup.find('main', class_='site-main')
    post_items = post_item_container.find_all('article')
    articles = []

    for post in post_items:
        title_link = post.find('h3', class_="article-title article-title-1").find('a')
        headline = title_link.text.replace('\n', '').strip()
        web_url = title_link['href']
        date = post.find('span', class_='item-metadata posts-date').text.replace('\n', '').strip()
        article_data = [headline, web_url, date]
        articles.append(article_data)

    return articles

# Used to speed up the initial run wont be used in deployment
def get_articles_by_tag(tag) -> list:
    articles = []

    base_url = f'https://www.dabangasudan.org/en/all-news/category/{tag}'
    response = requests.get(base_url)
    soup = BeautifulSoup(response.text, 'html.parser')

    articles = get_articles_from_page(soup) # Get articles from first page if only one page we just return
    
    # Check if navbar exists
    nav_bar = soup.find('div', class_='nav-links') # Identifies if there are multiple pages
    
    if nav_bar is not None: # Multiple pages
        last_page = nav_bar.find_all('a', class_='page-numbers')[-2].text # Last page
            
        for i in range(2, int(last_page) + 1):
            url = f'{base_url}/page/{i}'
            response = requests.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            articles += get_articles_from_page(soup)

    return articles

def remove_non_relevant_articles(articles) -> list:
    relevant_date = datetime(2023, 4, 15)
    date_format = '%d/%m/%Y %H:%M'

    # Create a new list to store the relevant articles
    articles = [article for article in articles if datetime.strptime(article[2], date_format) >= relevant_date]
            
    return articles

# Used to determine if the image is blank
def image_is_blank(image_url):
    # Fetch the image
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

# Used to scrape the article
def scrape_article(url):
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

# Main function
if __name__ == '__main__':
    articles = []
    print(f'Starting {SOURCE} crawler')

    if int(DEPLOYMENT):
        for tag in TAGS:
            url = f'https://www.dabangasudan.org/en/all-news/category/{tag}'
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
        print('Articles stored successfully')

    except Exception as e:
        print('Error storing articles:', e)
        exit()