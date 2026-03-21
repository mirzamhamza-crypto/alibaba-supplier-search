"""
main.py  —  PSX Narrative Engine v3
Turns news into scored, dated, technically-backed stock signals.

Usage:  python main.py
Output: Console report + psx_signals_YYYYMMDD_HHMMSS.txt
"""

from datetime import datetime
from news_fetcher import get_all_headlines
from analyzer    import analyze_headlines, build_summary

DIVIDER = "=" * 65
BLOCK   = "-" * 65

ACTION_ICONS = {"BUY": "✅ BUY", "HOLD": "🟡 HOLD", "AVOID": "🔴 AVOID"}
SIGNAL_ICONS = {"Bullish": "📈 BULLISH", "Bearish": "📉 BEARISH", "Neutral": "➖ NEUTRAL"}
CONF_ICONS   = {"High": "🔴 HIGH", "Medium": "🟡 MEDIUM", "Low": "⚪ LOW"}


def format_signal(sig: dict) -> str:
    tech    = sig["technicals"]
    has_data = not tech.get("error")

    sectors = ", ".join(sig["sectors"])
    stocks  = ", ".join(sig["stocks"])
    action  = ACTION_ICONS.get(sig["action"], sig["action"])
    signal  = SIGNAL_ICONS.get(sig["signal"], sig["signal"])
    conf    = CONF_ICONS.get(sig["confidence"], sig["confidence"])
    age     = f"  ({sig['age_label']})" if sig["age_label"] else ""

    lines = [
        BLOCK,
        f"Headline   : {sig['headline']}",
        f"Published  : {sig['pub_date']}{age}",
        f"Source     : {sig['source']}",
        f"Sector(s)  : {sectors}",
        f"Stocks     : {stocks}",
        f"Signal     : {signal}",
        f"Confidence : {conf}",
    ]

    if has_data:
        t = tech
        lines += [
            f"",
            f"── Technicals ({t['ticker']}) ──────────────────────────",
            f"  Price      : PKR {t['price']}  |  SMA-20: PKR {t['sma20']}  ({t['price_vs_sma']} SMA)",
            f"  RSI-14     : {t['rsi']}",
            f"  Volume     : {t['last_volume']} today  |  10-day avg: {t['avg_volume_10']}  |  Change: {t['vol_diff']} ({t['vol_pct']})",
        ]
    else:
        lines.append(f"  Technicals : Unavailable ({tech.get('error', '—')})")

    lines += [
        f"",
        f"  Score      : {sig['score']} / 10",
        f"  Action     : {action}",
        f"",
        f"  💬 {sig['commentary']}",
        BLOCK,
    ]
    return "\n".join(lines)


def format_summary(summary: dict) -> str:
    top_sector  = summary["top_sector"]
    breakdown   = " | ".join(f"{k}: {v}" for k, v in summary["sector_breakdown"].items())
    bullish_str = ", ".join(f"{s}({c})" for s, c in summary["top_bullish"]) or "None"
    bearish_str = ", ".join(f"{s}({c})" for s, c in summary["top_bearish"]) or "None"

    lines = [
        "",
        DIVIDER,
        "  📊  FINAL MARKET SUMMARY",
        DIVIDER,
        f"  Signals analysed   : {summary['total_signals']}",
        f"  Top impacted sector: {top_sector[0]} ({top_sector[1]} mentions)",
        f"  Sector breakdown   : {breakdown}",
        "",
        f"  📈 Top bullish stocks : {bullish_str}",
        f"  📉 Top bearish stocks : {bearish_str}",
        "",
        "  ── TOP BUY RECOMMENDATIONS TODAY ──────────────────",
    ]

    if summary["top_buys"]:
        for i, (stock, score, headline) in enumerate(summary["top_buys"], 1):
            short_hl = headline[:50] + "..." if len(headline) > 50 else headline
            lines.append(f"  {i}. {stock:<8} Score: {score}/10  |  \"{short_hl}\"")
    else:
        lines.append("  No strong BUY signals today.")

    lines += ["", DIVIDER]
    return "\n".join(lines)


def save_report(signals, summary) -> str:
    ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"psx_signals_{ts}.txt"

    header = (
        f"{DIVIDER}\n"
        f"  PSX NARRATIVE ENGINE v3  —  Signal Report\n"
        f"  Generated : {datetime.now().strftime('%A, %d %B %Y  %H:%M:%S')}\n"
        f"{DIVIDER}\n\n"
    )

    body = "\n\n".join(format_signal(s) for s in signals)
    report = header + body + "\n" + format_summary(summary) + "\n"

    with open(filename, "w", encoding="utf-8") as f:
        f.write(report)
    return filename


def main():
    print(f"\n{DIVIDER}")
    print("  PSX NARRATIVE ENGINE v3")
    print("  News  +  Technicals  →  Stock Signals")
    print(f"{DIVIDER}\n")

    headlines = get_all_headlines()
    signals   = analyze_headlines(headlines)

    if not signals:
        print("  No signals found. Check connection or try again later.")
        return

    for sig in signals:
        print(format_signal(sig))
        print()

    summary = build_summary(signals)
    print(format_summary(summary))

    filename = save_report(signals, summary)
    print(f"\n  ✔  Report saved → {filename}\n")


if __name__ == "__main__":
    main()
