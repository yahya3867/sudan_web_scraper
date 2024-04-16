from dotenv import dotenv_values
import requests
from bs4 import BeautifulSoup

config = dotenv_values(".env")

URL = f'https://content.guardianapis.com/world/sudan?from-date2023-04-10&tag=war&api-key={config["GUARDIAN_API_KEY"]}'

print(URL)
response = requests.get(URL)

response_items = []

for i in range(len(response.json()['response']['leadContent'])):
    api_url = response.json()['response']['leadContent'][i]['apiUrl'] + '?api-key=' + config['GUARDIAN_API_KEY']
    web_url = response.json()['response']['leadContent'][i]['webUrl']
    headline = response.json()['response']['leadContent'][i]['webTitle']
    date = response.json()['response']['leadContent'][i]['webPublicationDate']
    response_items.append({
        'api_url': api_url,
        'web_url': web_url,
        'headline': headline,
        'date': date
    })

