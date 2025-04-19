
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
    url = f"https://www.federalregister.gov/api/v1/documents.json?conditions[publication_date][gte]={start_date}&conditions[publication_date][lte]={end_date}&conditions[type]=PRORULE&per_page=100&page={page}"
    res = requests.get(url)
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
        agencies = [a.get("name") for a in doc.get("agencies", [])]
        agency_str = ", ".join(agencies) if agencies else "Unknown"

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
