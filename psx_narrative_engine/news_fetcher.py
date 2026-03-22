"""
news_fetcher.py
Fetches RSS headlines from Dawn and Business Recorder.
- Parses and displays publish date per headline
- Filters out headlines older than MAX_AGE_DAYS (default 7)
- Flags headlines as FRESH (today/yesterday) or OLDER
"""

import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

MAX_AGE_DAYS = 7   # discard anything older than this

RSS_FEEDS = {
    "Dawn Business":     "https://www.dawn.com/feeds/business-finance",
    "Business Recorder": "https://www.brecorder.com/feeds/rss",
}

SAMPLE_HEADLINES = [
    {"source": "Sample", "headline": "sbp holds policy rate steady at 17 percent",                    "link": "", "published": "Fri, 21 Mar 2026 08:00:00 +0500", "pub_date": "2026-03-21", "age_label": "Today"},
    {"source": "Sample", "headline": "oil prices surge amid global supply concerns",                   "link": "", "published": "Fri, 21 Mar 2026 07:30:00 +0500", "pub_date": "2026-03-21", "age_label": "Today"},
    {"source": "Sample", "headline": "cement sector reports record growth in exports",                  "link": "", "published": "Thu, 20 Mar 2026 09:00:00 +0500", "pub_date": "2026-03-20", "age_label": "Yesterday"},
    {"source": "Sample", "headline": "fertilizer subsidy approved by federal cabinet",                 "link": "", "published": "Thu, 20 Mar 2026 10:00:00 +0500", "pub_date": "2026-03-20", "age_label": "Yesterday"},
    {"source": "Sample", "headline": "circular debt in power sector reaches new high",                 "link": "", "published": "Wed, 19 Mar 2026 08:45:00 +0500", "pub_date": "2026-03-19", "age_label": "2 days ago"},
    {"source": "Sample", "headline": "bank profits decline amid rising tax burden",                    "link": "", "published": "Wed, 19 Mar 2026 11:00:00 +0500", "pub_date": "2026-03-19", "age_label": "2 days ago"},
    {"source": "Sample", "headline": "crude oil production increases in balochistan",                  "link": "", "published": "Tue, 18 Mar 2026 09:00:00 +0500", "pub_date": "2026-03-18", "age_label": "3 days ago"},
    {"source": "Sample", "headline": "construction boom drives demand for cement and steel",           "link": "", "published": "Mon, 17 Mar 2026 08:00:00 +0500", "pub_date": "2026-03-17", "age_label": "4 days ago"},
    {"source": "Sample", "headline": "electricity tariff hike sparks public outcry",                  "link": "", "published": "Sun, 16 Mar 2026 10:00:00 +0500", "pub_date": "2026-03-16", "age_label": "5 days ago"},
    {"source": "Sample", "headline": "engro posts record profit in quarterly earnings",                "link": "", "published": "Sat, 15 Mar 2026 09:00:00 +0500", "pub_date": "2026-03-15", "age_label": "6 days ago"},
]


def _parse_date(pub_str: str) -> tuple[datetime | None, str, str]:
    """
    Parse RSS pubDate string into a datetime object.
    Returns: (datetime_obj, formatted_date_str, age_label)
    """
    if not pub_str:
        return None, "Unknown date", "Unknown"

    try:
        dt = parsedate_to_datetime(pub_str)
        dt_utc = dt.astimezone(timezone.utc)
        now_utc = datetime.now(timezone.utc)
        delta   = now_utc - dt_utc

        formatted = dt.strftime("%d %b %Y, %I:%M %p")

        if delta.days == 0:
            age_label = "Today"
        elif delta.days == 1:
            age_label = "Yesterday"
        elif delta.days <= MAX_AGE_DAYS:
            age_label = f"{delta.days} days ago"
        else:
            age_label = f"STALE ({delta.days}d old)"

        return dt_utc, formatted, age_label

    except Exception:
        return None, pub_str[:30], "Unknown"


def fetch_feed(name: str, url: str) -> list[dict]:
    """Fetch, parse, and age-filter a single RSS feed."""
    headlines = []
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            xml_data = resp.read()

        root  = ET.fromstring(xml_data)
        items = root.findall(".//item")
        now   = datetime.now(timezone.utc)
        skipped = 0

        for item in items[:30]:
            title   = item.findtext("title",   "").strip()
            link    = item.findtext("link",    "").strip()
            pub_raw = item.findtext("pubDate", "").strip()

            if not title:
                continue

            dt_obj, formatted, age_label = _parse_date(pub_raw)

            # Skip headlines older than MAX_AGE_DAYS
            if dt_obj and (now - dt_obj).days > MAX_AGE_DAYS:
                skipped += 1
                continue

            headlines.append({
                "source":    name,
                "headline":  title.lower(),
                "link":      link,
                "published": pub_raw,
                "pub_date":  formatted,
                "age_label": age_label,
            })

        print(f"  ✔  {name}: {len(headlines)} headlines (skipped {skipped} older than {MAX_AGE_DAYS}d)")

    except Exception as e:
        print(f"  ✘  {name}: feed unavailable ({e})")

    return headlines


def get_all_headlines() -> list[dict]:
    """Fetch from all feeds. Fall back to sample data if both fail."""
    print("Fetching news...\n")
    all_headlines = []

    for name, url in RSS_FEEDS.items():
        all_headlines.extend(fetch_feed(name, url))

    if not all_headlines:
        print("  ⚠  Live feeds unavailable — using sample headlines.\n")
        return SAMPLE_HEADLINES

    print(f"\n  →  {len(all_headlines)} recent headlines collected\n")
    return all_headlines
