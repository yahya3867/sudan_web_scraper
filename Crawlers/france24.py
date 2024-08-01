from bs4 import BeautifulSoup
import requests
from datetime import datetime, date
import os
import itertools
from scraping_tools import store_articles, store_most_recent, store_article_analytics
from dotenv import load_dotenv
import sys
import html
import dateparser

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import time


load_dotenv()

DEPLOYMENT = os.getenv('DEPLOYMENT')
if len(sys.argv) > 1:
    if sys.argv[1] == 'initial':
        DEPLOYMENT = False

URL = f'https://www.france24.com/en/tag/sudan/'
SOURCE = 'France 24'
current_date = date.today()
target_date = date(2023,4,5)

# finds all the articles that relates to the Sudan war, war crimes, violence, etc
def scrape_articles():
    chrome_options = Options()
    chrome_options.add_argument('--ignore-certificate-errors')
    chrome_options.add_argument('--ignore-ssl-errors')
    chrome_options.add_argument('--headless')
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36")


    driver = webdriver.Chrome(options=chrome_options)
    driver.get('https://www.france24.com/en/tag/sudan/') 

    db_list = []
    try:
        driver.get(URL) 
        time.sleep(3)
        cookies = driver.find_element(By.ID, 'didomi-notice-agree-button')
        cookies.click()
        time.sleep(3)

        articles = driver.find_elements(By.CLASS_NAME, "article__infos")

        headlines = []
        urls = []
        dates = []

        for article in articles:            
            headlines.append(article.find_element(By.TAG_NAME,'h2').text.strip())
            
            urls.append(article.find_element(By.TAG_NAME,'a').get_attribute('href'))

            dt = article.find_element(By.TAG_NAME,'time').text.strip()
            dates.append(dt)

        img = []
        body_list = []

        for i in urls:
            time.sleep(2)
            new_driver = webdriver.Chrome(options=chrome_options)
            new_driver.get(i)

            time.sleep(3)
            try:
                cookies = new_driver.find_element(By.ID, 'didomi-notice-agree-button')
                cookies.click()
                time.sleep(3)
                try:
                    img.append(new_driver.find_element(By.TAG_NAME, 'main').find_elements(By.TAG_NAME,'img')[1].get_attribute('src'))
                except:
                    img.append('None')
                try:
                    body = new_driver.find_element(By.CLASS_NAME, "t-content__chapo").text
                except:
                    body = ''
                try:
                    container = new_driver.find_element(By.CSS_SELECTOR, "div.t-content__body.u-clearfix")
                    big_body = [i.text for i in container.find_elements(By.TAG_NAME, 'p')]
                    for i in range(0, len(big_body)):
                        body += big_body[i]
                        body += ' '  
                except:
                    pass
                body_list.append(body)

            except Exception as e:
                print(e)
                pass
            finally:
                new_driver.quit()
        for i in range(len(headlines)):
            db_data = {'source': SOURCE,
                    'headline': headlines[i],
                    'web_url': urls[i],
                    'date': dates[i],
                    'body': body_list[i],
                    'image_urls': img[i],
                    'archive_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            db_list.append(db_data)
    except Exception as e:
        print(e)
        pass
    finally:
        driver.quit()

    return db_list
def init_run():
    chrome_options = Options()
    chrome_options.add_argument('--ignore-certificate-errors')
    chrome_options.add_argument('--ignore-ssl-errors')
    chrome_options.add_argument('--headless')
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36")


    driver = webdriver.Chrome(options=chrome_options)
    driver.get('https://www.france24.com/en/tag/sudan/') 

    db_list = []
    try:
        last_date = current_date
        url = URL
        while target_date < last_date:

            driver.get(url) 
            time.sleep(3)
            try:
                cookies = driver.find_element(By.ID, 'didomi-notice-agree-button')
                cookies.click()
            except:
                pass
            time.sleep(3)

            articles = driver.find_elements(By.CLASS_NAME, "article__infos")

            headlines = []
            urls = []
            dates = []

            for article in articles:            
                headlines.append(article.find_element(By.TAG_NAME,'h2').text.strip())
                
                urls.append(article.find_element(By.TAG_NAME,'a').get_attribute('href'))

                dt = article.find_element(By.TAG_NAME,'time').text.strip()
                dates.append(dt)

            img = []
            body_list = []

            for i in urls:
                time.sleep(2)
                new_driver = webdriver.Chrome(options=chrome_options)
                new_driver.get(i)

                time.sleep(3)
                try:
                    cookies = new_driver.find_element(By.ID, 'didomi-notice-agree-button')
                    cookies.click()
                    time.sleep(3)
                    try:
                        img.append(new_driver.find_element(By.TAG_NAME, 'main').find_elements(By.TAG_NAME,'img')[1].get_attribute('src'))
                    except:
                        img.append('None')
                    try:
                        body = new_driver.find_element(By.CLASS_NAME, "t-content__chapo").text
                    except:
                        body = ''
                    try:
                        container = new_driver.find_element(By.CSS_SELECTOR, "div.t-content__body.u-clearfix")
                        big_body = [i.text for i in container.find_elements(By.TAG_NAME, 'p')]
                        for i in range(0, len(big_body)):
                            body += big_body[i]
                            body += ' '  
                    except:
                        pass
                    body_list.append(body)

                except Exception as e:
                    print(e)
                    pass
                finally:
                    new_driver.quit()
            for i in range(len(headlines)):
                db_data = {'source': SOURCE,
                        'headline': headlines[i],
                        'web_url': urls[i],
                        'date': dates[i],
                        'body': body_list[i],
                        'image_urls': img[i],
                        'archive_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                db_list.append(db_data)
            test_date = dates[-1]
            day = int(test_date[0:2])
            month = int(test_date[3:5])
            year = int(test_date[6:10])
            last_date = date(year, month, day)

            url = driver.find_element(By.CSS_SELECTOR, "a.m-pagination__item__link[href*='/en/tag/sudan/2/#pager']").get_attribute('href')
            time.sleep(3)
    except Exception as e:
        print(e)
        pass
    finally:
        driver.quit()

    return db_list

if __name__ == '__main__':
    articles = []
    print(f'Starting {SOURCE} crawler')

    if int(DEPLOYMENT):
        print('Running in deployment mode')
        articles = scrape_articles()
    else:
        articles = init_run()
    # Remove duplicates
    articles = list(k for k, _ in itertools.groupby(articles)) # Remove duplicates

    found_articles = store_most_recent([article for article in articles], SOURCE)
    articles = [article for article in articles if article not in found_articles]
    
    num_articles = len(articles)
    print(num_articles)

    if num_articles == 0:
        print('No new articles found')
        exit()

    # Now that we have our valid list of articles, we can start processing them
    for i in range(len(articles)):
        print('Processing:', articles[i]['headline'], f'{i + 1}/{num_articles}')

    db_articles = []

    for article in articles:
        db_articles.append(article)
    
    try:
        store_articles(db_articles) # Store articles in MongoDB
        store_article_analytics(len(articles), SOURCE) # Store article analytics
        print('Articles stored successfully')

    except Exception as e:
        print('Error storing articles:', e)
        exit()

