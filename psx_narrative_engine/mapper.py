"""
mapper.py - Maps news headlines to PSX sectors, stocks, and sentiment.

Sector mapping covers Oil & Gas, Banking, Fertilizer, Cement, and Power.
Sentiment is derived from keyword presence (bullish / bearish word lists).
"""


# ── Sector → keyword → stock mapping ────────────────────────────────────────

SECTOR_MAP = {
    "Oil & Gas": {
        "keywords": ["oil", "crude", "petroleum", "gas"],
        "stocks": ["OGDC", "PPL", "MARI", "PSO"],
    },
    "Banking": {
        "keywords": ["interest rate", "sbp", "policy rate", "bank"],
        "stocks": ["HBL", "UBL", "MCB", "ABL"],
    },
    "Fertilizer": {
        "keywords": ["fertilizer", "urea", "subsidy"],
        "stocks": ["ENGRO", "FFC", "FATIMA"],
    },
    "Cement": {
        "keywords": ["cement", "construction"],
        "stocks": ["LUCK", "DGKC", "PIOC"],
    },
    "Power": {
        "keywords": ["power", "circular debt", "tariff", "electricity"],
        "stocks": ["HUBC", "KAPCO"],
    },
}


# ── Sentiment word lists ─────────────────────────────────────────────────────

POSITIVE_WORDS = ["increase", "growth", "expansion", "approval", "record", "profit", "surge"]
NEGATIVE_WORDS = ["decline", "tax", "crisis", "shortage", "loss", "debt", "cut"]


def match_sectors(headline):
    """
    Scan a headline for sector keywords.
    Returns:
        sectors  - list of matched sector names
        stocks   - deduplicated list of associated stock tickers
        keyword_count - total number of keyword hits
    """
    headline_lower = headline.lower()
    sectors = []
    stocks = []
    keyword_count = 0

    for sector, info in SECTOR_MAP.items():
        for kw in info["keywords"]:
            if kw in headline_lower:
                keyword_count += 1
                if sector not in sectors:
                    sectors.append(sector)
                    stocks.extend(info["stocks"])

    # Remove duplicate stocks while preserving order
    seen = set()
    unique_stocks = []
    for s in stocks:
        if s not in seen:
            seen.add(s)
            unique_stocks.append(s)

    return sectors, unique_stocks, keyword_count


def detect_sentiment(headline):
    """
    Determine sentiment from positive / negative word counts.
    Returns:
        signal - "Bullish", "Bearish", or "Neutral"
        pos_count - number of positive words found
        neg_count - number of negative words found
    """
    headline_lower = headline.lower()

    pos_count = sum(1 for w in POSITIVE_WORDS if w in headline_lower)
    neg_count = sum(1 for w in NEGATIVE_WORDS if w in headline_lower)

    if pos_count > neg_count:
        return "Bullish", pos_count, neg_count
    elif neg_count > pos_count:
        return "Bearish", pos_count, neg_count
    else:
        return "Neutral", pos_count, neg_count
