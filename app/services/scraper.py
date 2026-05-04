"""
PinFlow AI — Amazon Scraper Service
Extracts product title, price, and images from Amazon product pages.
"""

import re
import requests
from bs4 import BeautifulSoup


# Realistic browser headers to avoid bot detection
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


def get_product_data(link: str) -> dict:
    """
    Scrape an Amazon product URL and return title, price, and hero image.

    Returns a safe fallback dict on any failure so callers never crash.
    """
    try:
        resp = requests.get(link, headers=_HEADERS, timeout=14)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, "html.parser")

        title = _extract_title(soup)
        price = _extract_price(soup)
        image = _extract_image(soup)

        return {"title": title, "price": price, "image": image}

    except Exception as exc:
        print(f"[scraper] Error fetching {link}: {exc}")
        return {"title": "Trending Product", "price": "N/A", "image": None}


def _extract_title(soup: BeautifulSoup) -> str:
    el = soup.find(id="productTitle")
    return el.get_text(strip=True) if el else "Trending Product"


def _extract_price(soup: BeautifulSoup) -> str:
    # Try multiple selectors Amazon uses for price
    for selector in [
        {"class": "a-offscreen"},
        {"id": "priceblock_ourprice"},
        {"id": "priceblock_dealprice"},
        {"class": "a-price-whole"},
    ]:
        el = soup.find("span", selector)
        if el:
            price_text = el.get_text(strip=True)
            if price_text:
                return price_text
    return "N/A"


def _extract_image(soup: BeautifulSoup) -> str | None:
    img_el = soup.find(id="landingImage")
    if not img_el:
        img_el = soup.find(id="imgBlkFront")
    if not img_el:
        return None

    # Prefer the higher-resolution data attribute
    for attr in ("data-old-hires", "data-src", "src"):
        val = img_el.get(attr)
        if val and val.startswith("http"):
            return val

    return None


def get_lifestyle_images(keywords: list[str]) -> list[str]:
    """
    Return placeholder lifestyle images based on product keywords.
    In production, replace with a real stock-photo API (Unsplash, Pexels, etc.).
    """
    seeds = [abs(hash(k)) % 1000 for k in keywords[:4]] or [42, 73, 99, 11]
    images = []
    for i, seed in enumerate(seeds * 3):
        images.append(f"https://picsum.photos/seed/{seed + i * 7}/600/800")
    return images[:9]


def extract_keywords(title: str) -> list[str]:
    """Pull meaningful words (4+ chars) from a product title."""
    return re.findall(r"[A-Za-z]{4,}", title)[:8]
