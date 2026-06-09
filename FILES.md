# Project Files Description

**Project:** IAD France Property Price Estimator  
**Author:** Sasha Stepanenko  
**License:** MIT

---

## Root

| File | Description |
|------|-------------|
| `README.md` | Popular-science project overview in English (GitHub landing page) |
| `REPORT.md` | Analytical report: data collection, EDA, model diagnostics, final model |
| `FILES.md` | This file — description of all files in the project |

---

## mojaaplkacja/

| File | Description |
|------|-------------|
| `run_app.py` | Entry point — launches the Flet desktop application |

### mojaaplkacja/src/app/

| File | Description |
|------|-------------|
| `main.py` | Main Flet GUI application. Contains `PropertyEstimatorApp` class with four tabs: Estimator, History, Logs, About. Handles user input, validation, prediction display, and navigation. |
| `header_anim.gif` | Lottie-converted animated GIF used as decorative header animation |
| `__init__.py` | Package marker |

### mojaaplkacja/src/model/

| File | Description |
|------|-------------|
| `predictor.py` | `Predictor` class — loads serialised OLS and Random Forest models, builds feature vectors, computes 95% prediction intervals, assigns valuation labels (bargain / average / overpriced) |
| `similar.py` | `SimilarListingsFinder` class — finds the 5 most similar listings from the cleaned dataset based on surface, bedrooms, property type and price proximity |
| `__init__.py` | Package marker |

### mojaaplkacja/src/db/

| File | Description |
|------|-------------|
| `database.py` | `DatabaseManager` class — manages SQLite database for estimation history and application logs. Auto-creates tables on first run. |
| `__init__.py` | Package marker |

### mojaaplkacja/src/utils/

| File | Description |
|------|-------------|
| `validators.py` | Input validation functions: `validate_surface`, `validate_bedrooms`, `validate_image_count`. Each returns `(is_valid, parsed_value, error_message)`. |
| `__init__.py` | Package marker |

### mojaaplkacja/models/

| File | Description |
|------|-------------|
| `ols_model.pkl` | Serialised OLS regression model (statsmodels). Trained on 2,269 observations, test R² = 0.501 |
| `rf_model.pkl` | Serialised Random Forest model (scikit-learn, 300 estimators). Test R² = 0.504 |
| `model_meta.pkl` | Model metadata: feature names, residual standard deviations, price percentiles (P25, P75), train/test sizes |

### mojaaplkacja/data/

| File | Description |
|------|-------------|
| `iad_clean.csv` | Cleaned dataset — 2,837 IAD France property listings with 20+ features. Used for similar listings lookup. |
| `history.db` | SQLite database with estimation history and application logs (auto-created at runtime) |
| `app.log` | Plain-text application log file (auto-created at runtime) |

### mojaaplkacja/tests/

| File | Description |
|------|-------------|
| `test_all.py` | 67 unit tests covering all modules: `validators` (30 tests), `DatabaseManager` (12 tests), `Predictor` (13 tests), `SimilarListingsFinder` (9 tests). Uses `pytest` with parametrize and named `ids`. |

### mojaaplkacja/docs/

| File | Description |
|------|-------------|
| `documentation.html` | Full API documentation generated with `pdoc` from docstrings. Covers all four modules in a single self-contained HTML file. |

---

## notebooks/

| File | Description |
|------|-------------|
| `01_eda.ipynb` | Exploratory Data Analysis notebook — data cleaning decisions, outlier removal, missing value imputation, distributions, correlation analysis, amenity flag impact |
| `02_modelling.ipynb` | Regression modelling notebook — OLS and Random Forest, diagnostic plots (residuals, Q-Q, Scale-Location, VIF), 10-fold cross-validation, permutation importance, model serialisation |

---

## scraper/

| File | Description |
|------|-------------|
| `newparser.py` | IAD France web scraper — `ListingPageParser`, `DetailPageParser`, `IADScraper` classes. Paginated crawl with checkpoint/resume system. Extracts prices, surface areas, locations, DPE classes, image counts, and vocabulary-based binary amenity flags from listing descriptions. |
| `progress.json` | Scraper checkpoint file — tracks last scraped page for resume after interruption |
| `iad_full.csv` | Raw scraped data before cleaning (2,959 listings) |

---

## How to run

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python mojaaplkacja/run_app.py

# Run tests
python -m pytest mojaaplkacja/tests/test_all.py -v
```
