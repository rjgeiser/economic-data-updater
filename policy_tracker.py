
import requests
import json
import gspread
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
import os

# Load credentials
creds_dict = json.loads(os.environ["GOOGLE_CREDENTIALS"])
creds = Credentials.from_service_account_info(creds_dict, scopes=["https://www.googleapis.com/auth/spreadsheets"])
gc = gspread.authorize(creds)
sheet = gc.open_by_key(os.environ["GOOGLE_SHEET_ID"])
ws = sheet.worksheet("Policy_Events")

# Fetch policy events
start_date = "2021-01-01"
end_date = datetime.utcnow().strftime("%Y-%m-%d")
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

        # Normalize agencies safely: handle None, dicts without 'name', or stray strings
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

# Overwrite Google Sheet
headers = ["Date", "Type", "Title", "Description", "Agency", "Source URL"]
rows = [[r[h] for h in headers] for r in all_results]
ws.clear()
ws.append_row(headers)
ws.append_rows(rows)

# Write to JSON
os.makedirs("docs/data", exist_ok=True)
with open("docs/data/Policy_Events.json", "w") as f:
    json.dump(all_results, f, indent=2)

print(f"✅ Wrote {len(rows)} policy events to Google Sheet and JSON.")
