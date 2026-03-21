"""
scorer.py
Fetches 90-day price + volume data for each stock via yfinance.
Calculates:
  - RSI (14-day)
  - 20-day SMA vs current price
  - Volume: last day vs 10-day average (with actual numbers)
  - Final score (0-10) and BUY / HOLD / AVOID recommendation
  - One-line commentary explaining the call
PSX tickers use the .KA suffix on Yahoo Finance.
"""

import yfinance as yf


# ---------------------------------------------------------------------------
# RSI calculation (no external libs)
# ---------------------------------------------------------------------------
def _calc_rsi(closes: list[float], period: int = 14) -> float | None:
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, period + 1):
        diff = closes[i] - closes[i - 1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))

    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    for i in range(period + 1, len(closes)):
        diff = closes[i] - closes[i - 1]
        gain = max(diff, 0)
        loss = max(-diff, 0)
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period

    if avg_loss == 0:
        return 100.0
    rs  = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 1)


# ---------------------------------------------------------------------------
# Human-readable volume formatter
# ---------------------------------------------------------------------------
def _fmt_vol(v: float) -> str:
    if v >= 1_000_000:
        return f"{v / 1_000_000:.2f}M"
    if v >= 1_000:
        return f"{v / 1_000:.1f}K"
    return str(int(v))


# ---------------------------------------------------------------------------
# Main scorer
# ---------------------------------------------------------------------------
def get_technicals(ticker: str) -> dict:
    """
    Fetch 90 days of daily data for <ticker>.KA and compute technicals.
    Returns a dict with all computed fields, or an error dict if data unavailable.
    """
    symbol = f"{ticker}.KA"
    try:
        df = yf.download(symbol, period="90d", interval="1d",
                         progress=False, auto_adjust=True)

        if df.empty or len(df) < 20:
            return {"error": "Insufficient data"}

        closes  = df["Close"].dropna().values.flatten().tolist()
        volumes = df["Volume"].dropna().values.flatten().tolist()

        current_price = round(float(closes[-1]), 2)
        sma20         = round(sum(closes[-20:]) / 20, 2)
        rsi           = _calc_rsi(closes)

        # Volume: last session vs 10-day average
        last_vol    = float(volumes[-1])
        avg_vol_10  = sum(volumes[-11:-1]) / 10 if len(volumes) >= 11 else last_vol
        vol_diff    = last_vol - avg_vol_10
        vol_pct     = (vol_diff / avg_vol_10 * 100) if avg_vol_10 > 0 else 0
        vol_trend   = "Rising" if vol_diff > 0 else "Falling"

        return {
            "ticker":        ticker,
            "price":         current_price,
            "sma20":         sma20,
            "price_vs_sma":  "Above" if current_price >= sma20 else "Below",
            "rsi":           rsi,
            "last_volume":   _fmt_vol(last_vol),
            "avg_volume_10": _fmt_vol(avg_vol_10),
            "vol_diff":      f"+{_fmt_vol(abs(vol_diff))}" if vol_diff >= 0 else f"-{_fmt_vol(abs(vol_diff))}",
            "vol_pct":       f"{vol_pct:+.1f}%",
            "vol_trend":     vol_trend,
            "error":         None,
        }

    except Exception as e:
        return {"error": str(e)}


def score_signal(sentiment: str, confidence: str, tech: dict) -> tuple[float, str, str]:
    """
    Combine sentiment + technicals into a score (0-10) and BUY/HOLD/AVOID.
    Also returns a one-line commentary.
    """
    if tech.get("error"):
        # No price data — rely purely on sentiment
        if sentiment == "Bullish" and confidence == "High":
            return 5.0, "HOLD", "News is bullish but no price data available to confirm trend."
        elif sentiment == "Bearish":
            return 3.0, "AVOID", "Bearish news signal; price data unavailable for confirmation."
        return 4.0, "HOLD", "Insufficient data for a strong call — monitor closely."

    rsi           = tech["rsi"] or 50
    price_vs_sma  = tech["price_vs_sma"]
    vol_trend     = tech["vol_trend"]
    price         = tech["price"]
    sma20         = tech["sma20"]

    # Base score from sentiment
    score = {"Bullish": 5.0, "Neutral": 3.5, "Bearish": 2.0}.get(sentiment, 3.0)

    # Confidence modifier
    score += {"High": 1.0, "Medium": 0.5, "Low": 0.0}.get(confidence, 0)

    # RSI modifier  (ideal: 40-60 for bullish entry, penalise overbought/oversold)
    if rsi < 35:
        score += 1.5   # oversold — potential bounce
    elif rsi < 50:
        score += 1.0   # healthy room to run
    elif rsi < 65:
        score += 0.5   # moderate
    else:
        score -= 1.0   # overbought — risky entry

    # SMA modifier
    if price_vs_sma == "Above":
        score += 1.0
    else:
        score -= 0.5

    # Volume modifier
    if vol_trend == "Rising":
        score += 0.5
    else:
        score -= 0.25

    score = round(min(max(score, 0), 10), 1)

    # Recommendation thresholds
    if score >= 6.5 and sentiment != "Bearish":
        action = "BUY"
    elif score <= 3.5 or sentiment == "Bearish":
        action = "AVOID"
    else:
        action = "HOLD"

    # Commentary
    commentary = _generate_commentary(sentiment, rsi, price_vs_sma, vol_trend,
                                       price, sma20, score, action, tech)

    return score, action, commentary


def _generate_commentary(sentiment, rsi, price_vs_sma, vol_trend,
                          price, sma20, score, action, tech) -> str:
    """Build a concise one-sentence analyst-style commentary."""
    parts = []

    # Sentiment note
    if sentiment == "Bullish":
        parts.append("Positive news catalyst")
    elif sentiment == "Bearish":
        parts.append("Negative news headwind")
    else:
        parts.append("No strong news catalyst")

    # Price vs SMA
    diff_pct = abs(price - sma20) / sma20 * 100
    if price_vs_sma == "Above":
        parts.append(f"price is {diff_pct:.1f}% above its 20-day average (uptrend)")
    else:
        parts.append(f"price is {diff_pct:.1f}% below its 20-day average (downtrend)")

    # RSI note
    if rsi < 35:
        parts.append(f"RSI at {rsi} signals oversold territory — possible bounce")
    elif rsi > 65:
        parts.append(f"RSI at {rsi} is overbought — elevated risk of pullback")
    else:
        parts.append(f"RSI at {rsi} is healthy")

    # Volume note
    vol_pct = tech.get("vol_pct", "")
    parts.append(f"volume {vol_trend.lower()} ({vol_pct} vs 10-day avg)")

    return "; ".join(parts) + "."
