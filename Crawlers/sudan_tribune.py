from bs4 import BeautifulSoup
import requests
import os
import itertools
from datetime import datetime
from scraping_tools import store_to_mongo
import json 

# List to dict -> ['some headline', 'some url', 'some date'] -> {'headline': 'some headline', 'web-url': 'some url', 'date': 'some date'}
# https://sudantribune.com/post_tag-sitemap.xml -- categories found here
TAGS = ['arbitrary-detention', 'darfur-conflict', 'darfur-conflicthumanitarian',
'darfur-groups', 'darfur-peacekeeping-mission-unamid', 'human-rights', 'humanitarian',
'kidnapping', 'rsf']
DEPLOYMENT = os.getenv('DEPLOYMENT')

def get_articles_from_page(soup) -> list:
    post_items = soup.find_all('div', class_='post-item col-md-4')
    articles = []

    for post in post_items:
        headline = post.find('h3', 'entry__title').text.replace('\n', '')
        web_url = post.find('a')['href']
        date = post.find('li', 'entry__meta-date').text #TODO needs to be converted to datetime
        article_data = [headline, web_url, date]
        articles.append(article_data)

    return articles

# Used to speed up the initial run wont be used in deployment
def get_articles_by_tag(tag) -> list:
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

def scrape_article(url) -> dict:
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    body = soup.find('div', class_='wp_content')
    content = body.find_all('p')

    text_list = []

    for paragraph in content:
        text_list.append(paragraph.get_text())

    text = '\n'.join(text_list)
    raw_text = text.encode('ascii', 'ignore').decode('ascii').replace('\n', '')

    try:
        image_url = soup.find('img', class_='attachment-str-singular size-str-singular lazy-img wp-post-image')['src']

        if image_url == 'https://sudantribune.com/wp-content/themes/sudantribune/images/no-image.jpg':
            image_url = None

    except TypeError:
        image_url = None

    return [raw_text, image_url]


if __name__ == '__main__':
    articles = []
    TAGS = ['rsf']
    if int(DEPLOYMENT):
        for tag in TAGS:
            url = f'https://sudantribune.com/articletag/{tag}'
            response = requests.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')

            articles += get_articles_from_page(soup)

    else:
        for tag in TAGS:
            articles += get_articles_by_tag(tag)

    articles.sort()
    articles = list(k for k, _ in itertools.groupby(articles)) # Remove duplicates

    articles = remove_non_relevant_articles(articles) # Remove articles that are not relevant by date

    # Now that we have our valid list of articles, we can start processing them
    for article in articles:
        article_data = scrape_article(article[1])
        article += article_data

    db_articles = []

    for article in articles:
        headline = article[0]
        web_url = article[1]
        date = article[2]
        body = article[3]
        image_urls = article[4]

        db_articles.append({'source': 'Sudan Tribune', 'headline': headline, 'web_url': web_url, 'date': date, 'body': body, 'image_urls': image_urls})
    
    try:
        store_to_mongo(db_articles) # Store articles in MongoDB

    except Exception as e:
        with open("sudantribune.json", "w") as outfile: 
            json.dump(db_articles, outfile)