"""
news_fetcher.py - Fetches and parses business news from Pakistani RSS feeds.

Sources:
  - Dawn Business & Finance
  - Business Recorder

Falls back to hardcoded sample headlines if feeds are unreachable.
"""

import xml.etree.ElementTree as ET
import urllib.request
import urllib.error
from datetime import datetime


# RSS feed URLs for Pakistani business news
FEEDS = {
    "Dawn": "https://www.dawn.com/feeds/business-finance",
    "Business Recorder": "https://www.brecorder.com/feeds/rss",
}

# Timeout in seconds for each feed request
REQUEST_TIMEOUT = 10


def _parse_rss(xml_text, source):
    """Parse RSS XML and return a list of headline dicts."""
    headlines = []
    root = ET.fromstring(xml_text)

    # RSS feeds keep items under <channel><item>
    for item in root.iter("item"):
        title_el = item.find("title")
        link_el = item.find("link")
        pub_el = item.find("pubDate")

        headline = title_el.text.strip() if title_el is not None and title_el.text else ""
        link = link_el.text.strip() if link_el is not None and link_el.text else ""
        published = pub_el.text.strip() if pub_el is not None and pub_el.text else ""

        if headline:
            headlines.append({
                "source": source,
                "headline": headline.lower(),  # normalize to lowercase
                "link": link,
                "published": published,
            })

    return headlines


def _fetch_feed(url, source):
    """Download a single RSS feed and return parsed headlines."""
    req = urllib.request.Request(url, headers={"User-Agent": "PSX-Narrative-Engine/1.0"})
    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
        xml_text = resp.read().decode("utf-8", errors="replace")
    return _parse_rss(xml_text, source)


def _sample_headlines():
    """Return 10 hardcoded sample headlines for offline / fallback use."""
    samples = [
        {"source": "Dawn", "headline": "oil prices surge amid global supply concerns",
         "link": "#", "published": "2025-01-15"},
        {"source": "Dawn", "headline": "sbp holds policy rate steady at 17 percent",
         "link": "#", "published": "2025-01-14"},
        {"source": "Business Recorder", "headline": "cement sector reports record growth in exports",
         "link": "#", "published": "2025-01-14"},
        {"source": "Dawn", "headline": "fertilizer subsidy approved by federal cabinet",
         "link": "#", "published": "2025-01-13"},
        {"source": "Business Recorder", "headline": "circular debt in power sector reaches new high",
         "link": "#", "published": "2025-01-13"},
        {"source": "Dawn", "headline": "bank profits decline amid rising tax burden",
         "link": "#", "published": "2025-01-12"},
        {"source": "Business Recorder", "headline": "crude oil production increases in balochistan",
         "link": "#", "published": "2025-01-12"},
        {"source": "Dawn", "headline": "construction boom drives demand for cement and steel",
         "link": "#", "published": "2025-01-11"},
        {"source": "Business Recorder", "headline": "electricity tariff hike sparks public outcry",
         "link": "#", "published": "2025-01-11"},
        {"source": "Dawn", "headline": "engro posts record profit in quarterly earnings",
         "link": "#", "published": "2025-01-10"},
    ]
    return samples


def fetch_news():
    """
    Fetch latest business headlines from all configured RSS feeds.
    Returns a list of dicts: {source, headline, link, published}.
    Falls back to sample headlines if all feeds fail.
    """
    all_headlines = []

    for source, url in FEEDS.items():
        try:
            headlines = _fetch_feed(url, source)
            all_headlines.extend(headlines)
            print(f"  [OK] {source}: {len(headlines)} headlines fetched")
        except (urllib.error.URLError, urllib.error.HTTPError, ET.ParseError, Exception) as e:
            print(f"  [WARN] {source} feed failed: {e}")

    # Fallback to sample data if no headlines were fetched
    if not all_headlines:
        print("  [INFO] Using hardcoded sample headlines as fallback")
        all_headlines = _sample_headlines()

    return all_headlines


if __name__ == "__main__":
    news = fetch_news()
    for item in news:
        print(f"[{item['source']}] {item['headline']}")
