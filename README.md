
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
  - FRED economic data
  - Public policy (`PRORULE`) tracking
  - Price scraping and rollover logic
- **Monthly**:
  - Metadata verification and maintenance

## 🌐 Visualization (in progress)

This repository will soon integrate with a GitHub Pages frontend to visualize data and annotate economic/policy trends over time.

---

Maintained by [@rjgeiser](https://github.com/rjgeiser) — questions welcome, kudos preferred.
