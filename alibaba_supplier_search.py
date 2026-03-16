"""
Alibaba Supplier Search Tool – Selenium Edition
Uses undetected-chromedriver in VISIBLE (non-headless) mode to bypass CAPTCHA.
If a CAPTCHA appears, the Chrome window comes on-screen for you to solve it.
"""

import subprocess
import sys
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import webbrowser
import time
import random


# ── Auto-install dependencies ───────────────────────────────────────────────────
def _ensure(import_name: str, pip_name: str):
    try:
        __import__(import_name)
    except ImportError:
        print(f"Installing {pip_name}…")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", pip_name, "-q"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


_ensure("undetected_chromedriver", "undetected-chromedriver")
_ensure("selenium", "selenium")
_ensure("selenium_stealth", "selenium-stealth")
_ensure("bs4", "beautifulsoup4")
_ensure("lxml", "lxml")

import undetected_chromedriver as uc                            # noqa: E402
from selenium.webdriver.common.by import By                    # noqa: E402
from selenium.webdriver.support.ui import WebDriverWait        # noqa: E402
from selenium.webdriver.support import expected_conditions as EC  # noqa: E402
from selenium.common.exceptions import TimeoutException, WebDriverException  # noqa: E402
from selenium_stealth import stealth                            # noqa: E402
from bs4 import BeautifulSoup                                  # noqa: E402


# ── Config ──────────────────────────────────────────────────────────────────────
SEARCH_TERMS = ["dog snuffle ball", "dog snuffle mat"]

RESULT_SELECTORS = (
    "div.organic-list-offer-outter, "
    "div.J-offer-wrapper, "
    "div[class*='offer-list'], "
    "div.list-item, "
    "div[class*='gallery-offer']"
)

CAPTCHA_SIGNALS = ["captcha", "verify you're human", "robot",
                   "unusual traffic", "blocked", "security check"]

CAPTCHA_WAIT_SECS = 120   # seconds user has to solve a CAPTCHA


