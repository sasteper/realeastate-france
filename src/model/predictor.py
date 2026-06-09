"""
Property price prediction module.

Wraps trained OLS (statsmodels) and Random Forest (scikit-learn) models,
handles feature engineering, prediction, confidence intervals, and
price valuation labels.

Author: [Twoje Imię i Nazwisko]
License: MIT
"""

import logging
import pickle
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Optional

import numpy as np
import pandas as pd
import statsmodels.api as sm

logger = logging.getLogger(__name__)

DPE_MAP: dict[str, int] = {"A": 1, "B": 2, "C": 3, "D": 4, "E": 5, "F": 6, "G": 7}
PROPERTY_TYPES = ("apartment", "house", "land")
DPE_CLASSES = ("A", "B", "C", "D", "E", "F", "G")

# Price percentiles from training data — used for valuation labels
_PRICE_P25_DEFAULT = 160_000.0
_PRICE_P75_DEFAULT = 371_000.0


@dataclass
class PredictionResult:
    """
    Container for a single price prediction.

    Attributes:
        model_name: Name of the model used ('OLS' or 'RandomForest').
        price_estimate: Point estimate in EUR.
        price_low: Lower bound of the 95% prediction interval.
        price_high: Upper bound of the 95% prediction interval.
        valuation_label: 'Okazyjna', 'Przeciętna', or 'Za wysoka'.
        log_price_estimate: Estimate in log-space (internal).
    """

    model_name: str
    price_estimate: float
    price_low: float
    price_high: float
    valuation_label: str
    log_price_estimate: float = field(repr=False)


