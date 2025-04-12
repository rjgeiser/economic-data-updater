# Economic Data Updater

This project automates the retrieval and daily updating of key U.S. economic indicators and product prices to a centralized Google Sheet. The data includes:

- 🥚 Average price of eggs (FRED/BLS)
- ⛽ Regular gasoline prices (EIA)
- 📈 S&P 500 Index (FRED)
- 💵 10-Year Treasury Yield (FRED)
- 📱 iPhone base model price (scraped from Apple)
- 🚗 Toyota RAV4 XLE MSRP (scraped from Edmunds)
- 🗂️ Automatically generated metadata for transparency

## Project Structure

```
.
├── data_updater.py         # Updates FRED & EIA data (Eggs, Gas, Interest, Stock)
├── price_scraper.py        # Scrapes iPhone and RAV4 prices daily
├── add_metadata_tab.py     # Creates or updates a Metadata sheet with source info
├── .github
│   └── workflows
│       ├── update.yml            # Runs full data updater daily
│       ├── price-scraper.yml     # Runs price scraper daily
│       └── update-metadata.yml   # Runs metadata refresher monthly
├── requirements.txt
└── README.md
```

## Setup Instructions

1. **Google Cloud Setup**
   - Create a service account and download the JSON credentials file.
   - Share your Google Sheet with the service account email (Editor access).
   - Set the `GOOGLE_CREDENTIALS` as a GitHub Secret (paste the full JSON content).
   - Set `GOOGLE_SHEET_ID` as another secret (from your sheet's URL).

2. **GitHub Actions Setup**
   - Upload all files to your repository.
   - Workflows will trigger based on schedule or manual invocation from the Actions tab.

3. **Manual Script Testing (Optional)**
   Run locally using:
   ```bash
   pip install gspread google-auth requests beautifulsoup4
   python data_updater.py
   python price_scraper.py
   ```

## Sheet Metadata

All tabs are explained in a dedicated `Metadata` sheet within the workbook, including:
- Source links
- Units of measurement
- Series ID
- Data provider

## Contact

Maintained by Roy Geiser (rjgeiser). For questions or contributions, please open an issue or reach out directly.
