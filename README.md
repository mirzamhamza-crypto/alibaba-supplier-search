# Alibaba Supplier Search 🐾

A Python desktop app that searches Alibaba for **dog snuffle ball** and **dog snuffle mat** suppliers and displays results in a clean, sortable table.

## Features

- 🔍 Searches both `dog snuffle ball` and `dog snuffle mat` simultaneously
- 📊 Displays supplier name, rating, price range, MOQ, and direct listing link
- ⚡ Loading indicator while fetching results
- 🔎 Inline filter bar to narrow down results
- 🌐 Double-click any row to open the Alibaba listing in your browser
- ⚠️ Graceful error handling if Alibaba blocks the request
- 📦 Auto-installs `requests` and `beautifulsoup4` on first run

## Requirements

- Python 3.10+
- `tkinter` (included with Python)
- `requests`
- `beautifulsoup4`
- `lxml`

## Run

```bash
python alibaba_supplier_search.py
```

Dependencies are installed automatically on first run.

## Notes

Results depend on Alibaba's live website structure. If Alibaba returns a CAPTCHA or blocks the request, the app will display a friendly error message.
