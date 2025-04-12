import requests
import gspread
from datetime import datetime

# Configuration: API keys and date range
FRED_API_KEY = "YOUR_FRED_API_KEY"
EIA_API_KEY = "YOUR_EIA_API_KEY"
START_DATE = "2021-01-01"
END_DATE = datetime.today().strftime("%Y-%m-%d")  # Use today's date for end of range

# Google Sheets setup (using service account credentials)
gc = gspread.service_account(filename="credentials.json")
sh = gc.open("EconomicData")  # replace with your Google Sheet name or use open_by_key

# Define series IDs for each data series
EGG_SERIES_ID = "APU0000708111"   # Average price of eggs (USD/dozen, U.S. city avg, BLS) via FRED
GAS_SERIES_ID = "PET.EMM_EPMR_PTE_NUS_DPG.W"  # Weekly U.S. regular gasoline price (USD/gal) via EIA
INTEREST_SERIES_ID = "DGS10"      # 10-Year Treasury yield (%), daily, via FRED
STOCK_SERIES_ID = "SP500"        # S&P 500 index, daily, via FRED

# Fetch Egg Prices from FRED (from Jan 2021 onward)
fred_url = (f"https://api.stlouisfed.org/fred/series/observations?"
            f"series_id={EGG_SERIES_ID}&observation_start={START_DATE}"
            f"&api_key={FRED_API_KEY}&file_type=json")
egg_response = requests.get(fred_url)
egg_data_json = egg_response.json()
egg_obs = egg_data_json.get("observations", [])
egg_rows = []
for obs in egg_obs:
    date = obs["date"]               # e.g. "2021-01-01"
    value_str = obs["value"]
    if value_str == "." or value_str == "":
        # Skip missing values (if any) to avoid inserting placeholders
        continue
    # Convert numeric value from string to float for proper numeric entry
    value = float(value_str)
    egg_rows.append([date, value])
# Ensure ascending date order (FRED is usually sorted ascending by default)
egg_rows.sort(key=lambda x: x[0])
egg_data = [["Date", "Price (USD per dozen)"]] + egg_rows  # Include header

# Fetch Gas Prices from EIA (Jan 2021 to present)
eia_url = (f"https://api.eia.gov/series/?api_key={EIA_API_KEY}&series_id={GAS_SERIES_ID}"
           f"&start={START_DATE}&end={END_DATE}")
gas_response = requests.get(eia_url)
gas_data_json = gas_response.json()
gas_series = gas_data_json.get("series", [{}])[0]
gas_points = gas_series.get("data", [])
gas_rows = []
for (date_str, value) in gas_points:
    # EIA returns dates as YYYYMMDD for weekly data&#8203;:contentReference[oaicite:5]{index=5}; format to YYYY-MM-DD
    if len(date_str) == 8 and date_str.isdigit():
        date_formatted = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
    else:
        date_formatted = date_str
    # Convert value to float if available, else None for missing/withheld data
    val = None
    if value not in [None, "", ".", "null", "w", "*"]:
        val = float(value)
    gas_rows.append([date_formatted, val])
# Sort by date ascending (EIA data might be in descending order by default)
gas_rows.sort(key=lambda x: x[0])
gas_data = [["Date", "Price (USD per gallon)"]] + gas_rows

# Fetch Interest Rates from FRED (10-Year Treasury yield, daily)
fred_url = (f"https://api.stlouisfed.org/fred/series/observations?"
            f"series_id={INTEREST_SERIES_ID}&observation_start={START_DATE}"
            f"&api_key={FRED_API_KEY}&file_type=json")
rate_response = requests.get(fred_url)
rate_data_json = rate_response.json()
rate_obs = rate_data_json.get("observations", [])
rate_rows = []
for obs in rate_obs:
    date = obs["date"]
    value_str = obs["value"]
    if value_str == "." or value_str == "":
        continue  # skip days with no data (market holidays or missing)
    rate = float(value_str)
    rate_rows.append([date, rate])
rate_rows.sort(key=lambda x: x[0])
interest_data = [["Date", "10-Year Treasury Rate (%)"]] + rate_rows

# Fetch Stock Market data from FRED (S&P 500 index, daily)
fred_url = (f"https://api.stlouisfed.org/fred/series/observations?"
            f"series_id={STOCK_SERIES_ID}&observation_start={START_DATE}"
            f"&api_key={FRED_API_KEY}&file_type=json")
stock_response = requests.get(fred_url)
stock_data_json = stock_response.json()
stock_obs = stock_data_json.get("observations", [])
stock_rows = []
for obs in stock_obs:
    date = obs["date"]
    value_str = obs["value"]
    if value_str == "." or value_str == "":
        continue
    price = float(value_str)
    stock_rows.append([date, price])
stock_rows.sort(key=lambda x: x[0])
stock_data = [["Date", "S&P 500 Index"]] + stock_rows

# Batch update each worksheet in Google Sheets
all_sheets_data = {
    "Egg_Prices": egg_data,
    "Gas_Prices": gas_data,
    "Interest_Rates": interest_data,
    "Stock_Market": stock_data
}
for sheet_name, data in all_sheets_data.items():
    ws = sh.worksheet(sheet_name)
    ws.clear()                 # clear all old data in the worksheet first&#8203;:contentReference[oaicite:6]{index=6}
    ws.update('A1', data)      # write the full dataset starting at cell A1 in one call&#8203;:contentReference[oaicite:7]{index=7}
