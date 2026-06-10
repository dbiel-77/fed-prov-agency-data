import re
import os
import csv
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs, unquote, urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Semaphore, Lock

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

PHONE_RE = re.compile(r'(?:(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})')
EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')

MINISTRY_FIELDS = [
    "province", "type", "name", "about", "priorities",
    "website", "phone", "email", "address",
    "minister_name", "minister_phone", "minister_email",
    "minister_url", "minister_photo_url",
    "twitter", "facebook", "youtube", "instagram",
]

AGENCY_FIELDS = [
    "province", "type", "name", "description",
    "website", "phone", "email", "address",
    "parent_ministry",
]

# ── Rate limiting ────────────────────────────────────────────────────────────
# Max concurrent requests per domain (avoids hammering a single gov site)
_DOM_LIMIT = 5
_dom_lock = Lock()
_dom_sems: dict[str, Semaphore] = {}

# Max concurrent DuckDuckGo searches globally
DDG_SEM = Semaphore(2)


def _dom_sem(url: str) -> Semaphore:
    domain = urlparse(url).netloc
    with _dom_lock:
        if domain not in _dom_sems:
            _dom_sems[domain] = Semaphore(_DOM_LIMIT)
        return _dom_sems[domain]


# ── HTTP helpers ─────────────────────────────────────────────────────────────

def make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update(HEADERS)
    return s


def get_soup(session: requests.Session, url: str, timeout: int = 15):
    with _dom_sem(url):
        try:
            resp = session.get(url, timeout=timeout)
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "html.parser")
        except Exception as e:
            print(f"[WARN] {url}: {e}")
            return None


def duckduckgo(query: str, session=None) -> str:
    if session is None:
        session = make_session()
    with DDG_SEM:
        try:
            r = session.get(
                "https://duckduckgo.com/html/",
                params={"q": query},
                timeout=10,
            )
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")
            a = soup.select_one("a.result__a")
            if not a:
                return ""
            parsed = urlparse(a["href"])
            qs = parse_qs(parsed.query)
            return unquote(qs["uddg"][0]) if "uddg" in qs else a["href"]
        except Exception as e:
            print(f"[DDG] {query}: {e}")
            return ""


# ── Extraction helpers ───────────────────────────────────────────────────────

def extract_phone(text: str) -> str:
    m = PHONE_RE.search(text or "")
    return m.group(0).strip() if m else ""


def extract_email(text: str) -> str:
    m = EMAIL_RE.search(text or "")
    return m.group(0).strip() if m else ""


def extract_socials(soup) -> dict:
    out = {"twitter": "", "facebook": "", "youtube": "", "instagram": ""}
    if not soup:
        return out
    patterns = {
        "twitter":   r"(?:twitter|x)\.com/",
        "facebook":  r"facebook\.com/",
        "youtube":   r"youtube\.com/",
        "instagram": r"instagram\.com/",
    }
    for a in soup.find_all("a", href=True):
        href = a["href"]
        for p, pat in patterns.items():
            if not out[p] and re.search(pat, href, re.I):
                out[p] = href
    return out


# ── I/O helpers ──────────────────────────────────────────────────────────────

def open_writer(filepath: str, fields: list):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    f = open(filepath, "w", newline="", encoding="utf-8")
    w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
    w.writeheader()
    return f, w


# ── Concurrency helper ───────────────────────────────────────────────────────

def parallel_scrape(session, items, worker_fn, max_workers: int = 8) -> list:
    """
    Call worker_fn(session, item) for every item concurrently.
    Returns a list of non-None results (order not guaranteed).
    """
    if not items:
        return []
    n = min(max_workers, len(items))
    results = []
    with ThreadPoolExecutor(max_workers=n) as ex:
        futs = {ex.submit(worker_fn, session, item): item for item in items}
        for fut in as_completed(futs):
            try:
                r = fut.result()
                if r is not None:
                    results.append(r)
            except Exception as e:
                print(f"[WARN] worker failed: {e}")
    return results
