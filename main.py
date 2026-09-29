#!/usr/bin/env python3

import json
import re
import os
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
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def slugify(text: str) -> str:
    text = text.strip().lower()

    h = hashlib.md5(text.encode()).hexdigest()[:10]

    s = re.sub(r"[^a-z0-9]+", "-", text).strip("-")

    return f"{s}-{h}" if s else h


def clean_image(src):
    if not src:
        return None

    src = src.split(" ")[0].strip()

    if src.startswith("//"):
        src = "https:" + src

    if src.startswith("http"):
        return src

    return None


def extract_year(card):
    text = card.get_text(" ", strip=True)

    match = re.search(r"\b(19\d{2}|20\d{2})\b", text)

    return int(match.group(1)) if match else None


def parse_card_generic(soup):
    items = []
    seen = set()

    selectors = [
        "a[href*='/movie/']",
        "a[href*='/watch/']",
        "div[class*='card']",
        "div[class*='movie']",
    ]

    for selector in selectors:
        for card in soup.select(selector):

            title_el = card.select_one(
                "h1, h2, h3, h4, "
                "[class*='title'], "
                "[class*='name']"
            )

            if not title_el:
                continue

            title = title_el.get_text(" ", strip=True)

            if len(title) < 2:
                continue

            img = card.select_one("img")

            poster = None

            if img:
                poster = clean_image(
                    img.get("src")
                    or img.get("data-src")
                    or img.get("data-lazy-src")
                )

            href = None

            if card.name == "a":
                href = card.get("href")
            else:
                link = card.select_one("a[href]")
                if link:
                    href = link.get("href")

            if href and href.startswith("/"):
                href = BASE + href

            movie_id = slugify(title)

            # Duplicate protection
            if movie_id in seen:
                continue

            seen.add(movie_id)

            year = extract_year(card)

            movie_data = {
                "id": movie_id,
                "title": title,
                "image": poster,
                "year": year,

                # Official page URL only
                "page_url": href,

                # Metadata
                "quality": [
                    "360p",
                    "720p",
                    "1080p"
                ],
            }

            items.append(movie_data)

    return items


def scrape_page(path: str, section: str):

    url = f"{BASE}/{path}".rstrip("/")

    if url == BASE + "/":
        url = BASE

    print(f"[*] Fetching {url}")

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=30
    )

    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    items = parse_card_generic(soup)

    seen = set()
    unique = []

    for item in items:

        if item["id"] in seen:
            continue

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

            page_items = scrape_page(
                path,
                section
            )

            for item in page_items:

                if item["id"] in seen:
                    continue

                seen.add(item["id"])

                items.append(item)

        except Exception as e:

            print(
                f"[!] {path} failed: {e}"
            )

    return items


def main():

    items = scrape_all()

    data = {
        "success": True,
        "source": BASE,
        "generated_at": (
            datetime.now(timezone.utc)
            .isoformat()
        ),
        "total": len(items),
        "results": items,
    }

    os.makedirs(
        "output",
        exist_ok=True
    )

    output_file = "output/api.json"

    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )

    print(
        f"[+] Wrote "
        f"{data['total']} items -> "
        f"{output_file}"
    )


if __name__ == "__main__":
    main()
