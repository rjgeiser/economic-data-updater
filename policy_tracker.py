
import requests
import gspread
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials

# Setup
scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
credentials = Credentials.from_service_account_file("servive_account.json", scopes=scopes)
gc = gspread.authorize(credentials)
sheet = gc.open_by_key("12_lLnv3t7Om8XHRwFA7spCJ8at282WE7hisxu23gITo")

# Worksheet references
events_ws = sheet.worksheet("Policy_Events")
notes_ws = sheet.worksheet("Update_Notes")
try:
    meta_ws = sheet.worksheet("Metadata")
except:
    meta_ws = sheet.add_worksheet("Metadata", rows=100, cols=10)

# Agency filtering (high-impact shortlist)
agency_ids = [497, 2, 88, 271, 367, 221, 54, 304, 43, 6]

# Date range: only fetch the last 1 day
end_date = datetime.today()
start_date = end_date - timedelta(days=1)
start_date_str = start_date.strftime("%Y-%m-%d")
end_date_str = end_date.strftime("%Y-%m-%d")

# Existing document URLs
existing_urls = [row[4] for row in events_ws.get_all_values()[1:] if len(row) >= 5]

# Fetch new PRORULE documents
new_rows = []
page = 1
print("🔄 Checking for new PRORULEs from top agencies...")
while True:
    url = "https://www.federalregister.gov/api/v1/documents.json"
    params = {
        "order": "newest",
        "page": page,
        "per_page": 100,
        "conditions[publication_date][gte]": start_date_str,
        "conditions[publication_date][lte]": end_date_str,
        "conditions[type][]": "PRORULE"
    }
    for aid in agency_ids:
        params.setdefault("conditions[agency_ids][]", []).append(aid)

    r = requests.get(url, params=params)
    data = r.json()
    results = data.get("results", [])
    if not results:
        break

    for doc in results:
        url = doc.get("html_url", "")
        if url in existing_urls:
            continue
        new_rows.append([
            doc.get("publication_date"),
            doc.get("document_type", "PRORULE"),
            doc.get("title", "").strip(),
            (doc.get("abstract") or "").strip(),
            url
        ])

    print(f"🔎 Page {page}: {len(results)} checked, {len(new_rows)} new.")
    page += 1

# Append rows and update log
if new_rows:
    new_rows.sort(key=lambda r: r[0])
    events_ws.append_rows(new_rows)
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    notes_ws.append_row([
        timestamp,
        "Policy_Events",
        len(new_rows),
        "daily_update",
        "New PRORULEs from selected agencies (past 1 day)",
        "https://www.federalregister.gov/api/v1/documents.json"
    ])
    print(f"✅ Added {len(new_rows)} new PRORULEs.")
else:
    print("✔️ No new PRORULEs to add.")

# Append clean metadata row if not already present
existing_meta = meta_ws.get_all_values()
policy_metadata = [
    "Policy_Events",
    "Proposed rulemakings from 10 key federal agencies",
    "Federal Register",
    "PRORULE",
    "Filtered by agency ID; daily tracker of new entries since Jan 1, 2021",
    "https://www.federalregister.gov"
]

if policy_metadata not in existing_meta:
    meta_ws.append_row(policy_metadata)

