"""
policy_tracker.py

Fetches policy events (e.g., PRORULE items) from the Federal Register API,
with robust retries, timeouts, and date-window chunking to avoid timeouts.

Outputs:
  - docs/data/Policy_Events.json  (consolidated results across requested range)

Optional:
  - If GOOGLE_CREDENTIALS / GOOGLE_SHEET_ID are set, appends/updates rows in the sheet.

Env knobs:
  START_DATE=YYYY-MM-DD      # default: 30 days ago
  END_DATE=YYYY-MM-DD        # default: today
  FR_TYPES=PRORULE           # comma-separated, e.g. "PRORULE,NOTICE"
  CHUNK_DAYS=7               # size of date chunks (will auto-bisect on failure)
  REQUEST_TIMEOUT=20         # seconds for each request
  MAX_RETRIES=5              # HTTP retry count for 429/5xx/connect/read
  DATA_OUT=docs/data/Policy_Events.json
"""

import os
import json
import math
import time
import logging
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Tuple

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ---- Optional Google Sheets wiring (only if env present) ----
try:
    import gspread
    from google.oauth2.service_account import Credentials as GCreds
except Exception:
    gspread = None
    GCreds = None

# ---------- Config ----------

def env_str(name: str, default: str) -> str:
    val = os.getenv(name)
    return val if val not in (None, "") else default

def env_int(name: str, default: int) -> int:
    try:
        return int(env_str(name, str(default)))
    except ValueError:
        return default

def env_date(name: str, default: date) -> date:
    s = os.getenv(name)
    if not s:
        return default
    return datetime.strptime(s, "%Y-%m-%d").date()

START_DATE = env_date("START_DATE", date.today() - timedelta(days=30))
END_DATE   = env_date("END_DATE", date.today())
FR_TYPES   = [t.strip() for t in env_str("FR_TYPES", "PRORULE").split(",") if t.strip()]
CHUNK_DAYS = env_int("CHUNK_DAYS", 7)
REQUEST_TIMEOUT = env_int("REQUEST_TIMEOUT", 20)
MAX_RETRIES = env_int("MAX_RETRIES", 5)
DATA_OUT = env_str("DATA_OUT", "docs/data/Policy_Events.json")

# Google Sheets
GOOGLE_CREDENTIALS = os.getenv("GOOGLE_CREDENTIALS", "")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "")

# ---------- Logging ----------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("policy_tracker")

# ---------- HTTP session with retries ----------

def make_session() -> requests.Session:
    sess = requests.Session()
    retry = Retry(
        total=MAX_RETRIES,
        connect=MAX_RETRIES,
        read=MAX_RETRIES,
        backoff_factor=1.5,  # exponential backoff with jitter-ish spacing
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
    sess.mount("https://", adapter)
    sess.mount("http://", adapter)
    sess.headers.update({
        "Accept": "application/json",
        "Accept-Encoding": "gzip, deflate",
        "User-Agent": "policy-tracker/1.0 (+https://github.com/rjgeiser/economic-data-updater)",
    })
    return sess

SESSION = make_session()

# ---------- Helpers ----------

def datestr(d: date) -> str:
    return d.strftime("%Y-%m-%d")

def normalize_agencies(raw) -> List[str]:
    """
    Accepts list[dict|str|None] and returns clean list[str].
    """
    if not raw:
        return []
    out: List[str] = []
    for a in raw:
        if not a:
            continue
        if isinstance(a, dict):
            name = a.get("name") or a.get("short_name") or a.get("title")
        else:
            name = str(a)
        if name:
            name = str(name).strip()
            if name:
                out.append(name)
    # de-dupe while preserving order
    seen = set()
    deduped = []
    for n in out:
        if n not in seen:
            seen.add(n)
            deduped.append(n)
    return deduped

def fr_page(session: requests.Session, start: date, end: date, fr_type: str, page: int) -> Dict:
    """Fetch one page for given date window and type."""
    url = (
        "https://www.federalregister.gov/api/v1/documents.json"
        f"?conditions[publication_date][gte]={datestr(start)}"
        f"&conditions[publication_date][lte]={datestr(end)}"
        f"&conditions[type]={fr_type}"
        "&per_page=100"
        f"&page={page}"
    )
    resp = session.get(url, timeout=REQUEST_TIMEOUT)
    # Even on non-200, we’ll return minimal info to let caller decide
    try:
        data = resp.json()
    except Exception:
        data = {}
    return {"status": resp.status_code, "data": data}

def fetch_window(session: requests.Session, start: date, end: date, fr_type: str) -> List[Dict]:
    """
    Fetch all pages for a date window. If we get repeated timeouts or 5xx, caller
    can decide to split the window smaller. Here we just attempt to iterate pages.
    """
    page = 1
    results: List[Dict] = []

    while True:
        r = fr_page(session, start, end, fr_type, page)
        status = r["status"]
        data = r["data"]

        # Handle outright failures
        if status != 200 or not isinstance(data, dict):
            log.warning("Non-200 or invalid JSON for %s..%s type=%s page=%s status=%s",
                        datestr(start), datestr(end), fr_type, page, status)
            # stop paging this window; let caller decide if we should bisect
            return results

        docs = data.get("results") or []
        if not docs:
            break

        for doc in docs:
            # Build normalized record
            date_str = doc.get("publication_date", "")
            title = doc.get("title", "") or ""
            desc = (doc.get("abstract", "") or "").strip()
            link = doc.get("html_url", "") or ""
            agencies = normalize_agencies(doc.get("agencies", []))
            agency_str = ", ".join(agencies) if agencies else "Unknown"

            results.append({
                "Date": date_str,
                "Type": fr_type,
                "Title": title,
                "Description": desc,
                "Agency": agency_str,
                "Source URL": link,
                # Stable key (useful for updates)
                "Key": f"{date_str}::{title}".strip(),
            })

        # Continue until no more pages
        page += 1

        # If API exposes total_pages, stop cleanly
        total_pages = data.get("total_pages")
        if isinstance(total_pages, int) and page > total_pages:
            break

    return results

def fetch_with_bisection(session: requests.Session, start: date, end: date, fr_type: str) -> List[Dict]:
    """
    Fetch a window, and if we hit failures (timeouts/non-200), bisect the window to reduce payload.
    Stops at 1-day window; if that still fails, we skip that day.
    """
    # First try the whole window
    before = time.time()
    results = fetch_window(session, start, end, fr_type)
    elapsed = time.time() - before
    if results:
        log.info("Fetched %d docs for %s..%s type=%s in %.1fs",
                 len(results), datestr(start), datestr(end), fr_type, elapsed)
        return results

    # If nothing returned, try splitting
    if start >= end:
        log.warning("No results and cannot split further for %s (type=%s)", datestr(start), fr_type)
        return []

    mid = start + (end - start) // 2
    left  = fetch_with_bisection(session, start, mid, fr_type)
    right = fetch_with_bisection(session, mid + timedelta(days=1), end, fr_type)
    return left + right

def daterange_chunks(start: date, end: date, step_days: int) -> List[Tuple[date, date]]:
    """
    Split [start, end] inclusive into windows of at most step_days each.
    """
    out = []
    cur = start
    while cur <= end:
        nxt = min(cur + timedelta(days=step_days - 1), end)
        out.append((cur, nxt))
        cur = nxt + timedelta(days=1)
    return out

# ---------- Persist JSON ----------

def read_existing(path: str) -> Dict[str, Dict]:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            arr = json.load(f)
        return { rec.get("Key") or f"{rec.get('Date','')}::{rec.get('Title','')}" : rec for rec in arr }
    except Exception:
        return {}

def write_json(path: str, records: List[Dict]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)

# ---------- Google Sheets (optional) ----------

def maybe_get_worksheet():
    if not (gspread and GCreds and GOOGLE_CREDENTIALS and GOOGLE_SHEET_ID):
        return None
    creds = GCreds.from_service_account_info(json.loads(GOOGLE_CREDENTIALS), scopes=[
        "https://www.googleapis.com/auth/spreadsheets"
    ])
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(GOOGLE_SHEET_ID)
    # Use or create a 'Policy_Events' sheet
    try:
        ws = sh.worksheet("Policy_Events")
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title="Policy_Events", rows=1000, cols=10)
        ws.append_row(["Date", "Type", "Title", "Description", "Agency", "Source URL", "Key"])
    return ws

