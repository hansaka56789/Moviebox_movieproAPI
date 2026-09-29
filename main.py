#!/usr/bin/env python3
import json
import re
import os
import hashlib
from datetime import datetime, timezone
import requests
from bs4 import BeautifulSoup

BASE = "https://themoviebox.xyz"
PAGES = [("", "home"), ("/discover", "discover"), ("/movies", "movies")]
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

def slugify(text: str) -> str:
    text = text.strip().lower()
    h = hashlib.md5(text.encode()).hexdigest()[:10]
    s = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return f"{s}-{h}" if s else h

def clean_image(src):
    if not src: return None
    src = src.split(" ")[0].strip()
    if src.startswith("//"): src = "https:" + src
    return src if src.startswith("http") else None

def extract_year(card):
    text = card.get_text(" ", strip=True)
    match = re.search(r"\b(19\d{2}|20\d{2})\b", text)
    return int(match.group(1)) if match else None

def parse_card_generic(soup):
    items = []
    seen = set()
    selectors = ["a[href*='/movie/']", "a[href*='/watch/']", "div[class*='card']", "div[class*='movie']"]
    for selector in selectors:
        for card in soup.select(selector):
            title_el = card.select_one("h1, h2, h3, h4, [class*='title'], [class*='name']")
            if not title_el: continue
            title = title_el.get_text(" ", strip=True)
            if len(title) < 2: continue

            img = card.select_one("img")
            poster = None
            if img:
                poster = clean_image(img.get("src") or img.get("data-src") or img.get("data-lazy-src"))

            href = card.get("href") if card.name == "a" else (card.select_one("a[href]").get("href") if card.select_one("a[href]") else None)
            if href and href.startswith("/"): href = BASE + href

            movie_id = slugify(title)
            if movie_id in seen: continue
            seen.add(movie_id)

            movie_data = {
                "id": movie_id,
                "title": title,
                "image": poster, # poster එක
                "year": extract_year(card),
                "page_url": href, # legal page url විතරයි
                "quality": ["360p", "720p", "1080p"]
            }
            items.append(movie_data)
    return items

def scrape_page(path: str, section: str):
    url = f"{BASE}/{path}".rstrip("/")
    if url == BASE + "/": url = BASE
    print(f"[*] Fetching {url}")
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    items = parse_card_generic(soup)
    seen = set()
    unique = []
    for item in items:
        if item["id"] not in seen:
            seen.add(item["id"])
            item["section"] = section
            unique.append(item)
    print(f" -> {len(unique)} items")
    return unique

def scrape_all():
    items = []
    seen = set()
    for path, section in PAGES:
        try:
            for item in scrape_page(path, section):
                if item["id"] not in seen:
                    seen.add(item["id"])
                    items.append(item)
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
