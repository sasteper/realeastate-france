# Analytical Report: French Property Price Estimator

**Author:** Sasha Stepanenko  
**License:** MIT  
**Dataset:** IAD France / beauxvillages.com  
**Date:** June 2026

---

## 1. Data Collection

### Source and method

Data was scraped from the IAD France real estate portal (beauxvillages.com) using a custom Python scraper built with `requests` and `BeautifulSoup4`. The scraper navigated paginated listing pages using a `?start=N` URL parameter and extracted both listing-level and detail-page features for each property.

To ensure robustness against network interruptions, the scraper implemented a checkpoint/resume system: progress was saved to `progress.json` every 20 listings, and the output was written incrementally to `iad_full.csv`.

### Collection results

| Metric | Value |
|--------|-------|
| Pages scraped | 100 |
| Raw listings collected | 2,959 |
| Listings after cleaning | 2,837 |
| Drop rate | 4.1% |

### Features extracted

Core fields: `price`, `surface_m2`, `bedrooms`, `city`, `department`, `postal_code`, `dpe_class`, `image_count`.

Vocabulary-based binary flags extracted from listing descriptions (classical dictionary method, no LLM):
`has_pool`, `has_terrace`, `has_view`, `has_garden`, `has_transport`, `is_quiet`, `has_fireplace`, `needs_work`, `has_sea`, `has_parking`.

Derived features: `price_per_m2`, `amenity_score`, `description_len`, `log_surface`.

---

## 2. Exploratory Data Analysis

### Price distribution

The raw price distribution is strongly right-skewed, with a long tail of high-value properties. The median price is approximately **237,000 EUR**, while the mean is pulled upward to around **303,000 EUR** by luxury outliers.

| Percentile | Price (EUR) |
|------------|-------------|
| P10 | 99,000 |
| P25 | 160,000 |
| P50 | ~237,000 |
| P75 | 371,000 |
| P90 | 555,480 |

A log transformation of price (`log_price = log1p(price)`) yields a near-normal distribution (mean ≈ 12.39, std ≈ 0.67), confirming it as the appropriate modelling target.

### Surface area

Surface ranges from 10 m² to several thousand m², with significant right skew. Log-transformation of surface (`log_surface = log1p(surface_m2)`) normalises the distribution and produces the strongest single predictor of price (Pearson r ≈ 0.62).

### Property types

| Type | Count | Share |
|------|-------|-------|
| House | ~1,590 | 56% |
| Apartment | ~980 | 35% |
| Land | ~267 | 9% |

Land listings are substantially cheaper than houses and apartments at comparable surface areas, which is reflected in the large negative coefficient for `type_land` in the final model.

### DPE energy class

Energy class distributions show most listings cluster around classes C–E. Better energy ratings (A, B) correlate with higher prices. DPE score is encoded ordinally (A=1 … G=7) for modelling purposes.

### Amenity flags

Binary amenity flags show clear price differentiation. Properties with `has_transport` command the largest average premium (~24%), followed by `has_terrace` (~18%) and `has_pool` (~16%).

`needs_work` is associated with an ~10% price discount on average.

---

## 3. Variable Transformations

| Variable | Transformation | Reason |
|----------|---------------|--------|
| `price` | `log1p()` | Right-skewed; normalises residuals |
| `surface_m2` | `log1p()` → `log_surface` | Right-skewed; linearises price–area relationship |
| `dpe_class` | Ordinal encoding A=1…G=7 → `dpe_score` | Preserves order; avoids dummy variable proliferation |
| `property_type` | One-hot: `type_apartment`, `type_land` (house = reference) | Nominal variable |
| `image_count` | Clamped to [3, 13] | Removes outlier effect of listings with extreme photo counts |
| Amenity flags | Binary 0/1 from vocabulary search | Classical NLP feature extraction |

### Descriptive statistics (model-ready dataset, n = 2,837)

| Feature | Mean | Std | Min | Max |
|---------|------|-----|-----|-----|
| log_surface | 4.52 | 0.89 | 2.30 | 8.52 |
| bedrooms | 2.81 | 1.54 | 0 | 12 |
| dpe_score | 3.84 | 1.42 | 1 | 7 |
| image_count | 8.3 | 2.9 | 3 | 13 |
| has_pool | 0.17 | — | 0 | 1 |
| has_terrace | 0.31 | — | 0 | 1 |
| has_transport | 0.22 | — | 0 | 1 |
| type_land | 0.09 | — | 0 | 1 |

