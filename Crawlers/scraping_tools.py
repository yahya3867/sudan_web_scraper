from bs4 import BeautifulSoup
from pymongo import MongoClient
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

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
        db = connect_to_mongo()

    except Exception as e:
        print('Error connecting to MongoDB:', e)
        return False
    
    # Attempt to store articles
    try:
        article_column = db[os.getenv('MONGO_ARTICLE_COLLECTION')]
        article_column.insert_many(articles)

    except Exception as e:
        print('Error storing articles:', e)
        return False
    
    if api_urls:
        # Attempt to store articles
        try:
            article_column = db[os.getenv('MONGO_API_COLLECTION')]
            article_column.insert_many(api_urls)
            return True

        except Exception as e:
            print('Error storing articles:', e)
            return False
    
    return True

def store_article_analytics(num_articles: int, source: str):
    # Attempt to connect to MongoDB
    try:
        db = connect_to_mongo()
        analytics_column = db[os.getenv('MONGO_ANALYTICS_COLLECTION')]

    except Exception as e:
        print('Error connecting to MongoDB:', e)
        return False
    
    try:
        date = datetime.now().strftime('%Y-%m-%d')
        
        # Check if there is already an entry for today
        results = list(analytics_column.find({ '_id': date }))

        if len(results) == 0:
            # Create a new entry
            new_entry = {
                '_id': date,
                'articles': {
                    source: num_articles
                }
            }
            analytics_column.insert_one(new_entry)
        
        else: # Update the existing entry
            filter = { '_id': date }
            newvalues = { "$inc": { f'articles.{source}': num_articles } }
            analytics_column.update_one(filter, newvalues)
    
    except Exception as e:
        print('Error storing articles:', e)
        return False

def store_most_recent(article_urls: list, source: str):
    # Attempt to connect to MongoDB
    try:
        db = connect_to_mongo()
        recent_column = db[os.getenv('MONGO_RECENT_COLLECTION')]

    except Exception as e:
        print('Error connecting to MongoDB:', e)
        return False
    
    # Attempt to store urls
    try:
        results = list(recent_column.find({ 'source': source }))

        if len(results) == 0:
            # Create a new entry
            new_entry = {
                'source': source,
                'url_list': article_urls
            }
            recent_column.insert_one(new_entry)
            return []

        else:
            # Collecting the URLs that are found in the database
            found_urls = results[0]['url_list']

            filter = { 'source': source }
            newvalues = { "$set": { 'url_list': article_urls } }
            recent_column.update_one(filter, newvalues, upsert=True) 

        return found_urls

    except Exception as e:
        print('Error storing articles:', e)
        return False
