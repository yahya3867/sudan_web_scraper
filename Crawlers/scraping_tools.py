from bs4 import BeautifulSoup
import pymongo
import os
from datetime import datetime

# Parses articles and returns raw text.
def parse_articles(articles: list):
    for article in articles:
        html = article['body']
        soup = BeautifulSoup(html, features='html.parser')

        # Get text
        text = soup.get_text()
        raw_text = text.encode('ascii', 'ignore').decode('ascii')
        article['body'] = raw_text

    return articles

# Connects to MongoDB and stores articles
def store_articles(articles: list, api_urls=None):
    # Attempt to connect to MongoDB
    try:
        myclient = pymongo.MongoClient(os.getenv('MONGO_URI'))
        mydb = myclient[os.getenv('MONGO_DB')]

    except Exception as e:
        print('Error connecting to MongoDB:', e)
        return False
    
    # Attempt to store articles
    try:
        mycol = mydb[os.getenv('MONGO_ARTICLE_COLLECTION')]
        mycol.insert_many(articles)

    except Exception as e:
        print('Error storing articles:', e)
        return False
    
    if api_urls:
        # Attempt to store articles
        try:
            mycol = mydb[os.getenv('MONGO_API_COLLECTION')]
            mycol.insert_many(api_urls)
            return True

        except Exception as e:
            print('Error storing articles:', e)
            return False
    
    return True

def store_article_analytics(num_articles: int, source: str):
    # Attempt to connect to MongoDB
    try:
        myclient = pymongo.MongoClient(os.getenv('MONGO_URI'))
        mydb = myclient[os.getenv('MONGO_DB')]
        mycol = mydb[os.getenv('MONGO_WEEKLY_COLLECTION')]

    except Exception as e:
        print('Error connecting to MongoDB:', e)
        return False
    
    # If it not is Monday, we will collect the weekly data
    weekday = datetime.today().weekday()
    if weekday != 0:
        # Find current week data
        try:
            results = mycol.find({ 'source': source })

            week_data = results[0]['week_data']

        except Exception as e: # Probably the first time we are storing data
            week_data = [0 for i in range(7)]
        
    else:
        week_data = [0 for i in range(7)]

    # Attempt to store articles
    try:
        week_data[weekday] = num_articles
        week_data = {
            'Monday': week_data[0],
            'Tuesday': week_data[1],
            'Wednesday': week_data[2],
            'Thursday': week_data[3],
            'Friday': week_data[4],
            'Saturday': week_data[5],
            'Sunday': week_data[6]
        }
        filter = { 'source': source }
        newvalues = { "$set": { 'week_data': week_data } }
        mycol.update_one(filter, newvalues, upsert=True) 

        return True

    except Exception as e:
        print('Error storing articles:', e)
        return False

def store_most_recent(article_urls: list, source: str):
    # Attempt to connect to MongoDB
    try:
        myclient = pymongo.MongoClient(os.getenv('MONGO_URI'))
        mydb = myclient[os.getenv('MONGO_DB')]
        mycol = mydb[os.getenv('MONGO_RECENT_COLLECTION')]

    except Exception as e:
        print('Error connecting to MongoDB:', e)
        return False
    
    # Attempt to store urls
    try:
        results = mycol.find({ 'source': source })

        # Collecting the URLs that are found in the database
        found_urls = results[0]['url_list']

        filter = { 'source': source }
        newvalues = { "$set": { 'url_list': article_urls } }
        mycol.update_one(filter, newvalues, upsert=True) 

        return found_urls

    except Exception as e:
        print('Error storing articles:', e)
        return False
