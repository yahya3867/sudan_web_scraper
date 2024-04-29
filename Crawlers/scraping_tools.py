from bs4 import BeautifulSoup
import pymongo
import os

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
def store_to_mongo(articles: list, api_urls=None):
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