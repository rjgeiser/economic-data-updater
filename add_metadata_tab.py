
import gspread
from google.oauth2.service_account import Credentials
import os
import json

# Set up Google credentials from environment variable
scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
creds_dict = json.loads(os.environ["GOOGLE_CREDENTIALS"])
credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
gc = gspread.authorize(credentials)

# Open the Google Sheet by ID
sheet = gc.open_by_key(os.environ["GOOGLE_SHEET_ID"])

# Delete existing Metadata worksheet if it exists
try:
    existing = sheet.worksheet("Metadata")
    sheet.del_worksheet(existing)
except gspread.exceptions.WorksheetNotFound:
    pass

# Create a new Metadata worksheet
meta_ws = sheet.add_worksheet(title="Metadata", rows="20", cols="6")

# Define metadata content
metadata = [
    ["Sheet Name", "Description", "Source", "Units", "Notes", "Link"],
    ["Egg_Prices", "Avg price of Grade A large eggs (U.S. city avg)", "FRED/BLS", "USD per dozen", "Series APU0000708111", "https://fred.stlouisfed.org/series/APU0000708111"],
    ["Gas_Prices", "Regular gasoline price, all formulations (U.S. avg)", "EIA", "USD per gallon", "Series PET.EMM_EPMR_PTE_NUS_DPG.W", "https://www.eia.gov/dnav/pet/pet_pri_gnd_dcus_nus_w.htm"],
    ["Interest_Rates", "10-Year Treasury constant maturity rate", "FRED", "Percent", "Series DGS10", "https://fred.stlouisfed.org/series/DGS10"],
    ["Stock_Market", "S&P 500 Index daily close", "FRED", "Index level", "Series SP500", "https://fred.stlouisfed.org/series/SP500"]
]

# Upload the metadata to the sheet
meta_ws.update("A1", metadata)

print("✅ Metadata sheet created and populated.")
