import functools
from datetime import datetime, timedelta
import re, smtplib
from email.message import EmailMessage

from flask import (
    Blueprint, current_app, flash, g, redirect, render_template, request,
    url_for
)
from flaskr.db import get_db
from flaskr.auth import login_required
import requests
from bs4 import BeautifulSoup

# -----------------------------------------------------------------------------
#  Blueprint
# -----------------------------------------------------------------------------

bp = Blueprint("scrape", __name__, url_prefix="/")

# -----------------------------------------------------------------------------
#  Scraping (1‑hour cache) – Veliko Širje excluded
# -----------------------------------------------------------------------------

_last_scrape_time: datetime | None = None  # UTC
_cached_data: list[dict] | None = None

STATION_ORDER = [
    "Laško",
    "Celje",
    "Medlog",
    "Letuš",
    "Nazarje",
    "Solčava",
]  # od iztoka proti izvoru

# -----------------------------------------------------------------------------
#  Helper: send e‑mail preko SMTP
# -----------------------------------------------------------------------------

def _send_email(recipients: list[str], subject: str, body: str) -> None:
    if not recipients:
        return

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = current_app.config.get("MAIL_SENDER", "alarm@savinja.si")
    msg["To"] = ", ".join(recipients)
    msg.set_content(body)

    host = current_app.config.get("MAIL_SERVER", "localhost")
    port = current_app.config.get("MAIL_PORT", 25)
    username = current_app.config.get("MAIL_USERNAME")
    password = current_app.config.get("MAIL_PASSWORD")
    use_tls = current_app.config.get("MAIL_USE_TLS", False)

    with smtplib.SMTP(host, port, timeout=10) as smtp:
        if use_tls:
            smtp.starttls()
        if username and password:
            smtp.login(username, password)
        smtp.send_message(msg)

# -----------------------------------------------------------------------------
#  Scrape helpers
# -----------------------------------------------------------------------------

def _do_real_scrape() -> list[dict]:
    """Fetch fresh Savinja data, skip Veliko Širje."""
    url = "https://www.arso.gov.si/vode/podatki/stanje_voda_samodejne.html"
    soup = BeautifulSoup(requests.get(url, timeout=10).content, "html.parser")
    table = soup.find("table", class_="online")
    data: list[dict] = []
    if not table:
        return data

    for tr in table.find_all("tr"):
        if tr.find("th"):
            continue
        tds = tr.find_all("td")
        if len(tds) < 6 or tds[0].text.strip() != "Savinja":
            continue

        loc = tds[1].text.strip()
        if loc == "Veliko Širje":
            continue

        data.append({
            "location":    loc,
            "water_level": tds[2].text.strip(),  # string cm
            "flow":        tds[3].text.strip(),
            "temperature": tds[5].text.strip(),
        })
    return data


def _refresh_cache():
    global _cached_data, _last_scrape_time
    _cached_data = _do_real_scrape()
    _last_scrape_time = datetime.utcnow()
    _check_and_notify(_cached_data)
    return _cached_data


def get_savinja_data() -> list[dict]:
    global _last_scrape_time, _cached_data
    now = datetime.utcnow()
    if _last_scrape_time is None or (now - _last_scrape_time) > timedelta(hours=1):
        _refresh_cache()
    return _cached_data or []

# -----------------------------------------------------------------------------
#  Danger detection + e‑mail
# -----------------------------------------------------------------------------

