
import os
import json
import gspread
from datetime import datetime
from google.oauth2.service_account import Credentials

# Google Sheets auth from GitHub Secrets
scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
creds_dict = json.loads(os.environ["GOOGLE_CREDENTIALS"])
credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
gc = gspread.authorize(credentials)
sheet = gc.open_by_key(os.environ["GOOGLE_SHEET_ID"])

# Ensure Update_Notes worksheet exists
try:
    log_ws = sheet.worksheet("Update_Notes")
except gspread.exceptions.WorksheetNotFound:
    log_ws = sheet.add_worksheet(title="Update_Notes", rows="100", cols="6")
    log_ws.update("A1:F1", [["Timestamp", "Tab Updated", "Row Count", "Update Type", "Notes", "Source"]])

# Log an update row (example for eggs)
def log_update(tab_name, row_count, update_type, note, source_url):
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    log_ws.append_row([timestamp, tab_name, row_count, update_type, note, source_url])

# Example usage
log_update(
    tab_name="Egg_Prices",
    row_count=520,
    update_type="full_overwrite",
    note="FRED data refreshed from Jan 2021 onward",
    source_url="https://fred.stlouisfed.org/series/APU0000708111"
)
