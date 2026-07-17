import json, os, re, smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
from bs4 import BeautifulSoup
URL="https://ikwilhuren.nu/aanbod/?sort=aanbodDESC"
MAX_PRICE=1500
TARGET_CITY="utrecht"
SMTP_SERVER="smtp.gmail.com"
SMTP_PORT=587
EMAIL_USER=os.environ["EMAIL_USER"]
EMAIL_PASSWORD=os.environ["EMAIL_PASSWORD"]
EMAIL_TO=os.environ["EMAIL_TO"]
HEADERS={"User-Agent":"Mozilla/5.0"}

def load_seen():
    try:
        with open('seen.json','r',encoding='utf-8') as f:
            return set(json.load(f))
    except Exception:
        return set()

def save_seen(data):
    with open('seen.json','w',encoding='utf-8') as f:
        json.dump(sorted(list(data)),f,indent=2)

def extract_price(text):
    text=text.replace('.','')
    m=re.search(r'€\s*(\d+)',text)
    return int(m.group(1)) if m else None

def send_email(matches):
    subject=f'New Utrecht Rental(s) <= €{MAX_PRICE}'
    html='<h2>New MVGM Rental Match</h2><ul>'
    for item in matches:
        html += f"<li><b>{item['title']}</b><br>Price: €{item['price']}<br><a href='{item['url']}'>Open Listing</a></li><br>"
    html+='</ul>'
    msg=MIMEMultipart(); msg['From']=EMAIL_USER; msg['To']=EMAIL_TO; msg['Subject']=subject
    msg.attach(MIMEText(html,'html'))
    with smtplib.SMTP(SMTP_SERVER,SMTP_PORT) as s:
        s.starttls(); s.login(EMAIL_USER,EMAIL_PASSWORD); s.send_message(msg)

def scrape():
    r=requests.get(URL,headers=HEADERS,timeout=30); r.raise_for_status()
    soup=BeautifulSoup(r.text,'lxml')
    matches=[]; processed=set()
    for a in soup.find_all('a',href=True):
        href=a['href']
        if '/object/' not in href: continue
        url=href if href.startswith('https://') else 'https://ikwilhuren.nu'+href
        if url in processed: continue
        processed.add(url)
        text=a.parent.get_text(' ',strip=True).lower()
        if TARGET_CITY not in text: continue
        price=extract_price(text)
        if price is None or price>MAX_PRICE: continue
        matches.append({'id':url,'url':url,'title':a.get_text(strip=True),'price':price})
    return matches

def main():
    seen=load_seen(); listings=scrape(); new=[]
    for l in listings:
        if l['id'] not in seen:
            new.append(l); seen.add(l['id'])
    if new: send_email(new)
    save_seen(seen)
    print(f'Listings found: {len(listings)} | New: {len(new)}')
if __name__=='__main__': main()
