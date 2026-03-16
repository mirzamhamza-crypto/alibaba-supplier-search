"""
Alibaba Supplier Search Tool
Searches for "dog snuffle ball" and "dog snuffle mat" suppliers on Alibaba.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import webbrowser
import time
import random

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests", "beautifulsoup4", "lxml"])
    import requests
    from bs4 import BeautifulSoup


# ── Configuration ─────────────────────────────────────────────────────────────
SEARCH_TERMS = ["dog snuffle ball", "dog snuffle mat"]
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,image/apng,*/*;q=0.8"
    ),
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
}
SESSION = requests.Session()


# ── Scraper ────────────────────────────────────────────────────────────────────
def build_url(query: str, page: int = 1) -> str:
    encoded = query.replace(" ", "+")
    return (
        f"https://www.alibaba.com/trade/search"
        f"?SearchText={encoded}&page={page}&type=supplier"
    )


def parse_results(html: str, search_term: str) -> list[dict]:
    """Parse Alibaba search HTML and return a list of supplier dicts."""
    soup = BeautifulSoup(html, "lxml")
    results = []

    # Alibaba uses several card class patterns – try them all
    card_selectors = [
        "div.organic-list-offer-outter",
        "div.J-offer-wrapper",
        "div[class*='offer-list-row']",
        "div.list-item",
        "div.m-gallery-product-item-v2",
        "div[data-content='offer']",
        "div.offer-list-row",
    ]

    cards = []
    for sel in card_selectors:
        cards = soup.select(sel)
        if cards:
            break

    # Fallback: grab any anchor that looks like a product listing
    if not cards:
        # Try to extract structured data from JSON-LD or meta
        return _fallback_parse(soup, search_term)

    for card in cards[:15]:  # cap at 15 per term
        try:
            result = _extract_card(card, search_term)
            if result:
                results.append(result)
        except Exception:
            continue

    return results


def _extract_card(card, search_term: str) -> dict | None:
    # ── Title / Link ──────────────────────────────────────────────────────────
    title_el = (
        card.select_one("h2 a")
        or card.select_one(".organic-list-offer__title a")
        or card.select_one("a.title")
        or card.select_one("[class*='title'] a")
        or card.select_one("a[title]")
        or card.select_one("a[href*='alibaba.com']")
    )
    if not title_el:
        return None

    title = title_el.get_text(strip=True) or title_el.get("title", "N/A")
    link = title_el.get("href", "")
    if link.startswith("//"):
        link = "https:" + link
    if not link.startswith("http"):
        link = "https://www.alibaba.com" + link

    # ── Supplier / Company ────────────────────────────────────────────────────
    supplier_el = (
        card.select_one(".organic-list-offer__company a")
        or card.select_one("[class*='company'] a")
        or card.select_one("[class*='supplier'] a")
        or card.select_one(".company-name a")
    )
    supplier = supplier_el.get_text(strip=True) if supplier_el else "N/A"

    # ── Rating ────────────────────────────────────────────────────────────────
    rating_el = (
        card.select_one("[class*='star']")
        or card.select_one("[class*='rating']")
        or card.select_one("[class*='score']")
    )
    if rating_el:
        raw = rating_el.get_text(strip=True)
        rating = raw[:6] if raw else "N/A"
    else:
        rating = "N/A"

    # ── Price ─────────────────────────────────────────────────────────────────
    price_el = (
        card.select_one(".price")
        or card.select_one("[class*='price']")
        or card.select_one(".offer-price")
    )
    price = price_el.get_text(strip=True) if price_el else "N/A"
    price = price[:40]  # truncate long strings

    # ── MOQ ───────────────────────────────────────────────────────────────────
    moq_el = (
        card.select_one("[class*='moq']")
        or card.select_one("[class*='min-order']")
        or card.select_one("[class*='minimum']")
    )
    if moq_el:
        moq = moq_el.get_text(strip=True)[:30]
    else:
        # look for text containing "Min. order"
        moq_text = card.find(string=lambda t: t and "Min. order" in t)
        moq = moq_text.strip()[:30] if moq_text else "N/A"

    return {
        "search_term": search_term,
        "title": title[:80],
        "supplier": supplier[:50],
        "rating": rating,
        "price": price,
        "moq": moq,
        "link": link,
    }


def _fallback_parse(soup, search_term: str) -> list[dict]:
    """Last-resort parser: grab all product anchors from the page."""
    results = []
    seen = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("//"):
            href = "https:" + href
        if "alibaba.com" not in href:
            continue
        if "/product-detail/" not in href and "/offer/" not in href:
            continue
        if href in seen:
            continue
        seen.add(href)
        title = a.get_text(strip=True) or a.get("title", "")
        if len(title) < 5:
            continue
        results.append({
            "search_term": search_term,
            "title": title[:80],
            "supplier": "N/A",
            "rating": "N/A",
            "price": "N/A",
            "moq": "N/A",
            "link": href,
        })
        if len(results) >= 10:
            break
    return results


def fetch_suppliers(search_term: str) -> list[dict]:
    """Fetch one search page and parse results."""
    url = build_url(search_term)
    time.sleep(random.uniform(1.0, 2.5))   # polite delay
    resp = SESSION.get(url, headers=HEADERS, timeout=20, allow_redirects=True)
    resp.raise_for_status()

    # Detect CAPTCHA / block pages
    if any(x in resp.text for x in ["CAPTCHA", "captcha", "robot", "Robot", "verify"]):
        raise RuntimeError("Alibaba returned a CAPTCHA/verification page.")

    return parse_results(resp.text, search_term)


# ── GUI ────────────────────────────────────────────────────────────────────────
class App(tk.Tk):
    COLUMNS = ("search_term", "supplier", "rating", "price", "moq", "title")
    COL_HEADERS = {
        "search_term": "Search Term",
        "supplier": "Supplier",
        "rating": "Rating",
        "price": "Price Range",
        "moq": "Min. Order",
        "title": "Product / Listing",
    }
    COL_WIDTHS = {
        "search_term": 130,
        "supplier": 180,
        "rating": 70,
        "price": 120,
        "moq": 110,
        "title": 280,
    }

    def __init__(self):
        super().__init__()
        self.title("Alibaba Supplier Search – Dog Snuffle Products")
        self.geometry("1100x680")
        self.resizable(True, True)
        self.configure(bg="#f0f4f8")

        self._results: list[dict] = []
        self._build_ui()

    # ── UI construction ───────────────────────────────────────────────────────
    def _build_ui(self):
        style = ttk.Style(self)
        style.theme_use("clam")

        # Header
        header = tk.Frame(self, bg="#1a73e8", pady=14)
        header.pack(fill="x")
        tk.Label(
            header,
            text="🐾  Alibaba Supplier Search",
            font=("Segoe UI", 18, "bold"),
            bg="#1a73e8",
            fg="white",
        ).pack(side="left", padx=20)

        # Subtitle label (search terms)
        tk.Label(
            header,
            text="  |  Dog Snuffle Ball  ·  Dog Snuffle Mat",
            font=("Segoe UI", 11),
            bg="#1a73e8",
            fg="#cce4ff",
        ).pack(side="left")

        # Controls bar
        ctrl = tk.Frame(self, bg="#f0f4f8", pady=10)
        ctrl.pack(fill="x", padx=20)

        self.search_btn = ttk.Button(
            ctrl, text="🔍  Search Alibaba", command=self._start_search, width=22
        )
        self.search_btn.pack(side="left", padx=(0, 12))

        self.status_var = tk.StringVar(value="Click 'Search Alibaba' to fetch live results.")
        self.status_lbl = tk.Label(
            ctrl, textvariable=self.status_var,
            font=("Segoe UI", 9), bg="#f0f4f8", fg="#555"
        )
        self.status_lbl.pack(side="left")

        self.progress = ttk.Progressbar(ctrl, mode="indeterminate", length=180)
        self.progress.pack(side="right", padx=6)

        # Results count
        self.count_var = tk.StringVar(value="")
        tk.Label(
            ctrl, textvariable=self.count_var,
            font=("Segoe UI", 9, "bold"), bg="#f0f4f8", fg="#1a73e8"
        ).pack(side="right", padx=6)

        # Filter bar
        filter_bar = tk.Frame(self, bg="#f0f4f8")
        filter_bar.pack(fill="x", padx=20, pady=(0, 6))
        tk.Label(filter_bar, text="Filter:", bg="#f0f4f8", font=("Segoe UI", 9)).pack(side="left")
        self.filter_var = tk.StringVar()
        self.filter_var.trace_add("write", lambda *_: self._apply_filter())
        filter_entry = ttk.Entry(filter_bar, textvariable=self.filter_var, width=35)
        filter_entry.pack(side="left", padx=6)
        ttk.Button(filter_bar, text="Clear", command=lambda: self.filter_var.set(""), width=7).pack(side="left")

        # Table frame
        table_frame = tk.Frame(self, bg="#f0f4f8")
        table_frame.pack(fill="both", expand=True, padx=20, pady=(0, 6))

        style.configure(
            "Results.Treeview",
            font=("Segoe UI", 9),
            rowheight=26,
            background="#ffffff",
            fieldbackground="#ffffff",
            foreground="#222",
        )
        style.configure("Results.Treeview.Heading", font=("Segoe UI", 9, "bold"))
        style.map("Results.Treeview", background=[("selected", "#cce4ff")])

        self.tree = ttk.Treeview(
            table_frame,
            columns=self.COLUMNS,
            show="headings",
            style="Results.Treeview",
            selectmode="browse",
        )
        for col in self.COLUMNS:
            self.tree.heading(col, text=self.COL_HEADERS[col],
                              command=lambda c=col: self._sort_col(c))
            self.tree.column(col, width=self.COL_WIDTHS[col], minwidth=60, stretch=(col == "title"))

        # Tag colours for alternating rows & term badges
        self.tree.tag_configure("odd", background="#f9fbff")
        self.tree.tag_configure("even", background="#ffffff")
        self.tree.tag_configure("ball", foreground="#1a73e8")
        self.tree.tag_configure("mat",  foreground="#0a7c59")

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        self.tree.bind("<Double-1>", self._on_double_click)

        # Footer
        footer = tk.Frame(self, bg="#e8ecf0", pady=5)
        footer.pack(fill="x", side="bottom")
        tk.Label(
            footer,
            text="Double-click any row to open the Alibaba listing in your browser.",
            font=("Segoe UI", 8), bg="#e8ecf0", fg="#666"
        ).pack(side="left", padx=14)
        tk.Label(
            footer,
            text="Note: Results depend on Alibaba's live website structure.",
            font=("Segoe UI", 8), bg="#e8ecf0", fg="#999"
        ).pack(side="right", padx=14)

    # ── Search logic ──────────────────────────────────────────────────────────
    def _start_search(self):
        self.search_btn.config(state="disabled")
        self.progress.start(10)
        self.status_var.set("Searching Alibaba… this may take 10–20 seconds.")
        self.count_var.set("")
        self._clear_table()
        threading.Thread(target=self._run_search, daemon=True).start()

    def _run_search(self):
        all_results = []
        errors = []

        for term in SEARCH_TERMS:
            self._set_status(f"Fetching '{term}'…")
            try:
                items = fetch_suppliers(term)
                all_results.extend(items)
                self._set_status(f"Found {len(items)} results for '{term}'.")
            except requests.exceptions.HTTPError as e:
                errors.append(f"HTTP error for '{term}': {e}")
            except requests.exceptions.ConnectionError:
                errors.append(f"Connection error for '{term}'. Check your internet connection.")
            except requests.exceptions.Timeout:
                errors.append(f"Request timed out for '{term}'.")
            except RuntimeError as e:
                errors.append(str(e))
            except Exception as e:
                errors.append(f"Unexpected error for '{term}': {e}")

        self._results = all_results
        self.after(0, self._finish_search, all_results, errors)

    def _finish_search(self, results: list[dict], errors: list[str]):
        self.progress.stop()
        self.search_btn.config(state="normal")

        if errors:
            msg = "\n\n".join(errors)
            if not results:
                messagebox.showerror(
                    "Search Error",
                    f"Could not retrieve results:\n\n{msg}\n\n"
                    "Alibaba may be blocking automated requests.\n"
                    "Try again later or check your network connection.",
                )
                self.status_var.set("Search failed. See error dialog.")
                return
            else:
                messagebox.showwarning("Partial Results", f"Some errors occurred:\n\n{msg}")

        if not results:
            self.status_var.set("No results found. Try searching manually on alibaba.com.")
            return

        self._populate_table(results)
        self.count_var.set(f"{len(results)} results")
        self.status_var.set(
            f"Done. {len(results)} suppliers found. "
            "Double-click a row to open the listing."
        )

    # ── Table helpers ─────────────────────────────────────────────────────────
    def _clear_table(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

    def _populate_table(self, data: list[dict]):
        self._clear_table()
        for i, item in enumerate(data):
            tag = "odd" if i % 2 else "even"
            term_tag = "ball" if "ball" in item.get("search_term", "").lower() else "mat"
            self.tree.insert(
                "",
                "end",
                iid=str(i),
                values=(
                    item["search_term"],
                    item["supplier"],
                    item["rating"],
                    item["price"],
                    item["moq"],
                    item["title"],
                ),
                tags=(tag, term_tag),
            )

    def _apply_filter(self):
        query = self.filter_var.get().lower()
        if not self._results:
            return
        filtered = [
            r for r in self._results
            if query in r.get("title", "").lower()
            or query in r.get("supplier", "").lower()
            or query in r.get("search_term", "").lower()
            or query in r.get("price", "").lower()
        ]
        self._populate_table(filtered)
        self.count_var.set(f"{len(filtered)} / {len(self._results)} results")

    def _sort_col(self, col: str):
        data = [
            (self.tree.set(child, col), child)
            for child in self.tree.get_children("")
        ]
        data.sort(key=lambda x: x[0].lower())
        for idx, (_, child) in enumerate(data):
            self.tree.move(child, "", idx)

    def _on_double_click(self, event):
        item = self.tree.identify_row(event.y)
        if not item:
            return
        idx = int(item)
        filtered_data = self._get_current_filtered()
        if idx < len(filtered_data):
            link = filtered_data[idx].get("link", "")
            if link.startswith("http"):
                webbrowser.open(link)
            else:
                messagebox.showinfo("No Link", "No valid link available for this listing.")

    def _get_current_filtered(self) -> list[dict]:
        """Return results matching the current filter."""
        query = self.filter_var.get().lower()
        if not query:
            return self._results
        return [
            r for r in self._results
            if query in r.get("title", "").lower()
            or query in r.get("supplier", "").lower()
            or query in r.get("search_term", "").lower()
            or query in r.get("price", "").lower()
        ]

    def _set_status(self, msg: str):
        self.after(0, lambda: self.status_var.set(msg))


# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = App()
    app.mainloop()
