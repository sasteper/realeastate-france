# 🏡 French Property Price Estimator

> *How much is that house in the Loire Valley actually worth?*

A desktop application that estimates property prices in France using real listings scraped from IAD France. Enter a few details about a property — size, energy rating, amenities — and get an instant price estimate with a confidence range. 


## Disclaimer

This project was created solely for educational purposes as part of an academic assignment.  

All data used in this project was collected from publicly available sources.  
The author does not claim ownership of any external data and does not intend to violate any copyright or intellectual property rights.  

This project is not intended for commercial use.

**Author:** Sasha Stepanenko | **License:** MIT

---

## What does it do?

You describe a property:
- surface area, number of bedrooms, energy class (DPE)
- amenities: pool, terrace, garden, public transport nearby, etc.
- property type: apartment, house, or land

The app returns:
- **Two price estimates** — one from a linear regression model, one from a Random Forest
- **A 95% confidence range** — e.g. "between 180,000 and 420,000 EUR"
- **A valuation label** — is this price a bargain, average, or overpriced?
- **5 similar real listings** from the dataset with links to the original IAD France pages


---

## How was it built?

### Step 1 — Collecting the data

There's no public API for French real estate data, so the data was collected by scraping https://www.iadfrance.fr/ (IAD France's listing portal). A custom Python scraper visited 100 pages and collected **2,959 listings**, extracting prices, surface areas, locations, energy ratings, and photos.
Th
To extract richer features, the scraper also read the listing descriptions and used a simple **vocabulary-based approach** — scanning for keywords like *"piscine"* (pool), *"vue mer"* (sea view), *"travaux"* (needs work) — to create binary feature flags. No AI was used for this step, just a dictionary of French words.

After removing duplicates and outliers, **2,837 clean listings** remained.

### Step 2 — Building the model

Property prices follow a roughly log-normal distribution — there are many affordable homes and a long tail of expensive ones. The models were trained to predict the **logarithm of price**, which makes the maths better behaved.

Two models were trained and compared:

| Model | How it works | Test R² |
|-------|-------------|---------|
| **Linear Regression (OLS)** | Fits a straight-line relationship between features and log-price | 0.501 |
| **Random Forest** | Builds 300 decision trees and averages their predictions | 0.504 |

Both achieve R² ≈ 0.50, meaning they explain about half of the variation in prices. The main missing ingredient is **precise location** — neighbourhood and distance to city centre are among the strongest drivers of property prices, but this data wasn't available in the listings.

The single most important predictor is **surface area** (larger = more expensive, unsurprisingly). Other notable findings:
- Land plots are ~78% cheaper than houses of the same size
- Good public transport adds ~25% to price
- A terrace adds ~18%, a pool ~16%
- Properties needing renovation are ~10% cheaper
- Each step down the energy rating scale (A→B→C…) costs ~7%

### Step 3 — The application

The GUI was built with [Flet](https://flet.dev), a Python framework that produces native desktop apps. It features:
- Input validation (no way to break the app from the UI)
- Dual-model results with prediction intervals
- SQLite database for saving estimation history
- Application logs accessible from a dedicated tab
- A Lottie animation because why not

---

## Installation

**Requirements:** Python 3.11+, pip

```bash
# Clone the repository
git clone https://github.com/yourusername/french-property-estimator
cd french-property-estimator

# Create virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the app
python mojaaplkacja/run_app.py
```

---

## Project structure

```
french-property-estimator/
├── mojaaplkacja/
│   ├── data/
│   │   ├── iad_clean.csv       # cleaned dataset (2,837 listings)
│   │   ├── history.db          # SQLite estimation history
│   │   └── app.log             # application logs
│   ├── models/
│   │   ├── ols_model.pkl       # trained OLS model
│   │   ├── rf_model.pkl        # trained Random Forest model
│   │   └── model_meta.pkl      # feature names, metrics, percentiles
│   ├── src/
│   │   ├── app/
│   │   │   └── main.py         # Flet GUI application
│   │   ├── db/
│   │   │   └── database.py     # SQLite manager
│   │   ├── model/
│   │   │   ├── predictor.py    # OLS + RF prediction wrapper
│   │   │   └── similar.py      # similar listings finder
│   │   └── utils/
│   │       └── validators.py   # input validation
│   ├── tests/
│   │   └── test_all.py         # 67 unit tests
│   ├── docs/
│   │   └── documentation.html  # API documentation (pdoc)
│   └── run_app.py              # entry point
├── notebooks/
│   ├── 01_eda.ipynb            # exploratory data analysis
│   └── 02_modelling.ipynb      # model building and diagnostics
├── scraper/
│   └── newparser.py            # IAD France web scraper
├── REPORT.md                   # analytical report
└── README.md                   # this file
```

---

## Running the tests

```bash
cd french-property-estimator
python -m pytest mojaaplkacja/tests/test_all.py -v
```

67 tests covering input validators, database operations, model predictions, and the similar listings finder.

---

## Limitations and future work

- **R² ≈ 0.50** — location data would substantially improve accuracy
- The scraper collected a snapshot in time; prices change seasonally
- The vocabulary-based feature extraction doesn't handle negations (*"sans piscine"* = no pool)
- A more granular property type taxonomy (studio, villa, farmhouse…) could improve predictions

---

## Technologies used

`Python` · `Flet` · `scikit-learn` · `statsmodels` · `pandas` · `BeautifulSoup4` · `SQLite` · `pytest` · `pdoc`


## Disclaimer

This project is intended for educational purposes only.  
It does not aim to violate any copyright or intellectual property rights.  
All data used in this project comes from publicly available sources.  

This project is not intended for commercial use.
``