# ── Driver factory ──────────────────────────────────────────────────────────────
def _make_driver() -> uc.Chrome:
    """
    Launch Chrome in VISIBLE (non-headless) mode.
    Headless browsers are trivially fingerprinted by Alibaba — removing that
    flag is the single most effective CAPTCHA-bypass change.
    The window starts off-screen so it doesn't clutter the desktop.
    """
    opts = uc.ChromeOptions()
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--window-size=1280,900")
    opts.add_argument("--window-position=-2400,0")   # off-screen but NOT headless
    opts.add_argument("--lang=en-US,en")
    opts.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
    # *** NO --headless flag — that's what was causing CAPTCHA blocks ***

    driver = uc.Chrome(options=opts, use_subprocess=True)

    # Apply selenium-stealth on top of undetected-chromedriver
    stealth(
        driver,
        languages=["en-US", "en"],
        vendor="Google Inc.",
        platform="Win32",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True,
    )

    # Additional JS fingerprint patches
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver',  {get: () => undefined});
            Object.defineProperty(navigator, 'plugins',    {get: () => [1,2,3,4,5]});
            Object.defineProperty(navigator, 'languages',  {get: () => ['en-US','en']});
            window.chrome = { runtime: {} };
        """
    })

    return driver


def build_url(query: str) -> str:
    encoded = query.replace(" ", "+")
    return f"https://www.alibaba.com/trade/search?SearchText={encoded}&type=supplier"


# ── CAPTCHA handler ─────────────────────────────────────────────────────────────
def _is_captcha_page(html: str) -> bool:
    lower = html.lower()
    return any(sig in lower for sig in CAPTCHA_SIGNALS)


def _wait_through_captcha(driver: uc.Chrome, status_cb) -> bool:
    """
    Move the Chrome window on-screen and wait up to CAPTCHA_WAIT_SECS for
    the user to solve the CAPTCHA manually.  Returns True if cleared.
    """
    status_cb("⚠️  CAPTCHA detected — Chrome window opening for you to solve it…")
    driver.set_window_position(100, 100)
    driver.set_window_size(1100, 800)

    # Jitter to auto-pass trivial bot checks
    try:
        driver.execute_script("window.scrollBy(0, 300);")
        time.sleep(1.5)
        driver.execute_script("window.scrollBy(0, -150);")
    except Exception:
        pass

    deadline = time.time() + CAPTCHA_WAIT_SECS
    while time.time() < deadline:
        time.sleep(2)
        if not _is_captcha_page(driver.page_source):
            driver.set_window_position(-2400, 0)   # hide again
            status_cb("✅  CAPTCHA cleared — continuing search…")
            return True
        remaining = int(deadline - time.time())
        status_cb(
            f"⚠️  Please solve the CAPTCHA in the Chrome window "
            f"({remaining}s remaining)…"
        )

    return False


# ── Scraper ─────────────────────────────────────────────────────────────────────
def fetch_suppliers(driver: uc.Chrome, search_term: str,
                    status_cb=None) -> list[dict]:
    if status_cb is None:
        status_cb = lambda _: None

    driver.get(build_url(search_term))
    time.sleep(random.uniform(3.0, 5.5))

    # Gentle human-like scroll
    driver.execute_script("window.scrollBy(0, 500);")
    time.sleep(random.uniform(1.0, 2.0))
    driver.execute_script("window.scrollBy(0, -200);")
    time.sleep(random.uniform(0.5, 1.0))

    # CAPTCHA check
    if _is_captcha_page(driver.page_source):
        if not _wait_through_captcha(driver, status_cb):
            raise RuntimeError(
                "CAPTCHA was not solved within the time limit.\n"
                "Please try again — Chrome will open on-screen."
            )

    # Wait for product cards
    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, RESULT_SELECTORS))
        )
    except TimeoutException:
        pass

    return parse_page(driver.page_source, search_term)


# ── Parser ───────────────────────────────────────────────────────────────────────
def parse_page(html: str, search_term: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    results = []

    for sel in [
        "div.organic-list-offer-outter", "div.J-offer-wrapper",
        "div[class*='offer-list-row']",  "div.list-item",
        "div.m-gallery-product-item-v2", "div[data-content='offer']",
        "div[class*='gallery-offer-item']",
    ]:
        cards = soup.select(sel)
        if cards:
            break
    else:
        return _fallback_parse(soup, search_term)

    for card in cards[:15]:
        try:
            r = _extract_card(card, search_term)
            if r:
                results.append(r)
        except Exception:
            continue

    return results


def _extract_card(card, search_term: str) -> dict | None:
    title_el = (
        card.select_one("h2 a")
        or card.select_one(".organic-list-offer__title a")
        or card.select_one("a.title")
        or card.select_one("[class*='title'] a")
        or card.select_one("a[title]")
    )
    if not title_el:
        return None

    title = title_el.get_text(strip=True) or title_el.get("title", "N/A")
    link  = title_el.get("href", "")
    if link.startswith("//"):
        link = "https:" + link
    if not link.startswith("http"):
        link = "https://www.alibaba.com" + link

    def _text(el):
        return el.get_text(strip=True) if el else "N/A"

    supplier = _text(
        card.select_one(".organic-list-offer__company a")
        or card.select_one("[class*='company'] a")
        or card.select_one("[class*='supplier'] a")
        or card.select_one(".company-name a")
    )
    rating = (_text(
        card.select_one("[class*='star']")
        or card.select_one("[class*='rating']")
        or card.select_one("[class*='score']")
    ))[:6]
    price = (_text(
        card.select_one(".price")
        or card.select_one("[class*='price']")
        or card.select_one(".offer-price")
    ))[:40]

    moq_el = (
        card.select_one("[class*='moq']")
        or card.select_one("[class*='min-order']")
        or card.select_one("[class*='minimum']")
    )
    if moq_el:
        moq = moq_el.get_text(strip=True)[:30]
    else:
        t = card.find(string=lambda s: s and "Min. order" in s)
        moq = t.strip()[:30] if t else "N/A"

    return {
        "search_term": search_term,
        "title":    title[:80],
        "supplier": supplier[:50],
        "rating":   rating,
        "price":    price,
        "moq":      moq,
        "link":     link,
    }


def _fallback_parse(soup, search_term: str) -> list[dict]:
    results, seen = [], set()
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
        results.append({"search_term": search_term, "title": title[:80],
                        "supplier": "N/A", "rating": "N/A",
                        "price": "N/A", "moq": "N/A", "link": href})
        if len(results) >= 10:
            break
    return results


# ── GUI ──────────────────────────────────────────────────────────────────────────
class App(tk.Tk):
    COLUMNS     = ("search_term", "supplier", "rating", "price", "moq", "title")
    COL_HEADERS = {
        "search_term": "Search Term", "supplier": "Supplier",
        "rating": "Rating",           "price":    "Price Range",
        "moq":    "Min. Order",       "title":    "Product / Listing",
    }
    COL_WIDTHS  = {
        "search_term": 130, "supplier": 180, "rating": 70,
        "price": 120,       "moq": 110,      "title": 280,
    }

    def __init__(self):
        super().__init__()
        self.title("Alibaba Supplier Search – Dog Snuffle Products")
        self.geometry("1100x680")
        self.resizable(True, True)
        self.configure(bg="#f0f4f8")
        self._results: list[dict] = []
        self._driver: uc.Chrome | None = None
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._build_ui()

    def _on_close(self):
        if self._driver:
            try:
                self._driver.quit()
            except Exception:
                pass
        self.destroy()

    def _build_ui(self):
        style = ttk.Style(self)
        style.theme_use("clam")

        header = tk.Frame(self, bg="#1a73e8", pady=14)
        header.pack(fill="x")
        tk.Label(header, text="🐾  Alibaba Supplier Search",
                 font=("Segoe UI", 18, "bold"), bg="#1a73e8", fg="white").pack(side="left", padx=20)
        tk.Label(header, text="  |  Dog Snuffle Ball  ·  Dog Snuffle Mat",
                 font=("Segoe UI", 11), bg="#1a73e8", fg="#cce4ff").pack(side="left")
        tk.Label(header, text="🛡️  Stealth Mode  •  CAPTCHA-aware",
                 font=("Segoe UI", 9, "bold"), bg="#1557b0", fg="#a8d4ff",
                 padx=8, pady=4).pack(side="right", padx=16)

        ctrl = tk.Frame(self, bg="#f0f4f8", pady=10)
        ctrl.pack(fill="x", padx=20)
        self.search_btn = ttk.Button(ctrl, text="🔍  Search Alibaba",
                                     command=self._start_search, width=22)
        self.search_btn.pack(side="left", padx=(0, 12))
        self.status_var = tk.StringVar(value="Click 'Search Alibaba' to fetch live results.")
        tk.Label(ctrl, textvariable=self.status_var, font=("Segoe UI", 9),
                 bg="#f0f4f8", fg="#555", wraplength=580, justify="left").pack(side="left")
        self.progress = ttk.Progressbar(ctrl, mode="indeterminate", length=180)
        self.progress.pack(side="right", padx=6)
        self.count_var = tk.StringVar(value="")
        tk.Label(ctrl, textvariable=self.count_var, font=("Segoe UI", 9, "bold"),
                 bg="#f0f4f8", fg="#1a73e8").pack(side="right", padx=6)

        filter_bar = tk.Frame(self, bg="#f0f4f8")
        filter_bar.pack(fill="x", padx=20, pady=(0, 6))
        tk.Label(filter_bar, text="Filter:", bg="#f0f4f8", font=("Segoe UI", 9)).pack(side="left")
        self.filter_var = tk.StringVar()
        self.filter_var.trace_add("write", lambda *_: self._apply_filter())
        ttk.Entry(filter_bar, textvariable=self.filter_var, width=35).pack(side="left", padx=6)
        ttk.Button(filter_bar, text="Clear",
                   command=lambda: self.filter_var.set(""), width=7).pack(side="left")

        table_frame = tk.Frame(self, bg="#f0f4f8")
        table_frame.pack(fill="both", expand=True, padx=20, pady=(0, 6))
        style.configure("Results.Treeview", font=("Segoe UI", 9), rowheight=26,
                        background="#ffffff", fieldbackground="#ffffff", foreground="#222")
        style.configure("Results.Treeview.Heading", font=("Segoe UI", 9, "bold"))
        style.map("Results.Treeview", background=[("selected", "#cce4ff")])

        self.tree = ttk.Treeview(table_frame, columns=self.COLUMNS, show="headings",
                                  style="Results.Treeview", selectmode="browse")
        for col in self.COLUMNS:
            self.tree.heading(col, text=self.COL_HEADERS[col],
                              command=lambda c=col: self._sort_col(c))
            self.tree.column(col, width=self.COL_WIDTHS[col],
                             minwidth=60, stretch=(col == "title"))
        self.tree.tag_configure("odd",  background="#f9fbff")
        self.tree.tag_configure("even", background="#ffffff")
        self.tree.tag_configure("ball", foreground="#1a73e8")
        self.tree.tag_configure("mat",  foreground="#0a7c59")

        vsb = ttk.Scrollbar(table_frame, orient="vertical",   command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)
        self.tree.bind("<Double-1>", self._on_double_click)

        footer = tk.Frame(self, bg="#e8ecf0", pady=5)
        footer.pack(fill="x", side="bottom")
        tk.Label(footer, text="Double-click any row to open the listing in your browser.",
                 font=("Segoe UI", 8), bg="#e8ecf0", fg="#666").pack(side="left", padx=14)
        tk.Label(footer, text="CAPTCHA? Chrome opens on-screen — solve it and search resumes automatically.",
                 font=("Segoe UI", 8), bg="#e8ecf0", fg="#999").pack(side="right", padx=14)

    def _start_search(self):
        self.search_btn.config(state="disabled")
        self.progress.start(10)
        self.status_var.set("Launching stealth browser… please wait 15–30 seconds.")
        self.count_var.set("")
        self._clear_table()
        threading.Thread(target=self._run_search, daemon=True).start()

    def _run_search(self):
        all_results, errors = [], []
        driver = None
        try:
            self._set_status("Starting undetected Chrome (stealth + CAPTCHA-aware)…")
            driver = _make_driver()
            self._driver = driver

            for term in SEARCH_TERMS:
                self._set_status(f"Searching Alibaba for '{term}'…")
                try:
                    items = fetch_suppliers(driver, term, status_cb=self._set_status)
                    all_results.extend(items)
                    self._set_status(f"✅  Found {len(items)} results for '{term}'.")
                except WebDriverException as e:
                    errors.append(f"Browser error for '{term}': {str(e)[:120]}")
                except RuntimeError as e:
                    errors.append(str(e))
                except Exception as e:
                    errors.append(f"Error for '{term}': {str(e)[:120]}")

        except Exception as e:
            errors.append(
                f"Failed to launch browser:\n{str(e)[:250]}\n\n"
                "➡  Make sure Google Chrome is installed."
            )
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass
            self._driver = None

        self._results = all_results
        self.after(0, self._finish_search, all_results, errors)

    def _finish_search(self, results, errors):
        self.progress.stop()
        self.search_btn.config(state="normal")
        if errors:
            msg = "\n\n".join(errors)
            if not results:
                messagebox.showerror("Search Error", f"Could not retrieve results:\n\n{msg}")
                self.status_var.set("Search failed — see error dialog.")
                return
            messagebox.showwarning("Partial Results", f"Some errors occurred:\n\n{msg}")
        if not results:
            self.status_var.set("No results found. Try again in a moment.")
            return
        self._populate_table(results)
        self.count_var.set(f"{len(results)} results")
        self.status_var.set(
            f"Done — {len(results)} suppliers found. Double-click any row to open the listing.")

    def _clear_table(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

    def _populate_table(self, data):
        self._clear_table()
        for i, item in enumerate(data):
            tag      = "odd" if i % 2 else "even"
            term_tag = "ball" if "ball" in item.get("search_term", "").lower() else "mat"
            self.tree.insert("", "end", iid=str(i), tags=(tag, term_tag),
                             values=(item["search_term"], item["supplier"], item["rating"],
                                     item["price"],       item["moq"],      item["title"]))

    def _apply_filter(self):
        query = self.filter_var.get().lower()
        if not self._results:
            return
        filtered = [r for r in self._results
                    if query in r.get("title",       "").lower()
                    or query in r.get("supplier",    "").lower()
                    or query in r.get("search_term", "").lower()
                    or query in r.get("price",       "").lower()]
        self._populate_table(filtered)
        self.count_var.set(f"{len(filtered)} / {len(self._results)} results")

    def _sort_col(self, col):
        data = [(self.tree.set(c, col), c) for c in self.tree.get_children("")]
        data.sort(key=lambda x: x[0].lower())
        for idx, (_, c) in enumerate(data):
            self.tree.move(c, "", idx)

    def _on_double_click(self, event):
        item = self.tree.identify_row(event.y)
        if not item:
            return
        filtered = self._get_current_filtered()
        idx = int(item)
        if idx < len(filtered):
            link = filtered[idx].get("link", "")
            if link.startswith("http"):
                webbrowser.open(link)
            else:
                messagebox.showinfo("No Link", "No valid link for this listing.")

    def _get_current_filtered(self):
        query = self.filter_var.get().lower()
        if not query:
            return self._results
        return [r for r in self._results
                if query in r.get("title",       "").lower()
                or query in r.get("supplier",    "").lower()
                or query in r.get("search_term", "").lower()
                or query in r.get("price",       "").lower()]

    def _set_status(self, msg):
        self.after(0, lambda: self.status_var.set(msg))


# ── Entry point ───────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = App()
    app.mainloop()
