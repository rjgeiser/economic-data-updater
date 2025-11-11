#!/usr/bin/env python3
"""
Policy tracker: fetches Federal Register documents for a date window, writes JSON,
and (optionally) syncs to a Google Sheet.

Environment variables (all optional unless noted):
  START_DATE         e.g., '2025-10-01' (default: 30 days ago)
  END_DATE           e.g., '2025-11-11' (default: today)
  FR_TYPES           comma list of document types, e.g. 'PRORULE,NOTICE' (default: 'PRORULE')
  CHUNK_DAYS         integer chunk size, e.g. '7' (default: 7)
  REQUEST_TIMEOUT    per-request timeout seconds, e.g. '20' (default: 20)
  MAX_RETRIES        retry count for transient errors (default: 5)
  DATA_OUT           output JSON path (default: 'docs/data/Policy_Events.json')

Optional Google Sheets sync:
  GOOGLE_CREDENTIALS  JSON string of a service account
  GOOGLE_SHEET_ID     target Google Sheet ID (not URL)

Notes:
- Robust retry with backoff (429/5xx/connect/read) using a single Session.
- Paginates per_page=100 until no more results.
- Normalizes 'agencies' to a clean 'Agency' string (handles None/missing names).
- If Sheet sync is enabled, ensures headers are set exactly and appends new rows
  by de-duplicating on (Date, Title) keys. Avoids get_all_records() header pitfalls.
"""

import json
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ==== Logging ====
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("policy-tracker")

# ==== Config ====
def getenv_str(name: str, default: str) -> str:
    val = os.getenv(name)
    return val if val not in (None, "") else default

def getenv_int(name: str, default: int) -> int:
    try:
        return int(getenv_str(name, str(default)))
    except ValueError:
        return default

DATE_FMT = "%Y-%m-%d"

def parse_date(s: str) -> datetime:
    return datetime.strptime(s, DATE_FMT)

def fmt_date(d: datetime) -> str:
    return d.strftime(DATE_FMT)

today = datetime.utcnow().date()
default_start = (today - timedelta(days=30)).strftime(DATE_FMT)
default_end = today.strftime(DATE_FMT)

START_DATE = getenv_str("START_DATE", default_start)
END_DATE = getenv_str("END_DATE", default_end)
FR_TYPES = [t.strip() for t in getenv_str("FR_TYPES", "PRORULE").split(",") if t.strip()]
CHUNK_DAYS = getenv_int("CHUNK_DAYS", 7)
REQUEST_TIMEOUT = getenv_int("REQUEST_TIMEOUT", 20)
MAX_RETRIES = getenv_int("MAX_RETRIES", 5)
DATA_OUT = getenv_str("DATA_OUT", "docs/data/Policy_Events.json")

GOOGLE_CREDENTIALS = os.getenv("GOOGLE_CREDENTIALS")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")

EXPECTED_HEADERS = ["Date", "Type", "Title", "Description", "Agency", "Source URL"]

# ==== HTTP Session with retries ====
def build_session(timeout: int, max_retries: int) -> requests.Session:
    """
    Create a requests Session with resilient retry policy for common transient failures.
    """
    session = requests.Session()
    retry = Retry(
        total=max_retries,
        connect=max_retries,
        read=max_retries,
        backoff_factor=0.8,              # exponential backoff with jitter-ish spacing
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
        raise_on_status=False,
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_maxsize=10)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    # Store default timeout on the session
    session.request = _with_timeout(session.request, timeout)
    return session

def _with_timeout(request_fn, timeout):
    def wrapped(method, url, **kwargs):
        if "timeout" not in kwargs:
            kwargs["timeout"] = timeout
        return request_fn(method, url, **kwargs)
    return wrapped

# ==== Federal Register fetch ====
BASE_URL = "https://www.federalregister.gov/api/v1/documents.json"

def normalize_agency_names(raw_list) -> List[str]:
    """
    Given doc.get('agencies'), return a clean list of agency names (strings).
    Handles None, empty, dicts without name keys, or str.
    """
    if not raw_list:
        return []
    out: List[str] = []
    for a in raw_list:
        if not a:
            continue
        name = None
        if isinstance(a, dict):
            name = a.get("name") or a.get("short_name") or a.get("title")
        else:
            name = str(a)
        if name:
            name = str(name).strip()
            if name:
                out.append(name)
    # de-dup preserving order
    seen = set()
    uniq = []
    for n in out:
        if n not in seen:
            seen.add(n)
            uniq.append(n)
    return uniq

def fetch_window(session: requests.Session, start: str, end: str, doc_type: str) -> List[Dict]:
    """
    Fetch one date window for one doc_type, with pagination.
    Returns list of normalized records.
    """
    page = 1
    per_page = 100
    acc: List[Dict] = []
    while True:
        params = {
            "conditions[publication_date][gte]": start,
            "conditions[publication_date][lte]": end,
            "conditions[type]": doc_type,
            "per_page": per_page,
            "page": page,
            # NOTE: add more filters if needed, e.g., agencies, topics, etc.
        }
        resp = session.get(BASE_URL, params=params)
        if resp.status_code != 200:
            log.warning("Non-200 from FR API: %s %s", resp.status_code, resp.text[:200])
            break
        data = resp.json()
        docs = data.get("results", []) or []
        if not docs:
            break
        for doc in docs:
            date = doc.get("publication_date", "") or ""
            title = doc.get("title", "") or ""
            desc = (doc.get("abstract", "") or "").strip()
            link = doc.get("html_url", "") or ""
            agency_names = normalize_agency_names(doc.get("agencies", []))
            agency_str = ", ".join(agency_names) if agency_names else "Unknown"

            acc.append({
                "Date": date,
                "Type": doc_type,
                "Title": title,
                "Description": desc,
                "Agency": agency_str,
                "Source URL": link,
            })
        page += 1
    return acc

