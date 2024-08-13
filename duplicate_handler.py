from bs4 import BeautifulSoup
from pymongo import MongoClient
import os
from datetime import datetime
import datefinder
from dotenv import load_dotenv
from bson import ObjectId

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

def find_duplicates():
    # Attempt to connect to MongoDB
    try:
        db = connect_to_mongo()

    except Exception as e:
        print('Error connecting to MongoDB:', e)
        return False
    
    article_collection = db[os.getenv('MONGO_ARTICLE_COLLECTION')]

    pipeline = [
        {
            "$group": {
                "_id": "$web_url",
                "count": {"$sum": 1},
                "archive_dates": {"$push": "$archive_date"},
                "ids": {"$push": "$_id"}
            }
        },
        {
            "$match": {
                "_id": {"$ne": None},
                "count": {"$gt": 1}
            }
        },
        {
            "$project": {
                "web_url": "$_id",
                "archive_dates": 1,
                "ids": 1,
                "_id": 0
            }
        }
    ]

    duplicates = list(article_collection.aggregate(pipeline))

    return duplicates

# Selects duplicates by oldest date (keeps newest)
def select_for_removal(duplicates):
    old_ids = []

    for entry in duplicates:
        # Parse the archive_dates into datetime objects
        dates = [datetime.strptime(date, "%Y-%m-%d %H:%M:%S") for date in entry['archive_dates']]
        
        # Find the index of the newest date
        newest_date_index = dates.index(max(dates))
        
        # Collect all ids except the one corresponding to the newest date
        for i, id in enumerate(entry['ids']):
            if i != newest_date_index:
                old_ids.append(id)

    return old_ids

def delete_duplicates(old_ids):
    # Attempt to connect to MongoDB
    try:
        db = connect_to_mongo()

    except Exception as e:
        print('Error connecting to MongoDB:', e)
        return False
    
    article_collection = db[os.getenv('MONGO_ARTICLE_COLLECTION')]

    # Convert the list of strings to ObjectId instances
    object_ids = [ObjectId(oid) for oid in old_ids]

    # Delete all documents with the given ObjectIds
    article_collection.delete_many({"_id": {"$in": object_ids}})

    

duplicates = find_duplicates()
if len(duplicates) > 0:
    print('Found duplicates:', len(duplicates))
    print('Removing duplicates...')

    old_ids = select_for_removal(duplicates)
    delete_duplicates(old_ids)

    print('Duplicates removed.')

else:
    print('No duplicates found.')

