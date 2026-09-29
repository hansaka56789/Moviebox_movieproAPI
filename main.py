#!/usr/bin/env python3
"""
TheMovieBox (themoviebox.xyz) Unofficial API scraper.
"""

import json
import re
import os
import sys
import hashlib
from datetime import datetime, timezone
import requests
from bs4 import BeautifulSoup

BASE = "https://themoviebox.xyz"  
PAGES = [
    ("", "home"),
    ("/discover", "discover"),
    ("/movies", "movies"),
]
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

def slugify(text: str) -> str:
    h = hashlib.md5(text.strip().lower().encode()).hexdigest()[:10]
    s = re.sub(r"[^a-z0-9]+", "-", text.strip().lower()).strip("-")
    return f"{s}-{h}" if s else h

def clean_image(src):
    if not src: return None
    src = src.split(" ")[0].strip()
    if src.startswith("//"): src = "https:" + src
    return src if src.startswith("http") else None

def parse_card_generic(soup):
    items = []
    
    for card in soup.select("a[href*='/movie/'], a[href*='/watch/'], div[class*='card'], div[class*='movie']"):
        title_el = card.select_one("h3, h2, [class*='title']")
        if not title_el: continue
        title = title_el.get_text(strip=True)
        if len(title) < 2: continue

        img = card.select_one("img")
        poster = clean_image(img.get("src") or img.get("data-src") if img else None)

        href = card.get("href") or (card.select_one("a").get("href") if card.select_one("a") else None)
        if href and href.startswith("/"): href = BASE + href

        items.append({
            "id": slugify(title),
            "title": title,
            "title_clean": title,
            "poster": poster,
            "url": href,
            "genres": [],
        })
    return items

def scrape_page(path: str, section: str):
    url = f"{BASE}/{path}".rstrip("/")
    if url == BASE + "/": url = BASE
    print(f"[*] Fetching {url}")
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    items = parse_card_generic(soup)
    # dedupe
    seen = set()
    uniq = []
    for it in items:
        if it["id"] not in seen:
            seen.add(it["id"])
            it["section"] = section
            uniq.append(it)
    print(f" -> {len(uniq)} items")
    return uniq

def scrape_all():
    items, seen = [], set()
    for path, section in PAGES:
        try:
            for card in scrape_page(path, section):
                if card["id"] not in seen:
                    seen.add(card["id"])
                    items.append(card)
        except Exception as e:
            print(f"[!] {path} failed: {e}")
    return items

def main():
    items = scrape_all()
    data = {
        "success": True,
        "source": BASE,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total": len(items),
        "results": items,
    }
    os.makedirs("output", exist_ok=True)
    with open("output/api.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[+] Wrote {data['total']} items -> output/api.json")

if __name__ == "__main__":
    main()