def daterange_chunks(start: datetime, end: datetime, days: int) -> List[Tuple[str, str]]:
    """
    Inclusive date chunks [start..end], each of length <= days.
    """
    chunks: List[Tuple[str, str]] = []
    cur = start
    while cur <= end:
        nxt = min(cur + timedelta(days=days - 1), end)
        chunks.append((fmt_date(cur), fmt_date(nxt)))
        cur = nxt + timedelta(days=1)
    return chunks

# ==== File I/O ====
def ensure_parent_dir(path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)

def write_json(records: List[Dict], path: str):
    ensure_parent_dir(path)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)

# ==== Google Sheets sync (optional) ====
def sync_google_sheet(records: List[Dict], sheet_id: str, credentials_json: str):
    import gspread
    from google.oauth2.service_account import Credentials

    # Auth
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/drive",
    ]
    info = json.loads(credentials_json)
    creds = Credentials.from_service_account_info(info, scopes=scope)
    gc = gspread.authorize(creds)

    # Open sheet
    sh = gc.open_by_key(sheet_id)

    # Worksheet name fixed
    title = "Policy_Events"
    try:
        ws = sh.worksheet(title)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=title, rows=1000, cols=10)

    # Ensure headers exactly once in row 1
    current = ws.get_all_values()
    if not current:
        ws.update("A1:F1", [EXPECTED_HEADERS])
        current = [EXPECTED_HEADERS]
    else:
        first = current[0] if current else []
        if first != EXPECTED_HEADERS:
            # Overwrite header row to match expected (avoids duplicates/blank header issues)
            ws.update("A1:F1", [EXPECTED_HEADERS])

    # Build existing keys (Date, Title) from sheet to avoid duplicates
    values = ws.get_all_values()
    existing_keys = set()
    if len(values) > 1:
        for row in values[1:]:
            # pad row to at least 3 cols
            row = (row + ["", "", ""])[:3]
            k = (row[0], row[2])  # Date, Title
            if any(k):
                existing_keys.add(k)

    # Prepare rows to append (in expected column order)
    rows = []
    for r in records:
        key = (r.get("Date", ""), r.get("Title", ""))
        if key in existing_keys:
            continue
        rows.append([r.get(h, "") for h in EXPECTED_HEADERS])

    if rows:
        ws.append_rows(rows, value_input_option="RAW")
        log.info("Appended %d new rows to Google Sheet", len(rows))
    else:
        log.info("No new rows to append to Google Sheet")

# ==== Main ====
def main():
    start_dt = parse_date(START_DATE)
    end_dt = parse_date(END_DATE)
    log.info(
        "Policy tracker starting: %s .. %s types=%s chunk=%sd timeout=%ss retries=%s",
        START_DATE, END_DATE, FR_TYPES, CHUNK_DAYS, REQUEST_TIMEOUT, MAX_RETRIES
    )

    session = build_session(timeout=REQUEST_TIMEOUT, max_retries=MAX_RETRIES)

    all_records: List[Dict] = []
    chunks = daterange_chunks(start_dt, end_dt, CHUNK_DAYS)
    for doc_type in FR_TYPES:
        for a, b in chunks:
            try:
                records = fetch_window(session, a, b, doc_type)
                if records:
                    all_records.extend(records)
                    log.info("Fetched %d docs for %s..%s type=%s", len(records), a, b, doc_type)
                else:
                    # If truly no results for that day-range, it's fine; just note it.
                    # We don't recursively split below 1 day to avoid API hammering.
                    # The earlier error you saw ("No results and cannot split further") was benign info.
                    pass
            except requests.ReadTimeout:
                log.warning("Read timeout for %s..%s type=%s", a, b, doc_type)
            except requests.RequestException as e:
                log.warning("RequestException for %s..%s type=%s: %s", a, b, doc_type, e)

    # Sort & write
    # Sort by Date desc then Title asc for stability
    all_records.sort(key=lambda r: (r.get("Date", ""), r.get("Title", "")))
    write_json(all_records, DATA_OUT)
    log.info("Wrote %d total records to %s", len(all_records), DATA_OUT)

    # Optional Google Sheets sync
    if GOOGLE_CREDENTIALS and GOOGLE_SHEET_ID:
        try:
            sync_google_sheet(all_records, GOOGLE_SHEET_ID, GOOGLE_CREDENTIALS)
        except Exception as e:
            # Don't fail the entire job just because Sheet sync had a shape/header issue
            log.error("Google Sheets sync failed: %s", e)
            # Re-raise if you want the CI to fail here:
            # raise

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log.exception("Fatal error")
        sys.exit(1)