def sheet_upsert(ws, new_records: List[Dict]):
    """Upsert by Key."""
    if not ws or not new_records:
        return
    # Build existing map from sheet
    existing = { (r["Date"], r["Title"]): r for r in ws.get_all_records() }
    for rec in new_records:
        k = (rec["Date"], rec["Title"])
        if k not in existing:
            ws.append_row([
                rec.get("Date",""), rec.get("Type",""), rec.get("Title",""),
                rec.get("Description",""), rec.get("Agency",""),
                rec.get("Source URL",""), rec.get("Key","")
            ])
    # (If you need in-place updates, convert to find+update by key; omitted for brevity.)

# ---------- Main ----------

def main():
    log.info("Policy tracker starting: %s .. %s types=%s chunk=%sd timeout=%ss retries=%s",
             datestr(START_DATE), datestr(END_DATE), FR_TYPES, CHUNK_DAYS, REQUEST_TIMEOUT, MAX_RETRIES)

    all_records: Dict[str, Dict] = {}
    windows = daterange_chunks(START_DATE, END_DATE, CHUNK_DAYS)

    for t in FR_TYPES:
        for (w_start, w_end) in windows:
            recs = fetch_with_bisection(SESSION, w_start, w_end, t)
            for r in recs:
                all_records[r["Key"]] = r  # de-dup across chunks

    combined = list(all_records.values())
    combined.sort(key=lambda r: (r.get("Date",""), r.get("Title","")))

    # Merge with existing JSON (preserve/update by Key)
    existing_by_key = read_existing(DATA_OUT)
    existing_by_key.update({ r["Key"]: r for r in combined })
    merged = list(existing_by_key.values())
    merged.sort(key=lambda r: (r.get("Date",""), r.get("Title","")))

    write_json(DATA_OUT, merged)
    log.info("Wrote %d total records to %s", len(merged), DATA_OUT)

    # Optional sheet update
    ws = maybe_get_worksheet()
    if ws:
        # Only push *new* keys compared to sheet
        existing_sheet = { (r["Date"], r["Title"]) for r in ws.get_all_records() }
        new_for_sheet = [r for r in merged if (r["Date"], r["Title"]) not in existing_sheet]
        if new_for_sheet:
            log.info("Appending %d new rows to Google Sheet", len(new_for_sheet))
            sheet_upsert(ws, new_for_sheet)
        else:
            log.info("No new rows to append to Google Sheet")

    log.info("✅ Done.")

if __name__ == "__main__":
    main()
