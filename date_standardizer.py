from dateutil import parser
from pymongo import MongoClient
import os
from datetime import datetime
from dotenv import load_dotenv
import datefinder

load_dotenv()

non_identified_dates = []

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

def get_documents(collection):
    return collection.find()

def identify_date_format(date_string):
    try:
        matches = list(datefinder.find_dates(date_string))
        if matches:
            return matches[0]
        return None

    except Exception as e:
        print(f"Error parsing date: {e}")
        return None

def update_documents(collection, non_identified_dates):
    documents = get_documents(collection)

    article_number = 1
    for document in documents:
        print(f"Processing article: {article_number}")
        article_number += 1

        date_string = document['date']
        parsed_date = identify_date_format(date_string)
        if not parsed_date:
            non_identified_dates.append(document['web_url'])
        
        else:
            document['date'] = parsed_date
            collection.update_one({'_id': document['_id']}, {'$set': {'date': parsed_date.strftime('%Y/%m/%d')}})
        
    print(non_identified_dates)

db = connect_to_mongo()
article_collection = db[os.getenv('MONGO_ARTICLE_COLLECTION')]
update_documents(article_collection, non_identified_dates)

print("Non-identified dates:", non_identified_dates)
print("Date standardization complete.")
