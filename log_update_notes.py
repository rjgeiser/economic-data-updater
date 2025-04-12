
import os
import json
import gspread
from datetime import datetime
from google.oauth2.service_account import Credentials

def log_update(tab_name, row_count, update_type, note, source_url):
    # Authenticate using environment secrets
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds_dict = json.loads(os.environ["GOOGLE_CREDENTIALS"])
    credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    gc = gspread.authorize(credentials)
    sheet = gc.open_by_key(os.environ["GOOGLE_SHEET_ID"])

    # Ensure the log worksheet exists
    try:
        log_ws = sheet.worksheet("Update_Notes")
    except gspread.exceptions.WorksheetNotFound:
        log_ws = sheet.add_worksheet(title="Update_Notes", rows="100", cols="6")
        log_ws.update("A1:F1", [["Timestamp", "Tab Updated", "Row Count", "Update Type", "Notes", "Source"]])

    # Create the log entry
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    log_ws.append_row([timestamp, tab_name, row_count, update_type, note, source_url])
