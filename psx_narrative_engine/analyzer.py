"""
analyzer.py - Analyzes headlines and produces trading signals with confidence scores.

For each headline:
  1. Detect matching sectors via keyword scan
  2. Map sectors to stock tickers
  3. Calculate sentiment (Bullish / Bearish / Neutral)
  4. Assign a confidence level (High / Medium / Low)

Also produces an aggregate summary:
  - Top impacted sector
  - Top 5 bullish stocks
  - Top 5 bearish stocks
"""

from collections import Counter
from mapper import match_sectors, detect_sentiment


def _confidence(keyword_count, signal, pos_count, neg_count):
    """
    Confidence heuristic:
      High   → multiple keywords AND strong sentiment (2+ sentiment words)
      Medium → at least one keyword AND some sentiment
      Low    → everything else (weak or no match)
    """
    sentiment_strength = pos_count + neg_count

    if keyword_count >= 2 and sentiment_strength >= 2 and signal != "Neutral":
        return "High"
    elif keyword_count >= 1 and signal != "Neutral":
        return "Medium"
    else:
        return "Low"


def analyze_headline(item):
    """
    Analyze a single headline dict and return a signal dict.
    Input:  {source, headline, link, published}
    Output: {headline, source, sectors, stocks, signal, confidence}
    """
    headline = item["headline"]
    source = item["source"]

    sectors, stocks, keyword_count = match_sectors(headline)
    signal, pos_count, neg_count = detect_sentiment(headline)
    conf = _confidence(keyword_count, signal, pos_count, neg_count)

    return {
        "headline": headline,
        "source": source,
        "sectors": sectors,
        "stocks": stocks,
        "signal": signal,
        "confidence": conf,
    }


def analyze_all(headlines):
    """
    Run analysis on every headline and return (signals, summary).
    signals: list of signal dicts
    summary: dict with top_sector, bullish_stocks, bearish_stocks
    """
    signals = [analyze_headline(item) for item in headlines]

    # ── Aggregate counters ───────────────────────────────────────────────
    sector_counter = Counter()
    bullish_counter = Counter()
    bearish_counter = Counter()

    for sig in signals:
        for sector in sig["sectors"]:
            sector_counter[sector] += 1

        # Count each stock once per headline (no duplicates within a signal)
        if sig["signal"] == "Bullish":
            for stock in sig["stocks"]:
                bullish_counter[stock] += 1
        elif sig["signal"] == "Bearish":
            for stock in sig["stocks"]:
                bearish_counter[stock] += 1

    # ── Build summary ────────────────────────────────────────────────────
    top_sector = sector_counter.most_common(1)[0][0] if sector_counter else "None"
    top_bullish = [s for s, _ in bullish_counter.most_common(5)]
    top_bearish = [s for s, _ in bearish_counter.most_common(5)]

    summary = {
        "top_sector": top_sector,
        "bullish_stocks": top_bullish,
        "bearish_stocks": top_bearish,
    }

    return signals, summary
