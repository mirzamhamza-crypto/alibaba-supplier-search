"""
analyzer.py
Processes headlines into signals, then enriches each with technicals + scoring.
"""

from collections import Counter
from mapper  import find_sectors, get_stocks_for_sectors, get_sentiment
from scorer  import get_technicals, score_signal


def _confidence(kw_count: int, strength: int) -> str:
    if kw_count >= 2 and strength >= 2:
        return "High"
    elif kw_count >= 1 and strength >= 1:
        return "Medium"
    return "Low"


def analyze_headlines(headlines: list[dict]) -> list[dict]:
    """Detect sectors, sentiment, then fetch technicals and score each signal."""
    print("Analyzing headlines...\n")
    signals = []

    for item in headlines:
        headline = item["headline"]
        sectors, kw_count = find_sectors(headline)
        if not sectors:
            continue

        stocks     = get_stocks_for_sectors(sectors)
        sentiment, strength = get_sentiment(headline)
        confidence = _confidence(kw_count, strength)

        # Fetch technicals for the first (most representative) stock
        lead_stock = stocks[0] if stocks else None
        tech       = get_technicals(lead_stock) if lead_stock else {"error": "No stock"}

        score, action, commentary = score_signal(sentiment, confidence, tech)

        signals.append({
            "headline":    headline,
            "source":      item["source"],
            "pub_date":    item.get("pub_date", "Unknown date"),
            "age_label":   item.get("age_label", ""),
            "sectors":     sectors,
            "stocks":      stocks,
            "signal":      sentiment,
            "confidence":  confidence,
            "technicals":  tech,
            "score":       score,
            "action":      action,
            "commentary":  commentary,
        })
        status = f"✔ {lead_stock}: {action} ({score}/10)" if lead_stock else "✔ no stock"
        print(f"  {status}  |  {headline[:55]}...")

    print(f"\n  →  {len(signals)} signals scored\n")
    return signals


def build_summary(signals: list[dict]) -> dict:
    sector_counter  = Counter()
    bullish_counter = Counter()
    bearish_counter = Counter()
    buy_list        = []

    for sig in signals:
        for sector in sig["sectors"]:
            sector_counter[sector] += 1

        unique = list(dict.fromkeys(sig["stocks"]))
        if sig["signal"] == "Bullish":
            bullish_counter.update(unique)
        elif sig["signal"] == "Bearish":
            bearish_counter.update(unique)

        if sig["action"] == "BUY":
            buy_list.append((sig["stocks"][0], sig["score"], sig["headline"]))

    # Sort BUY list by score descending, top 3
    buy_list.sort(key=lambda x: x[1], reverse=True)

    return {
        "total_signals":    len(signals),
        "top_sector":       sector_counter.most_common(1)[0] if sector_counter else ("N/A", 0),
        "sector_breakdown": dict(sector_counter.most_common()),
        "top_bullish":      bullish_counter.most_common(5),
        "top_bearish":      bearish_counter.most_common(5),
        "top_buys":         buy_list[:3],
    }