def _check_and_notify(data: list[dict]):
    if not data:
        return

    level_by = {d["location"]: int(d["water_level"].replace(",", "")) for d in data}
    db = get_db()

    users = db.execute(
        """
        SELECT u.id, GROUP_CONCAT(ae.email, ',') AS emails
        FROM user u JOIN alert_email ae ON ae.user_id = u.id
        GROUP BY u.id
        """
    ).fetchall()
    if not users:
        return

    danger_loc = None
    danger_level = None
    for loc in STATION_ORDER:
        if loc not in level_by:
            continue
        rows = db.execute(
            "SELECT threshold_cm FROM river_threshold WHERE location = ?",
            (loc,)
        ).fetchall()
        if not rows:
            continue
        max_thr = max(r["threshold_cm"] for r in rows)
        if level_by[loc] > max_thr:
            danger_loc = loc
            danger_level = level_by[loc]
            break

    if danger_loc is None:
        return

    subj = "NEVARNOST: visoka Savinja!"
    body = (
        f"NEVARNOST: višina reke Savinje v {danger_loc} je {danger_level} cm, "
        "kar presega nastavljene varne meje. Prosimo ukrepajte!"
    )

    for u in users:
        emails = u["emails"].split(",") if u["emails"] else []
        _send_email(emails, subj, body)

# -----------------------------------------------------------------------------
#  Email utilities
# -----------------------------------------------------------------------------

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def get_user_emails():
    db = get_db()
    return db.execute(
        "SELECT id, email FROM alert_email WHERE user_id = ? ORDER BY id",
        (g.user["id"],),
    ).fetchall()

# -----------------------------------------------------------------------------
#  ROUTES
# -----------------------------------------------------------------------------

@bp.route("/")
@login_required
def scrape():
    headlines = get_savinja_data()
    db = get_db()
    rows = db.execute(
        "SELECT location, threshold_cm FROM river_threshold WHERE user_id = ?",
        (g.user["id"],),
    ).fetchall()
    thresholds = {r["location"]: r["threshold_cm"] for r in rows}
    last_ts = _last_scrape_time.isoformat(" ", "seconds") if _last_scrape_time else None
    return render_template("scrape/scrape.html",
                           headlines=headlines,
                           thresholds=thresholds,
                           last_refresh=last_ts)

@bp.route("/refresh", methods=["POST"])
@login_required
def manual_refresh():
    _refresh_cache()
    flash("Podatki uspešno osveženi!", "success")
    return redirect(url_for("scrape.scrape"))

# ------------------------ Email management UI -------------------------------

@bp.route("/notify")
@login_required
def notify():
    return render_template("scrape/notify.html", emails=get_user_emails())

@bp.route("/add_email", methods=["POST"])
@login_required
def add_email():
    email = request.form.get("email", "").strip().lower()
    if not email:
        flash("Vnesi e‑poštni naslov.", "error")
        return redirect(url_for("scrape.notify"))
    if not EMAIL_RE.match(email):
        flash("E‑naslov ni veljaven.", "error")
        return redirect(url_for("scrape.notify"))

    db = get_db()
    try:
        db.execute("INSERT INTO alert_email (user_id, email) VALUES (?, ?)",
                   (g.user["id"], email))
        db.commit()
        flash("E‑naslov dodan!", "success")
    except db.IntegrityError:
        flash("Ta e‑naslov je že na seznamu.", "error")
    return redirect(url_for("scrape.notify"))

@bp.route("/delete_email/<int:email_id>", methods=["POST"])
@login_required
def delete_email(email_id: int):
    db = get_db()
    db.execute("DELETE FROM alert_email WHERE id = ? AND user_id = ?",
               (email_id, g.user["id"]))
    db.commit()
    flash("E‑naslov odstranjen.", "info")
    return redirect(url_for("scrape.notify"))
# ------------------------ Threshold endpoint (restored) ----------------------

@bp.route("/set_threshold", methods=["POST"])
@login_required
def set_threshold():
    location  = request.form.get("location")
    threshold = request.form.get("threshold")
    if not location or not threshold:
        flash("Manjka lokacija ali prag.", "error")
        return redirect(url_for("scrape.scrape"))

    db = get_db()
    db.execute(
        """INSERT INTO river_threshold (user_id, location, threshold_cm)
               VALUES (?, ?, ?)
               ON CONFLICT(user_id, location)
               DO UPDATE SET threshold_cm = excluded.threshold_cm""",
        (g.user["id"], location, threshold))
    db.commit()
    flash(f"Prag za {location} posodobljen!", "success")
    return redirect(url_for("scrape.scrape"))

