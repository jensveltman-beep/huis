import json
import os
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import requests
from bs4 import BeautifulSoup

MAX_PRICE = 1500
TARGET_CITY = "utrecht"
MAX_PAGES = 15

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


def send_email(matches):
    subject = f"🏠 New Utrecht Rental(s) under €{MAX_PRICE}"

    html = "<h2>New MVGM Rental Match</h2><ul>"

    for item in matches:
        html += (
            f"<li>"
            f"<strong>{item['title']}</strong><br>"
            f"Price: €{item['price']}<br>"
            f"URL: {item['url']}"
            f"</li><br>"
        )

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

    listings = []
    processed = set()

    for page in range(1, MAX_PAGES + 1):

        page_url = (
            f"https://ikwilhuren.nu/aanbod/"
            f"?page={page}&sort=aanbodDESC"
        )

        print(f"Checking page {page}")

        response = session.get(
            page_url,
            headers=HEADERS,
            timeout=30,
        )

        response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")

        page_matches = 0

        for link in soup.select('a[href*="/object/"]'):

            href = link.get("href", "").strip()

            if not href:
                continue

            if href.startswith("/"):
                url = "https://ikwilhuren.nu" + href
            elif href.startswith("http"):
                url = href
            else:
                continue

            if url in processed:
                continue

            processed.add(url)

            card = link.find_parent("div", class_="card-body")

            if not card:
                continue

            card_text = card.get_text(" ", strip=True)

            if TARGET_CITY not in card_text.lower():
                continue

            price_match = re.search(r"€\s*([\d\.]+)", card_text)

            if not price_match:
                continue

            try:
                price = int(
                    price_match.group(1)
                    .replace(".", "")
                )
            except ValueError:
                continue

            if price > MAX_PRICE:
                continue

            listing = {
                "id": url,
                "url": url,
                "title": link.get_text(strip=True),
                "price": price,
            }

            listings.append(listing)
            page_matches += 1

        print(
            f"Page {page}: {page_matches} matching properties"
        )

    print(f"\nTotal matches found: {len(listings)}")

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
        print(f"Sending email for {len(new_matches)} new listing(s)")
        send_email(new_matches)
    else:
        print("No new listings found. No email sent.")

    save_seen(seen)

    print(f"Listings found: {len(listings)}")
    print(f"New listings: {len(new_matches)}")


if __name__ == "__main__":
    main()
