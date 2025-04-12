
import os
import json
import requests
from datetime import datetime
from bs4 import BeautifulSoup
import gspread
from google.oauth2.service_account import Credentials

# Google Sheets authentication using GitHub Secrets
scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
creds_dict = json.loads(os.environ["GOOGLE_CREDENTIALS"])
credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
gc = gspread.authorize(credentials)

# Open the Google Sheet using its unique ID
sheet = gc.open_by_key(os.environ["GOOGLE_SHEET_ID"])

def get_current_iphone_price():
    url = "https://www.apple.com/shop/buy-iphone/iphone-15"
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, "html.parser")
    try:
        price_tag = soup.find("span", class_="as-price-currentprice")
        price_text = price_tag.get_text().strip()
        price = float(price_text.replace("$", "").replace(",", ""))
        return price
    except Exception:
        return None

def get_current_rav4_price():
    url = "https://www.edmunds.com/toyota/rav4/2024/xle/"
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, "html.parser")
    try:
        price_tag = soup.find("div", class_="overview-cost__pricing-summary").find("span")
        price_text = price_tag.get_text().strip()
        price = float(price_text.replace("$", "").replace(",", ""))
        return price
    except Exception:
        return None

def update_price_sheet(sheet_name, current_price):
    ws = sheet.worksheet(sheet_name)
    records = ws.get_all_values()
    today = datetime.today().strftime("%Y-%m-%d")
    if records and records[-1][1] == str(current_price):
        ws.append_row([today, current_price])
    elif not records or records[-1][1] != str(current_price):
        ws.append_row([today, current_price])

def main():
    iphone_price = get_current_iphone_price()
    if iphone_price:
        update_price_sheet("iPhone_Prices", iphone_price)

    rav4_price = get_current_rav4_price()
    if rav4_price:
        update_price_sheet("Car_Prices", rav4_price)

main()
