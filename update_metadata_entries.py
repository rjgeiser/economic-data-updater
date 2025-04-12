
import gspread
from google.oauth2.service_account import Credentials

# Google Sheets authentication
scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
credentials = Credentials.from_service_account_file("credentials.json", scopes=scopes)
gc = gspread.authorize(credentials)
sheet = gc.open_by_key("12_lLnv3t7Om8XHRwFA7spCJ8at282WE7hisxu23gITo")

# Get metadata worksheet
meta_ws = sheet.worksheet("Metadata")
existing_rows = meta_ws.get_all_values()
existing_set = {tuple(row) for row in existing_rows}

# New metadata entries
new_metadata = [
    ["iPhone_Prices", "MSRP of base model iPhone with 128GB storage", "Apple", "USD", "Daily scrape from Apple.com with rollover if unchanged", "https://www.apple.com/iphone/"],
    ["Car_Prices", "MSRP of Toyota RAV4 XLE by model year", "Toyota", "USD", "Annual MSRP tracked daily with rollover; pulled from pressroom releases", "https://pressroom.toyota.com/releases/"]
]

# Append if not already present
for row in new_metadata:
    if tuple(row) not in existing_set:
        meta_ws.append_row(row)

print("✅ Metadata entries added or already exist.")
