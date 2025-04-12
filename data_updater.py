
import os
import json
import requests
import gspread
import time
from datetime import datetime
from google.oauth2.service_account import Credentials
from log_update_notes import log_update

# API keys from environment
FRED_API_KEY = os.environ["FRED_API_KEY"]
EIA_API_KEY = os.environ["EIA_API_KEY"]
START_DATE = "2021-01-01"
END_DATE = datetime.today().strftime("%Y-%m-%d")

# Google Sheets auth
scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
creds_dict = json.loads(os.environ["GOOGLE_CREDENTIALS"])
credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
gc = gspread.authorize(credentials)
sh = gc.open_by_key(os.environ["GOOGLE_SHEET_ID"])

# Helper to update a sheet
def update_sheet(sheet_name, header, rows, note, source_url):
    ws = sh.worksheet(sheet_name)
    ws.clear()
    data = [header] + rows
    ws.update("A1", data)
    log_update(
        tab_name=sheet_name,
        row_count=len(rows),
        update_type="full_overwrite",
        note=note,
        source_url=source_url
    )

# Egg Prices
egg_url = f"https://api.stlouisfed.org/fred/series/observations?series_id=APU0000708111&observation_start={START_DATE}&api_key={FRED_API_KEY}&file_type=json"
egg_obs = requests.get(egg_url).json().get("observations", [])
egg_rows = [[obs["date"], float(obs["value"])] for obs in egg_obs if obs["value"] not in [".", ""]]
egg_rows.sort(key=lambda x: x[0])
update_sheet("Egg_Prices", ["Date", "Price (USD per dozen)"], egg_rows,
             "FRED data refreshed from Jan 2021", "https://fred.stlouisfed.org/series/APU0000708111")

def fetch_eia_data_with_retry(url, retries=3, delay=3):
    for attempt in range(1, retries + 1):
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt} failed: {e}")
            if attempt < retries:
                time.sleep(delay * attempt)
            else:
                raise

# Gas Prices (with retry)
eia_url = f"https://api.eia.gov/series/?api_key={EIA_API_KEY}&series_id=PET.EMM_EPMR_PTE_NUS_DPG.W&start={START_DATE.replace('-', '')}&end={END_DATE.replace('-', '')}"

try:
    eia_json = fetch_eia_data_with_retry(eia_url)
    print("✅ Fetched EIA data. Top-level keys:", list(eia_json.keys()))
    gas_series = eia_json.get("series", [{}])[0].get("data", [])
    gas_data = []

    for date_str, value in gas_series:
        if len(date_str) == 8:
            formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        else:
            formatted_date = date_str
        if value not in ["", ".", "null", "w", "*"]:
            gas_data.append([formatted_date, float(value)])

    gas_data.sort(key=lambda x: x[0])

    update_sheet("Gas_Prices", ["Date", "Price (USD per gallon)"], gas_data,
                 "EIA gas price data refreshed from Jan 2021",
                 "https://www.eia.gov/dnav/pet/pet_pri_gnd_dcus_nus_w.htm")

except Exception as e:
    print("❌ Final error after retries:", str(e))

# Interest Rates
rate_url = f"https://api.stlouisfed.org/fred/series/observations?series_id=DGS10&observation_start={START_DATE}&api_key={FRED_API_KEY}&file_type=json"
rate_obs = requests.get(rate_url).json().get("observations", [])
rate_rows = [[obs["date"], float(obs["value"])] for obs in rate_obs if obs["value"] not in [".", ""]]
rate_rows.sort(key=lambda x: x[0])
update_sheet("Interest_Rates", ["Date", "10-Year Treasury Rate (%)"], rate_rows,
             "FRED interest rate data refreshed from Jan 2021", "https://fred.stlouisfed.org/series/DGS10")

# Stock Market
stock_url = f"https://api.stlouisfed.org/fred/series/observations?series_id=SP500&observation_start={START_DATE}&api_key={FRED_API_KEY}&file_type=json"
stock_obs = requests.get(stock_url).json().get("observations", [])
stock_rows = [[obs["date"], float(obs["value"])] for obs in stock_obs if obs["value"] not in [".", ""]]
stock_rows.sort(key=lambda x: x[0])
update_sheet("Stock_Market", ["Date", "S&P 500 Index"], stock_rows,
             "FRED S&P 500 data refreshed from Jan 2021", "https://fred.stlouisfed.org/series/SP500")
