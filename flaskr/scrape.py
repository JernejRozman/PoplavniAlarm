import requests
from bs4 import BeautifulSoup
def scrape_news():
    url = "https://webscraper.io/test-sites/e-commerce/allinone"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")
    headlines = []
    for headline in soup.find_all("h3", class_="headline"):
        headlines.append(headline.text)
    return headlines

