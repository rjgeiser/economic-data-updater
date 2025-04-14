
import gspread
import json
from google.oauth2.service_account import Credentials
import os

# Load credentials from GitHub secret
creds_dict = json.loads(os.environ["GOOGLE_CREDENTIALS"])
creds = Credentials.from_service_account_info(creds_dict, scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"])
gc = gspread.authorize(creds)

SHEET_ID = os.environ["GOOGLE_SHEET_ID"]
sheet = gc.open_by_key(SHEET_ID)

# Tabs to export
TABS = [
    "Egg_Prices",
    "Gas_Prices",
    "iPhone_Prices",
    "Car_Prices",
    "Interest_Rates",
    "Stock_Market",
    "Policy_Events"
]

os.makedirs("docs/data", exist_ok=True)

for tab in TABS:
    try:
        ws = sheet.worksheet(tab)
        rows = ws.get_all_records()
        out_path = f"docs/data/{tab}.json"
        with open(out_path, "w") as f:
            json.dump(rows, f, indent=2)
        print(f"✅ Exported {tab} to {out_path}")
    except Exception as e:
        print(f"❌ Failed to export {tab}: {e}")
