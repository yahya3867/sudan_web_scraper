# Sudan Webscraper Project

## Description
This project is developed to scrape data from news websites related to the Sudanese Civil War. It aims to collect and analyze data for academic, research, and informational purposes. The scraper targets specific websites and extracts relevant information, facilitating easier access and processing of data.

## Notes
 - Contact me for .env.
 - When working locally, before initial run, ensure you are not pushing to db (we can test functionality with excel)

```python
articles = get_articles()

# Operate on dataframe
df = pd.DataFrame(articles)
df['date'] = pd.to_datetime(df['date'])
df.sort_values(by='date')
df['date'] = df['date'].dt.tz_localize(None) # Remove timezone info for excel compatibility

excel_writer = pd.ExcelWriter('News_Articles/guardian_articles.xlsx')
df.to_excel('News_Articles/guardian_articles.xlsx')

```


## Installation

### Requirements
- Python 3.11
- requirements.txt

### Setup
Clone the repository to your local machine:
```bash
git clone https://github.com/stccenter/sudan_web_scraper
cd sudan_web_scraper
conda env create -f environment.yml

```
You can then run the python program as you would any other.
