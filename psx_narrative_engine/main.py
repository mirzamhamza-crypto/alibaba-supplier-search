"""
main.py - PSX Narrative Engine entry point.

Workflow:
  1. Fetch news headlines from Pakistani business RSS feeds
  2. Analyze each headline for sector, stock, and sentiment signals
  3. Print a formatted report to the console
  4. Save the full report to psx_signals_YYYYMMDD_HHMMSS.txt
"""

import os
import sys
from datetime import datetime

# Ensure the package directory is on the path so imports work
# when running as `python main.py` from inside the folder.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from news_fetcher import fetch_news
from analyzer import analyze_all


SEPARATOR = "-" * 50


def format_signal(sig):
    """Format a single signal dict into a readable block."""
    sectors_str = ", ".join(sig["sectors"]) if sig["sectors"] else "N/A"
    stocks_str = ", ".join(sig["stocks"]) if sig["stocks"] else "N/A"

    return (
        f"{SEPARATOR}\n"
        f"Headline   : {sig['headline']}\n"
        f"Source     : {sig['source']}\n"
        f"Sector(s)  : {sectors_str}\n"
        f"Stocks     : {stocks_str}\n"
        f"Signal     : {sig['signal'].upper()}\n"
        f"Confidence : {sig['confidence'].upper()}\n"
        f"{SEPARATOR}"
    )


def format_summary(summary):
    """Format the aggregate summary section."""
    bullish = ", ".join(summary["bullish_stocks"]) if summary["bullish_stocks"] else "None"
    bearish = ", ".join(summary["bearish_stocks"]) if summary["bearish_stocks"] else "None"

    return (
        f"\n{'=' * 50}\n"
        f"             MARKET SIGNAL SUMMARY\n"
        f"{'=' * 50}\n"
        f"Top impacted sector : {summary['top_sector']}\n"
        f"Top bullish stocks  : {bullish}\n"
        f"Top bearish stocks  : {bearish}\n"
        f"{'=' * 50}\n"
    )


def save_report(report_text):
    """Save the full report to a timestamped text file and return the path."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"psx_signals_{timestamp}.txt"
    filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(report_text)

    return filepath


def main():
    # ── Step 1: Fetch headlines ──────────────────────────────────────────
    print("Fetching news...")
    headlines = fetch_news()
    print(f"  Total headlines: {len(headlines)}\n")

    # ── Step 2: Analyze ──────────────────────────────────────────────────
    print("Analyzing headlines...\n")
    signals, summary = analyze_all(headlines)

    # ── Step 3: Build report ─────────────────────────────────────────────
    report_lines = []
    report_lines.append("PSX NARRATIVE ENGINE - Signal Report")
    report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    for sig in signals:
        block = format_signal(sig)
        print(block)
        report_lines.append(block)

    summary_block = format_summary(summary)
    print(summary_block)
    report_lines.append(summary_block)

    # ── Step 4: Save to file ─────────────────────────────────────────────
    full_report = "\n".join(report_lines)
    filepath = save_report(full_report)
    print(f"Report saved to: {filepath}")


if __name__ == "__main__":
    main()
