from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

import pandas as pd
import requests
from bs4 import BeautifulSoup
from dateutil import parser as date_parser

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}


@dataclass
class Listing:
    source: str
    title: str
    brand: str | None
    model_hint: str | None
    sold_price: float
    shipping: float
    total_price: float
    sold_at: datetime
    listing_url: str
    condition: str | None
    location: str | None


class ScrapeError(RuntimeError):
    """Raised when source pages could not be fetched or parsed."""


def _extract_price(text: str) -> float | None:
    filtered = "".join(ch for ch in text if ch.isdigit() or ch in ".,")
    if not filtered:
        return None
    try:
        return float(filtered.replace(",", ""))
    except ValueError:
        return None


def _normalize_brand(title: str) -> str | None:
    brands = [
        "Gibson",
        "Eastman",
        "Kentucky",
        "Collings",
        "Ibanez",
        "Loar",
        "Washburn",
        "Breedlove",
        "Fender",
    ]
    for brand in brands:
        if brand.lower() in title.lower():
            return brand
    return None


def _model_hint(title: str) -> str | None:
    tokens = title.replace("/", " ").split()
    alnum_tokens = [t for t in tokens if any(ch.isdigit() for ch in t) and len(t) >= 3]
    return alnum_tokens[0] if alnum_tokens else None


def _to_df(listings: Iterable[Listing]) -> pd.DataFrame:
    return pd.DataFrame([vars(item) for item in listings])


def fetch_ebay_sold(search_term: str = "mandolin", max_pages: int = 4) -> pd.DataFrame:
    """Scrape sold eBay listings (most recent first).

    This uses publicly accessible HTML pages and is intended for light personal use.
    """
    listings: list[Listing] = []
    for page in range(1, max_pages + 1):
        url = (
            "https://www.ebay.com/sch/i.html"
            f"?_nkw={search_term}&_sacat=0&LH_Sold=1&LH_Complete=1"
            "&_sop=10&_udlo=200&_udhi=1500"
            f"&_pgn={page}"
        )
        response = requests.get(url, headers=HEADERS, timeout=20)
        if response.status_code != 200:
            raise ScrapeError(f"eBay request failed: {response.status_code}")
        soup = BeautifulSoup(response.text, "lxml")
        cards = soup.select("li.s-item")
        if not cards:
            continue

        for card in cards:
            title_el = card.select_one("div.s-item__title")
            price_el = card.select_one("span.s-item__price")
            sold_el = card.select_one("span.POSITIVE")
            link_el = card.select_one("a.s-item__link")
            shipping_el = card.select_one("span.s-item__shipping")
            condition_el = card.select_one("span.SECONDARY_INFO")
            location_el = card.select_one("span.s-item__location")

            if not title_el or not price_el or not sold_el or not link_el:
                continue

            title = title_el.get_text(strip=True)
            sold_price = _extract_price(price_el.get_text(strip=True))
            if not sold_price:
                continue

            shipping = _extract_price(shipping_el.get_text(strip=True)) if shipping_el else 0.0
            sold_text = sold_el.get_text(strip=True).replace("Sold", "").strip()
            try:
                sold_at = date_parser.parse(sold_text)
            except (ValueError, TypeError):
                sold_at = datetime.now(timezone.utc)

            listings.append(
                Listing(
                    source="ebay",
                    title=title,
                    brand=_normalize_brand(title),
                    model_hint=_model_hint(title),
                    sold_price=float(sold_price),
                    shipping=float(shipping or 0),
                    total_price=float(sold_price + (shipping or 0)),
                    sold_at=sold_at,
                    listing_url=link_el.get("href", ""),
                    condition=condition_el.get_text(strip=True) if condition_el else None,
                    location=location_el.get_text(strip=True) if location_el else None,
                )
            )

    return _to_df(listings)


def fetch_reverb_recent(search_term: str = "mandolin", max_pages: int = 3) -> pd.DataFrame:
    """Scrape recently listed Reverb results as a proxy dataset.

    Reverb's sold-history data is not fully exposed without private endpoints, so this
    collector returns recent listings with prices that can be combined with eBay sold data.
    """
    listings: list[Listing] = []
    for page in range(1, max_pages + 1):
        url = (
            "https://reverb.com/marketplace"
            f"?query={search_term}&product_type=folk-instruments&sort=published_at%7Cdesc"
            f"&page={page}"
        )
        response = requests.get(url, headers=HEADERS, timeout=20)
        if response.status_code != 200:
            raise ScrapeError(f"Reverb request failed: {response.status_code}")
        soup = BeautifulSoup(response.text, "lxml")
        cards = soup.select("li[data-testid='listing-grid-card']")
        if not cards:
            cards = soup.select(".tile")

        for card in cards:
            title_el = card.select_one("[data-testid='listing-card-title'], .tile__title")
            price_el = card.select_one("[data-testid='listing-card-price'], .money")
            link_el = card.select_one("a[href*='/item/']")
            if not title_el or not price_el or not link_el:
                continue

            title = title_el.get_text(strip=True)
            sold_price = _extract_price(price_el.get_text(strip=True))
            if not sold_price:
                continue
            href = link_el.get("href", "")
            if href.startswith("/"):
                href = f"https://reverb.com{href}"

            listings.append(
                Listing(
                    source="reverb_ask",
                    title=title,
                    brand=_normalize_brand(title),
                    model_hint=_model_hint(title),
                    sold_price=float(sold_price),
                    shipping=0.0,
                    total_price=float(sold_price),
                    sold_at=datetime.now(timezone.utc),
                    listing_url=href,
                    condition=None,
                    location=None,
                )
            )

    return _to_df(listings)