---

## 4. Model Building History

### Train/test split

The dataset was split 80/20 (stratified by property type):
- Training set: **2,269 observations**
- Test set: **568 observations**

### Candidate features

Initial modelling included 20+ candidate features. Features were selected based on:
1. Correlation with `log_price`
2. Statistical significance (p < 0.05) in OLS
3. Low variance inflation factor (VIF < 5) to avoid multicollinearity

Features removed during selection: raw `surface_m2` (replaced by `log_surface`), `postal_code` (too many categories, leakage risk), `description_len` (marginal contribution after amenity flags included), `has_sea` / `has_parking` (p > 0.05 in full model).

### OLS Regression — diagnostics

The final OLS model passes standard regression diagnostics:

- **Durbin-Watson = 2.00** — no autocorrelation in residuals ✅
- **Residual std (σ) = 0.472** on log scale — typical prediction error ±47% in price space
- **Heteroskedasticity** — present (confirmed by Breusch-Pagan test), expected without location variables
- **Normality** — Jarque-Bera rejects normality due to heavy tails, but CLT applies at n > 2,000 ✅
- **VIF** — all features < 5, no problematic multicollinearity ✅

10-fold cross-validation: R² = 0.471 ± 0.044

### Random Forest — diagnostics

- Max depth: unlimited (default), min samples leaf = 5 (tuned)
- 300 estimators
- Residual std (σ) = 0.471 on log scale
- 10-fold cross-validation: R² = 0.470 ± 0.031 (lower variance than OLS)
- Slight overfitting observed on training set (train R² ≈ 0.73 vs test R² ≈ 0.50)

---

## 5. Final Model

Both models were retained in the application to allow dual-model comparison.

### OLS coefficients (final model, 14 predictors + intercept)

| Variable | Coefficient | p-value | Interpretation |
|----------|-------------|---------|----------------|
| const | +9.374 | 0.000 | baseline |
| **log_surface** | **+0.503** | 0.000 | strongest predictor; +10% surface → +5% price |
| type_land | **−1.487** | 0.000 | land −78% vs house |
| has_transport | +0.220 | 0.000 | +25% premium |
| has_terrace | +0.168 | 0.000 | +18% premium |
| type_apartment | +0.161 | 0.000 | +17% vs house |
| has_pool | +0.148 | 0.000 | +16% premium |
| has_view | +0.139 | 0.000 | +15% premium |
| has_garden | +0.133 | 0.000 | +14% premium |
| needs_work | −0.105 | 0.000 | −10% discount |
| is_quiet | +0.098 | 0.000 | +10% premium |
| dpe_score | −0.072 | 0.000 | per A→B step −7% |
| has_fireplace | +0.067 | 0.040 | +7% premium |
| image_count | +0.061 | 0.000 | more photos = higher price |
| bedrooms | +0.039 | 0.001 | per bedroom +4% |

### Test-set performance

| Metric | OLS | Random Forest |
|--------|-----|---------------|
| R² (test) | **0.501** | **0.504** |
| RMSE (log) | 0.472 | 0.471 |
| CV R² | 0.471 ± 0.044 | 0.470 ± 0.031 |

### Prediction intervals

95% prediction intervals are computed using the log-scale residual standard deviation (σ):

```
price_low  = exp(log_pred − 1.96 × σ)
price_high = exp(log_pred + 1.96 × σ)
```

### Valuation labels

| Label | Threshold |
|-------|-----------|
| Okazyjna (bargain) | price ≤ P25 = 160,000 EUR |
| Przeciętna (average) | 160,000 < price ≤ 371,000 EUR |
| Za wysoka (overpriced) | price > P75 = 371,000 EUR |

### Limitations

- R² ≈ 0.50 — approximately half of price variance explained. The primary missing predictor is **precise location** (neighbourhood, distance to city centre). IAD France does not expose coordinates in listing HTML.
- Amenity flags rely on vocabulary matching in French text; compound or negated expressions (e.g. *"sans piscine"*) are not handled.
- Model trained on listings from a single scrape window — temporal price trends are not captured.
