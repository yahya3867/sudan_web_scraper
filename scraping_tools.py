from bs4 import BeautifulSoup

# Parses articles and returns raw text.
def parse_articles(articles):
    for article in articles:
        html = article['body']
        soup = BeautifulSoup(html, features='html.parser')

        # Get text
        text = soup.get_text()
        raw_text = text.encode('ascii', 'ignore').decode('ascii')
        article['body'] = raw_text

    return articles
