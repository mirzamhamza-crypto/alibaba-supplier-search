"""
mapper.py
Keyword → sector → stock mappings + sentiment rules.
"""

SECTOR_KEYWORDS: dict[str, list[str]] = {
    "Oil & Gas":  ["oil", "crude", "petroleum", "gas"],
    "Banking":    ["interest rate", "sbp", "policy rate", "bank"],
    "Fertilizer": ["fertilizer", "urea", "subsidy"],
    "Cement":     ["cement", "construction"],
    "Power":      ["power", "circular debt", "tariff", "electricity"],
}

SECTOR_STOCKS: dict[str, list[str]] = {
    "Oil & Gas":  ["OGDC", "PPL", "MARI", "PSO"],
    "Banking":    ["HBL", "UBL", "MCB", "ABL"],
    "Fertilizer": ["ENGRO", "FFC", "FATIMA"],
    "Cement":     ["LUCK", "DGKC", "PIOC"],
    "Power":      ["HUBC", "KAPCO"],
}

POSITIVE_WORDS = ["increase", "growth", "expansion", "approval", "record", "profit", "surge"]
NEGATIVE_WORDS = ["decline", "tax", "crisis", "shortage", "loss", "debt", "cut"]


def find_sectors(headline: str) -> tuple[list[str], int]:
    matched, total = [], 0
    for sector, keywords in SECTOR_KEYWORDS.items():
        hits = sum(1 for kw in keywords if kw in headline)
        if hits:
            matched.append(sector)
            total += hits
    return matched, total


def get_stocks_for_sectors(sectors: list[str]) -> list[str]:
    stocks = []
    for sector in sectors:
        for s in SECTOR_STOCKS.get(sector, []):
            if s not in stocks:
                stocks.append(s)
    return stocks


def get_sentiment(headline: str) -> tuple[str, int]:
    pos = sum(1 for w in POSITIVE_WORDS if w in headline)
    neg = sum(1 for w in NEGATIVE_WORDS if w in headline)
    strength = abs(pos - neg)
    if pos > neg:
        return "Bullish", strength
    elif neg > pos:
        return "Bearish", strength
    return "Neutral", 0
