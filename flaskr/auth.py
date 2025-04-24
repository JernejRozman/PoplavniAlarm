import functools

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
from werkzeug.security import check_password_hash, generate_password_hash

from flaskr.db import get_db

### Zato, da se po 1 uri ponovno izvede scrape
from datetime import datetime, timedelta

last_scrape_time = None


bp = Blueprint('auth', __name__, url_prefix='/auth')


@bp.route('/register', methods=('GET', 'POST'))
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        error = None

        if not username:
            error = 'Username is required.'
        elif not password:
            error = 'Password is required.'

        if error is None:
            try:
                db.execute(
                    "INSERT INTO user (username, password) VALUES (?, ?)",
                    (username, generate_password_hash(password)),
                )
                db.commit()
            except db.IntegrityError:
                error = f"User {username} is already registered."
            else:
                return redirect(url_for("auth.login"))

        flash(error)

    return render_template('auth/register.html')

@bp.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        error = None
        user = db.execute(
            'SELECT * FROM user WHERE username = ?', (username,)
        ).fetchone()

        if user is None:
            error = 'Incorrect username.'
        elif not check_password_hash(user['password'], password):
            error = 'Incorrect password.'

        if error is None:
            session.clear()
            session['user_id'] = user['id']
            return redirect(url_for('index'))

        flash(error)

    return render_template('auth/login.html')

@bp.before_app_request
def load_logged_in_user():
    user_id = session.get('user_id')

    if user_id is None:
        g.user = None
    else:
        g.user = get_db().execute(
            'SELECT * FROM user WHERE id = ?', (user_id,)
        ).fetchone()


@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for('auth.login'))

        return view(**kwargs)

    return wrapped_view


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
                    })
    return savinja_data

@bp.route("/scrape")
def scrape():
    headlines = scrape_news()
    return render_template("auth/scrape.html", headlines=headlines)


@bp.route("/notify")
def notify():
    return render_template("auth/notify.html")