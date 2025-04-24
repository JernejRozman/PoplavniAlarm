import functools

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
from werkzeug.security import check_password_hash, generate_password_hash

from flaskr.db import get_db

bp = Blueprint('scrape', __name__, url_prefix='/scrape')



import requests
from bs4 import BeautifulSoup

def scrape_news():
    url = "https://www.arso.gov.si/vode/podatki/stanje_voda_samodejne.html"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")
    table = soup.find('table', class_='online')
    savinja_data = []
    
    if table:
        for row in table.find_all('tr'):
            # Skip header rows
            if row.find('th'):
                continue
            tds = row.find_all('td')
            if len(tds) >= 6:  # Ensure there are enough columns
                river = tds[0].get_text(strip=True)
                if river == 'Savinja':
                    savinja_data.append({
                        'river': river,
                        'location': tds[1].get_text(strip=True),
                        'water_level': tds[2].get_text(strip=True),
                        'flow': tds[3].get_text(strip=True),
                        'temperature': tds[5].get_text(strip=True)
                    })
    return savinja_data

@bp.route("")
def scrape():
    headlines = scrape_news()
    return render_template("auth/scrape.html", headlines=headlines)