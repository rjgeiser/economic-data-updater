
# 🧮 Economic Data Updater

This project automates the collection and logging of economic and public policy data into a central Google Sheet for visualization and analysis.

## 📊 Data Collected

| Sheet Name       | Description                                                | Source            |
|------------------|------------------------------------------------------------|-------------------|
| Egg_Prices       | Avg. price of Grade A large eggs (U.S. city avg)           | FRED/BLS          |
| Gas_Prices       | Regular gasoline price, all formulations (U.S. avg)        | FRED/EIA          |
| Interest_Rates   | 10-Year Treasury constant maturity rate                    | FRED              |
| Stock_Market     | S&P 500 Index daily close                                  | FRED              |
| iPhone_Prices    | MSRP of base model iPhone (128GB)                          | Apple.com         |
| Car_Prices       | MSRP of Toyota RAV4 XLE by model year                      | Toyota Pressroom  |
| Policy_Events    | Proposed federal rules from 10 major U.S. agencies         | Federal Register  |

## 🔁 Automation

This project uses GitHub Actions to automatically update data and metadata:

- **Daily**:
  - FRED and EIA economic data
  - Public policy (`PRORULE`) tracking
  - Price scraping and rollover logic
- **Monthly**:
  - Metadata verification and maintenance

## 📁 Files & Structure

| File                          | Description                                         |
|-------------------------------|-----------------------------------------------------|
| `data_updater.py`            | Updates FRED + EIA data                             |
| `price_scraper.py`           | Scrapes Apple and Toyota prices                    |
| `policy_tracker.py`          | Appends daily policy events from selected agencies |
| `update_metadata_entries.py` | Maintains metadata entries for new sheets          |
| `.github/workflows/`         | Contains all scheduled GitHub Actions workflows    |

## 🛠 Setup

1. Share your Google Sheet with your service account email.
2. Add these GitHub Secrets:
   - `GOOGLE_CREDENTIALS` — your service account JSON (stringified)
   - `GOOGLE_SHEET_ID` — your Google Sheet ID
3. Adjust API keys inside `data_updater.py` if needed.

## 🌐 Visualization (in progress)

This repository will soon integrate with a GitHub Pages frontend to visualize data and annotate economic/policy trends over time.

---

Maintained by [@rjgeiser](https://github.com/rjgeiser) — questions welcome.
