
import requests
import json
import gspread
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
import os

# Load credentials
creds_dict = json.loads(os.environ["GOOGLE_CREDENTIALS"])
creds = Credentials.from_service_account_info(creds_dict, scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"])
gc = gspread.authorize(creds)
sheet = gc.open_by_key(os.environ["GOOGLE_SHEET_ID"])
ws = sheet.worksheet("Policy_Events")

# Fetch new policy events
today = datetime.utcnow().date()
yesterday = today - timedelta(days=1)

url = f"https://www.federalregister.gov/api/v1/documents.json?conditions[publication_date][gte]={yesterday}&conditions[type]=PRORULE&per_page=100"

res = requests.get(url)
data = res.json()
results = []

for doc in data.get("results", []):
    date = doc.get("publication_date", "")
    title = doc.get("title", "")
    desc = doc.get("abstract", "") or ""
    link = doc.get("html_url", "")
    agencies = [a.get("name") for a in doc.get("agencies", [])]
    agency_str = ", ".join(agencies) if agencies else "Unknown"

    results.append({
        "Date": date,
        "Type": "PRORULE",
        "Title": title,
        "Description": desc.strip(),
        "Agency": agency_str,
        "Source URL": link
    })

# Write to JSON file for dashboard
os.makedirs("docs/data", exist_ok=True)
with open("docs/data/Policy_Events.json", "w") as f:
    json.dump(results, f, indent=2)

print(f"✅ {len(results)} policy events written to docs/data/Policy_Events.json")