class Predictor:
    """
    Unified interface for property price prediction using OLS and Random Forest.

    Loads serialised models from disk on initialisation and exposes
    a single :meth:`predict` method that returns point estimates,
    95% prediction intervals, and a qualitative valuation label.

    Args:
        models_dir: Directory containing ``ols_model.pkl``,
            ``rf_model.pkl``, and ``model_meta.pkl``.
    """

    def __init__(self, models_dir: Optional[Path] = None) -> None:
        self._models_dir = Path(models_dir) if models_dir else (
            Path(__file__).parent.parent.parent / "models"
        )
        self._load_models()
        logger.info("Predictor loaded from %s", self._models_dir)

    def _load_models(self) -> None:
        """Load OLS, RF and metadata from pickle files."""
        with open(self._models_dir / "ols_model.pkl", "rb") as f:
            ols_data = pickle.load(f)
        with open(self._models_dir / "rf_model.pkl", "rb") as f:
            rf_data = pickle.load(f)
        with open(self._models_dir / "model_meta.pkl", "rb") as f:
            self._meta = pickle.load(f)

        self._ols = ols_data["model"]
        self._rf = rf_data["model"]
        self._features: list[str] = self._meta["features"]
        self._ols_std: float = self._meta["ols_resid_std"]
        self._rf_std: float = self._meta["rf_resid_std"]
        self._price_p25: float = self._meta.get("price_p25", _PRICE_P25_DEFAULT)
        self._price_p75: float = self._meta.get("price_p75", _PRICE_P75_DEFAULT)

    def _build_feature_vector(
        self,
        surface_m2: float,
        bedrooms: int,
        dpe_class: str,
        image_count: int,
        property_type: Literal["apartment", "house", "land"],
        amenities: dict[str, int],
    ) -> pd.DataFrame:
        """
        Construct a single-row DataFrame matching the training feature schema.

        Args:
            surface_m2: Property area in m².
            bedrooms: Number of bedrooms.
            dpe_class: Energy class letter (A–G).
            image_count: Number of listing photos.
            property_type: Property category string.
            amenities: Dict mapping amenity flag names to 0/1 integers.

        Returns:
            Single-row DataFrame ready for model inference.
        """
        row: dict[str, float] = {
            "log_surface": float(np.log1p(surface_m2)),
            "bedrooms": float(bedrooms),
            "dpe_score": float(DPE_MAP.get(dpe_class, 4)),
            "image_count": float(max(3, min(image_count, 13))),
            "has_pool": float(amenities.get("has_pool", 0)),
            "has_terrace": float(amenities.get("has_terrace", 0)),
            "has_view": float(amenities.get("has_view", 0)),
            "has_garden": float(amenities.get("has_garden", 0)),
            "needs_work": float(amenities.get("needs_work", 0)),
            "has_transport": float(amenities.get("has_transport", 0)),
            "is_quiet": float(amenities.get("is_quiet", 0)),
            "has_fireplace": float(amenities.get("has_fireplace", 0)),
            "type_apartment": float(property_type == "apartment"),
            "type_land": float(property_type == "land"),
        }
        return pd.DataFrame([row], columns=self._features)

    @staticmethod
    def _valuation_label(
        price: float, p25: float, p75: float
    ) -> str:
        """
        Classify price as bargain, average, or overpriced.

        Args:
            price: Estimated price in EUR.
            p25: 25th percentile of training prices.
            p75: 75th percentile of training prices.

        Returns:
            One of 'Okazyjna 🟢', 'Przeciętna 🟡', 'Za wysoka 🔴'.
        """
        if price <= p25:
            return "Okazyjna 🟢"
        if price <= p75:
            return "Przeciętna 🟡"
        return "Za wysoka 🔴"

    @staticmethod
    def _clamp_log_price(log_price: float) -> float:
        """Clamp log-price to a sensible range before back-transformation."""
        return float(np.clip(log_price, 9.0, 15.5))

    def predict(
        self,
        surface_m2: float,
        bedrooms: int,
        dpe_class: str,
        image_count: int,
        property_type: Literal["apartment", "house", "land"],
        amenities: dict[str, int],
        model: Literal["OLS", "RandomForest"] = "OLS",
    ) -> PredictionResult:
        """
        Predict property price and compute a 95% prediction interval.

        Args:
            surface_m2: Property area in m² (must be > 0).
            bedrooms: Number of bedrooms (≥ 0).
            dpe_class: DPE energy class ('A'–'G').
            image_count: Number of listing images (3–13).
            property_type: 'apartment', 'house', or 'land'.
            amenities: Dict of boolean feature flags (0 or 1).
            model: Which model to use — 'OLS' or 'RandomForest'.

        Returns:
            :class:`PredictionResult` with point estimate, interval, and label.

        Raises:
            ValueError: If ``surface_m2`` ≤ 0 or ``dpe_class`` is invalid.
        """
        if surface_m2 <= 0:
            raise ValueError(f"surface_m2 must be positive, got {surface_m2}")
        if dpe_class not in DPE_MAP:
            raise ValueError(f"Invalid DPE class: {dpe_class!r}")

        X = self._build_feature_vector(
            surface_m2, bedrooms, dpe_class, image_count, property_type, amenities
        )

        if model == "OLS":
            Xc = sm.add_constant(X, has_constant="add")
            log_pred = float(self._ols.predict(Xc).iloc[0])
            std = self._ols_std
            name = "OLS"
        else:
            log_pred = float(self._rf.predict(X)[0])
            std = self._rf_std
            name = "RandomForest"

        log_pred = self._clamp_log_price(log_pred)
        log_low = self._clamp_log_price(log_pred - 1.96 * std)
        log_high = self._clamp_log_price(log_pred + 1.96 * std)

        price = float(np.expm1(log_pred))
        price_low = float(np.expm1(log_low))
        price_high = float(np.expm1(log_high))

        # Round to nearest 500 EUR for cleaner display
        price = round(price / 500) * 500
        price_low = round(price_low / 500) * 500
        price_high = round(price_high / 500) * 500

        label = self._valuation_label(price, self._price_p25, self._price_p75)

        logger.debug(
            "Prediction [%s]: %.0f EUR [%.0f – %.0f] — %s",
            name, price, price_low, price_high, label,
        )

        return PredictionResult(
            model_name=name,
            price_estimate=price,
            price_low=price_low,
            price_high=price_high,
            valuation_label=label,
            log_price_estimate=log_pred,
        )

    def predict_both(
        self,
        surface_m2: float,
        bedrooms: int,
        dpe_class: str,
        image_count: int,
        property_type: str,
        amenities: dict[str, int],
    ) -> tuple[PredictionResult, PredictionResult]:
        """
        Run both OLS and Random Forest predictions in one call.

        Returns:
            Tuple of (OLS result, RandomForest result).
        """
        ols_result = self.predict(
            surface_m2, bedrooms, dpe_class, image_count,
            property_type, amenities, model="OLS"
        )
        rf_result = self.predict(
            surface_m2, bedrooms, dpe_class, image_count,
            property_type, amenities, model="RandomForest"
        )
        return ols_result, rf_result

    @property
    def feature_names(self) -> list[str]:
        """List of feature names expected by the models."""
        return list(self._features)

    @property
    def model_metrics(self) -> dict:
        """Dictionary of test-set metrics for both models."""
        return {
            "OLS R² (test)": self._meta.get("test_r2_ols"),
            "RF  R² (test)": self._meta.get("test_r2_rf"),
            "Train size":    self._meta.get("train_size"),
            "Test size":     self._meta.get("test_size"),
        }
