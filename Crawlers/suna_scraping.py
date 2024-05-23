from bs4 import BeautifulSoup
import requests
from datetime import datetime as dt

SOURCE = 'SUNA'

# finds all the articles that relates to the Sudan war, war crimes, violence, etc
def find_articles(page_num):
    # key words that may be included in the headlines of articles related to the Sudan conflict
    keywords = [
    "conflict", "war", "crisis", "clashes", "military", "coup", 
    "violence", "rebels", "humanitarian", "aid", "refugees", "displacement", 
    "peacekeeping", "negotiations", "ceasefire", "sanctions", "regional stability", 
    "ethnic violence", "casualties", "troops", "opposition","diplomacy", 
    "instability", "tensions", "talks", "agreements", "resolution", "bloodshed",
    "brutality", "massacre", "fighting", "destruction", "assault", "warfare", "killing", 
    "killed", "kill",'rape', 'physical abuse', 'sexual abuse', 'child soldiers', 
    'child abuse', 'child prostitution', 'torture',
    ]

    # stores all the articles that contains any of the key words in the headline
    relevant_articles = []

    # defines the url based on the given page number
    url = f'https://suna-sd.net/suna/24/en?page={page_num}'
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'lxml')
 
    # finds all the articles on that page
    articles = soup.find_all('div', class_='news-list-item articles-list')

    # checks the headline for the key words
    for article in articles:
        article_title = article.find('a',class_='title').text.lower()
        for word in keywords:
            if word in article_title:
                relevant_articles.append(article)
                break

    return relevant_articles

# scraped the article for headlines, url, images, body, and date published
def scrape_article(page_num):
    # stores all the article data
    article_db = []
    # scrapes the article
    for article in find_articles(page_num):
        # finds the deadline
        headline = article.find('a',class_='title').text

        # finds the date published
        date = article.find('li').text
        date = date[date.find('/')-2:date.find('/')+17]

        url = article.find('a',class_='title')['href']
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'lxml')

        # creates a list of all the body text
        body_list = [i.text for i in soup.find('div', class_="post_details_block").find_all('p')]

        # combines it as one cohesive paragraph
        body = ''
        for i in range(1, len(body_list)):
            body += body_list[i]
        #find the image urls
        image_urls = soup.find('img')['src']

        # stroes it as a dictionary
        db_data = {'source': SOURCE,
            'headline': headline,
            'web_url': url,
            'date': date,
            'body': str(body),
            'image_urls': image_urls,
            'archive_date': dt.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        #stores it into the list
        article_db.append(db_data)
    return article_db

print(scrape_article(1)[0])

