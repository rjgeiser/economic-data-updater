import requests
import json
import gspread
from datetime import datetime
from google.oauth2.service_account import Credentials
import os

def get_existing_records(ws):
    # Assumes headers are present
    records = ws.get_all_records()
    # Index by key (date + title)
    return {(r["Date"], r["Title"]): r for r in records}

def get_existing_json(path):
    if os.path.exists(path):
        with open(path, "r") as f:
            return {(r["Date"], r["Title"]): r for r in json.load(f)}
    else:
        return {}

def fetch_api_data(start_date, end_date):
    page = 1
    all_results = []
    while True:
        url = (
            "https://www.federalregister.gov/api/v1/documents.json"
            f"?conditions[publication_date][gte]={start_date}"
            f"&conditions[publication_date][lte]={end_date}"
            "&conditions[type]=PRORULE"
            "&per_page=100"
            f"&page={page}"
        )
        res = requests.get(url, timeout=20)
        if res.status_code != 200:
            break
        docs = res.json().get("results", [])
        if not docs:
            break
        for doc in docs:
            date = doc.get("publication_date", "")
            title = doc.get("title", "")
            desc = doc.get("abstract", "") or ""
            link = doc.get("html_url", "")
            raw_agencies = doc.get("agencies", []) or []
            agency_names = []
            for a in raw_agencies:
                if not a:
                    continue
                if isinstance(a, dict):
                    name = a.get("name") or a.get("short_name") or a.get("title")
                else:
                    name = str(a)
                if name:
                    name = str(name).strip()
                    if name:
                        agency_names.append(name)
            agency_str = ", ".join(agency_names) if agency_names else "Unknown"
            all_results.append({
                "Date": date,
                "Type": "PRORULE",
                "Title": title,
                "Description": desc.strip(),
                "Agency": agency_str,
                "Source URL": link
            })
        page += 1
    return all_results

def main():
    # Load credentials
    creds_dict = json.loads(os.environ["GOOGLE_CREDENTIALS"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=["https://www.googleapis.com/auth/spreadsheets"])
    gc = gspread.authorize(creds)
    sheet = gc.open_by_key(os.environ["GOOGLE_SHEET_ID"])
    ws = sheet.worksheet("Policy_Events")
    try:
        changelog_ws = sheet.worksheet("Policy_Events_Changelog")
    except Exception:
        changelog_ws = sheet.add_worksheet(title="Policy_Events_Changelog", rows=1000, cols=10)

    # Load existing sheet and JSON
    existing_sheet = get_existing_records(ws)
    json_path = "docs/data/Policy_Events.json"
    existing_json = get_existing_json(json_path)

    # Fetch new data from API
    start_date = "2021-01-01"
    end_date = datetime.utcnow().strftime("%Y-%m-%d")
    api_results = fetch_api_data(start_date, end_date)

    # Track new and changed events
    new_entries = []
    changed_entries = []
    headers = ["Date", "Type", "Title", "Description", "Agency", "Source URL"]

    for entry in api_results:
        key = (entry["Date"], entry["Title"])
        old_entry = existing_sheet.get(key) or existing_json.get(key)
        if old_entry:
            # Check for changes
            changes = []
            for h in headers:
                if entry[h] != old_entry.get(h, ""):
                    changes.append({
                        "Key": key,
                        "Field": h,
                        "Old": old_entry.get(h, ""),
                        "New": entry[h],
                        "Timestamp": datetime.utcnow().isoformat()
                    })
            if changes:
                changed_entries.append({
                    "Key": key,
                    "Changes": changes
                })
                # Update the entry in sheet and json
                # Sheet logic will be handled below
        else:
            # New entry
            new_entries.append(entry)

    # Append new entries to Google Sheet, do not rewrite
    # Find next row index to append to
    if new_entries:
        new_rows = [[r[h] for h in headers] for r in new_entries]
        ws.append_rows(new_rows)

    # Update changed entries in Google Sheet
    if changed_entries:
        # We'll update cell values only for the changed fields
        sheet_records = ws.get_all_records()
        for changed in changed_entries:
            key = changed["Key"]
            for i, r in enumerate(sheet_records):
                if (r["Date"], r["Title"]) == key:
                    for change in changed["Changes"]:
                        col_idx = headers.index(change["Field"]) + 1  # gspread is 1-based
                        ws.update_cell(i + 2, col_idx, change["New"]) # add 2: 1 for header, 1 for 0-index
    # Log changelog in changelog sheet
    changelog_headers = ["Date", "Title", "Field", "Old", "New", "Timestamp"]
    changelog_rows = []
    for changed in changed_entries:
        for change in changed["Changes"]:
            changelog_rows.append([
                change["Key"][0], change["Key"][1],
                change["Field"], change["Old"], change["New"], change["Timestamp"]
            ])

    # Only append changelog if there were changes
    if changelog_rows:
        changelog_ws.append_rows(changelog_rows)

    # Update JSON: read old, update new and changed, append only new
    existing_data = list(existing_json.values())
    new_keys = { (r["Date"], r["Title"]): r for r in existing_data }
    for r in new_entries:
        new_keys[(r["Date"], r["Title"])] = r
    for changed in changed_entries:
        key = changed["Key"]
        if key in new_keys:
            for change in changed["Changes"]:
                new_keys[key][change["Field"]] = change["New"]
    # Write updated JSON
    os.makedirs("docs/data", exist_ok=True)
    with open(json_path, "w") as f:
        json.dump(list(new_keys.values()), f, indent=2)

    print(f"✅ Added {len(new_entries)} new events, updated {len(changed_entries)} events.")
    print(f"Change log entries: {len(changelog_rows)}")

if __name__ == "__main__":
    main()