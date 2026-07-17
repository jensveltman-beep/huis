import json
import os
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import requests
from bs4 import BeautifulSoup

URL = "https://ikwilhuren.nu/aanbod/?sort=aanbodDESC"

MAX_PRICE = 1500
TARGET_CITY = "utrecht"

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

EMAIL_USER = os.environ["EMAIL_USER"]
EMAIL_PASSWORD = os.environ["EMAIL_PASSWORD"]
EMAIL_TO = os.environ["EMAIL_TO"]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/138.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "nl-NL,nl;q=0.9,en;q=0.8",
    "Referer": "https://www.google.com/",
    "Connection": "keep-alive",
}


def load_seen():
    try:
        with open("seen.json", "r", encoding="utf-8") as f:
            return set(json.load(f))
    except Exception:
        return set()


def save_seen(data):
    with open("seen.json", "w", encoding="utf-8") as f:
        json.dump(sorted(list(data)), f, indent=2)


def extract_price(text):
    text = text.replace(".", "")
    match = re.search(r"€\s*(\d+)", text)

    if not match:
        return None

    return int(match.group(1))


def send_email(matches):
    subject = f"New Utrecht Rental(s) <= €{MAX_PRICE}"

    html = """
    <h2>New MVGM Rental Match</h2>
    <ul>
    """

    for item in matches:
        html += f"""
        <li>
            <b>{item['title']}</b><br>
            Price: €{item['price']}<br>
            Link: {item['url']}{item['url']}</a>
        </li>
        <br>
        """

    html += "</ul>"

    msg = MIMEMultipart()
    msg["From"] = EMAIL_USER
    msg["To"] = EMAIL_TO
    msg["Subject"] = subject

    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        server.send_message(msg)


def scrape():
    session = requests.Session()

    response = session.get(
        URL,
        headers=HEADERS,
        timeout=30,
        allow_redirects=True,
    )

    print("Status code:", response.status_code)
    print("Response URL:", response.url)
    print("First 500 chars:")
    print(response.text[:500])

    response.raise_for_status()

    soup = BeautifulSoup(response.text, "lxml")

    listings = []
    processed = set()

    for anchor in soup.find_all("a", href=True):
        href = anchor["href"]

        if "/object/" not in href:
            continue

        if href.startswith("https://"):
            url = href
        else:
            url = "https://ikwilhuren.nu" + href

        if url in processed:
            continue

        processed.add(url)

        text = anchor.parent.get_text(" ", strip=True).lower()

        if TARGET_CITY not in text:
            continue

        price = extract_price(text)

        if price is None:
            continue

        if price > MAX_PRICE:
            continue

        listings.append(
            {
                "id": url,
                "url": url,
                "title": anchor.get_text(strip=True),
                "price": price,
            }
        )

    return listings


def main():
    seen = load_seen()

    listings = scrape()

    new_matches = []

    for listing in listings:
        if listing["id"] not in seen:
            new_matches.append(listing)
            seen.add(listing["id"])

    if new_matches:
        send_email(new_matches)

    save_seen(seen)

    print(f"Listings found: {len(listings)}")
    print(f"New listings: {len(new_matches)}")


if __name__ == "__main__":
    main()
