
import os
import json
import requests
import datetime
import gspread
from google.oauth2.service_account import Credentials

FRED_API_KEY = os.getenv("FRED_API_KEY")
EIA_API_KEY = os.getenv("EIA_API_KEY")
GOOGLE_CREDENTIALS = os.getenv("GOOGLE_CREDENTIALS")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")

credentials = Credentials.from_service_account_file("economic-data-tracker-456517-cbb6da83ab25.json", scopes=...)
gc = gspread.authorize(credentials)
sheet = gc.open_by_key(GOOGLE_SHEET_ID)

def fetch_fred_series(series_id):
    url = f"https://api.stlouisfed.org/fred/series/observations?series_id={series_id}&api_key={FRED_API_KEY}&file_type=json"
    res = requests.get(url)
    data = res.json()
    return {item['date']: item['value'] for item in data['observations'] if item['value'] not in ('', '.', 'NaN')}

def fetch_eia_series(series_id):
    url = f"https://api.eia.gov/series/?api_key={EIA_API_KEY}&series_id={series_id}"
    res = requests.get(url)
    data = res.json()
    return {entry[0]: entry[1] for entry in data['series'][0]['data']}

def update_sheet(tab_name, headers, rows):
    ws = sheet.worksheet(tab_name)
    ws.clear()
    ws.append_row(headers)
    for row in rows:
        ws.append_row(row)

def update_egg_prices():
    data = fetch_fred_series("APU0000708111")
    rows = [[k, float(v)] for k, v in sorted(data.items())]
    update_sheet("Egg_Prices", ["Date", "Price (USD)"], rows)

def update_gas_prices():
    states = {
        "California": "EMM_EPMR_PTE_SCA_DPG",
        "Texas": "EMM_EPMRU_PTE_STX_DPG"
    }
    merged = {}
    for state, series_id in states.items():
        data = fetch_eia_series(series_id)
        for date, val in data.items():
            date_fmt = f"{date[:4]}-{date[4:6]}-{date[6:]}" if len(date) == 8 else date
            merged.setdefault(date_fmt, {})[state] = val
    rows = []
    for date in sorted(merged.keys()):
        row = [date] + [merged[date].get(state, "") for state in states]
        rows.append(row)
    update_sheet("Gas_Prices", ["Date"] + list(states.keys()), rows)

def update_interest_rates():
    series = {
        "Fed Funds Rate": "FEDFUNDS",
        "30Y Mortgage Rate": "MORTGAGE30US"
    }
    data = {label: fetch_fred_series(sid) for label, sid in series.items()}
    all_dates = set(d for dset in data.values() for d in dset)
    rows = []
    for date in sorted(all_dates):
        row = [date] + [data[label].get(date, "") for label in series]
        rows.append(row)
    update_sheet("Interest_Rates", ["Date"] + list(series.keys()), rows)

def update_stock_market():
    indices = {
        "S&P 500": "SP500",
        "DJIA": "DJIA",
        "NASDAQ": "NASDAQCOM"
    }
    data = {label: fetch_fred_series(sid) for label, sid in indices.items()}
    all_dates = set(d for dset in data.values() for d in dset)
    rows = []
    for date in sorted(all_dates):
        row = [date] + [data[label].get(date, "") for label in indices]
        rows.append(row)
    update_sheet("Stock_Market", ["Date"] + list(indices.keys()), rows)

if __name__ == "__main__":
    update_egg_prices()
    update_gas_prices()
    update_interest_rates()
    update_stock_market()
