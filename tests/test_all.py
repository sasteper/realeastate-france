"""
Unit tests for IAD France Property Price Estimator.

Covers: validators, DatabaseManager, Predictor, SimilarListingsFinder.

Author: Sasha Stepanenko
License: MIT
"""

import math
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

import sys
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

from utils.validators import validate_bedrooms, validate_image_count, validate_surface
from db.database import DatabaseManager


# ===========================================================================
# validators — validate_surface
# ===========================================================================

@pytest.mark.parametrize("value,expected_ok", [
    ("85",      True),
    ("85.5",    True),
    ("85,5",    True),   # comma as decimal separator
    ("1",       True),   # min > 0
    ("5000",    True),   # max boundary
    ("0",       False),
    ("-1",      False),
    ("5001",    False),  # above max 5000
    ("abc",     False),
    ("",        False),
    ("  ",      False),
], ids=[
    "valid-integer",
    "valid-float-dot",
    "valid-float-comma",
    "min-boundary",
    "max-boundary",
    "zero",
    "negative",
    "above-max",
    "text",
    "empty-string",
    "whitespace-only",
])
def test_validate_surface(value, expected_ok):
    ok, parsed, msg = validate_surface(value)
    assert ok == expected_ok
    if ok:
        assert parsed is not None
        assert isinstance(parsed, float)
        assert parsed > 0
        assert msg == ""
    else:
        assert parsed is None
        assert msg != ""


# ===========================================================================
# validators — validate_bedrooms
# ===========================================================================

@pytest.mark.parametrize("value,expected_ok", [
    ("0",    True),
    ("3",    True),
    ("20",   True),
    ("-1",   False),
    ("21",   False),
    ("abc",  False),
    ("",     False),
    ("2.9",  True),    # int(float()) truncation
    ("  4 ", True),    # stripped whitespace
], ids=[
    "zero-bedrooms",
    "typical-3",
    "max-boundary",
    "negative",
    "above-max",
    "text",
    "empty",
    "float-truncated",
    "whitespace-padded",
])
def test_validate_bedrooms(value, expected_ok):
    ok, parsed, msg = validate_bedrooms(value)
    assert ok == expected_ok
    if ok:
        assert isinstance(parsed, int)
        assert 0 <= parsed <= 20


# ===========================================================================
# validators — validate_image_count
# ===========================================================================

@pytest.mark.parametrize("value,expected_ok", [
    ("1",    True),
    ("10",   True),
    ("30",   True),
    ("0",    False),
    ("31",   False),
    ("-5",   False),
    ("abc",  False),
    ("",     False),
    ("5.9",  True),    # truncated to int
], ids=[
    "min-boundary",
    "typical",
    "max-boundary",
    "zero-invalid",
    "above-max",
    "negative",
    "text",
    "empty",
    "float-truncated",
])
def test_validate_image_count(value, expected_ok):
    ok, parsed, msg = validate_image_count(value)
    assert ok == expected_ok
    if ok:
        assert isinstance(parsed, int)
        assert 1 <= parsed <= 30


def test_validators_always_return_three_tuple():
    """All validators must return (bool, value_or_None, str)."""
    for fn, val in [
        (validate_surface,     "50"),
        (validate_bedrooms,    "2"),
        (validate_image_count, "5"),
    ]:
        result = fn(val)
        assert len(result) == 3
        assert isinstance(result[0], bool)
        assert isinstance(result[2], str)


# ===========================================================================
# DatabaseManager
# ===========================================================================

AMENITIES_STUB = {
    "has_pool": 0, "has_terrace": 1, "has_view": 0, "has_garden": 0,
    "has_transport": 1, "is_quiet": 0, "has_fireplace": 0, "needs_work": 0,
}


@pytest.fixture()
def tmp_db(tmp_path):
    return DatabaseManager(tmp_path / "test.db")


def test_db_creates_file(tmp_path):
    db_path = tmp_path / "new.db"
    DatabaseManager(db_path)
    assert db_path.exists()


def test_db_tables_exist(tmp_db):
    with sqlite3.connect(tmp_db.db_path) as conn:
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
    assert "estimations" in tables
    assert "logs" in tables


def test_db_save_and_retrieve_estimation(tmp_db):
    tmp_db.save_estimation(
        surface_m2=80.0, bedrooms=2, dpe_class="C", image_count=8,
        property_type="apartment", amenities=AMENITIES_STUB,
        model_used="OLS", price_estimate=240000.0,
        price_low=180000.0, price_high=320000.0,
        valuation_label="Przeciętna 🟡",
    )
    rows = tmp_db.get_history(10)
    assert len(rows) == 1
    assert rows[0]["surface_m2"] == pytest.approx(80.0)
    assert rows[0]["model_used"] == "OLS"
    assert rows[0]["price_estimate"] == pytest.approx(240000.0)


def test_db_history_newest_first(tmp_db):
    for price in [100000.0, 200000.0, 300000.0]:
        tmp_db.save_estimation(
            surface_m2=60.0, bedrooms=1, dpe_class="D", image_count=5,
            property_type="apartment", amenities=AMENITIES_STUB,
            model_used="RF", price_estimate=price,
            price_low=price * 0.8, price_high=price * 1.2,
            valuation_label="Okazyjna 🟢",
        )
    rows = tmp_db.get_history(10)
    prices = [r["price_estimate"] for r in rows]
    assert prices == sorted(prices, reverse=True)


def test_db_clear_history(tmp_db):
    tmp_db.save_estimation(
        surface_m2=50.0, bedrooms=1, dpe_class="E", image_count=3,
        property_type="land", amenities=AMENITIES_STUB,
        model_used="OLS", price_estimate=90000.0,
        price_low=70000.0, price_high=110000.0,
        valuation_label="Okazyjna 🟢",
    )
    deleted = tmp_db.clear_history()
    assert deleted == 1
    assert tmp_db.get_history() == []


def test_db_clear_history_returns_count(tmp_db):
    for _ in range(5):
        tmp_db.save_estimation(
            surface_m2=70.0, bedrooms=2, dpe_class="B", image_count=10,
            property_type="house", amenities=AMENITIES_STUB,
            model_used="OLS", price_estimate=300000.0,
            price_low=220000.0, price_high=400000.0,
            valuation_label="Za wysoka 🔴",
        )
    assert tmp_db.clear_history() == 5


def test_db_log_action(tmp_db):
    tmp_db.log_action("TEST_ACTION", "some details", level="INFO")
    logs = tmp_db.get_logs(10)
    actions = [lg["action"] for lg in logs]
    assert "TEST_ACTION" in actions


def test_db_log_levels(tmp_db):
    tmp_db.log_action("A", "info",    level="INFO")
    tmp_db.log_action("B", "warning", level="WARNING")
    tmp_db.log_action("C", "error",   level="ERROR")
    logs = tmp_db.get_logs(10)
    levels = {lg["level"] for lg in logs}
    assert {"INFO", "WARNING", "ERROR"}.issubset(levels)


def test_db_get_history_limit(tmp_db):
    for i in range(10):
        tmp_db.save_estimation(
            surface_m2=float(50 + i), bedrooms=1, dpe_class="D", image_count=4,
            property_type="apartment", amenities=AMENITIES_STUB,
            model_used="OLS", price_estimate=150000.0,
            price_low=100000.0, price_high=200000.0,
            valuation_label="Okazyjna 🟢",
        )
    assert len(tmp_db.get_history(3)) == 3
    assert len(tmp_db.get_history(100)) == 10


def test_db_get_logs_limit(tmp_db):
    for i in range(8):
        tmp_db.log_action(f"EVT_{i}", "details")
    assert len(tmp_db.get_logs(3)) == 3


def test_db_empty_history_returns_list(tmp_db):
    assert tmp_db.get_history() == []


def test_db_save_returns_int_id(tmp_db):
    row_id = tmp_db.save_estimation(
        surface_m2=90.0, bedrooms=3, dpe_class="B", image_count=12,
        property_type="house", amenities=AMENITIES_STUB,
        model_used="OLS", price_estimate=350000.0,
        price_low=250000.0, price_high=450000.0,
        valuation_label="Za wysoka 🔴",
    )
    assert isinstance(row_id, int)
    assert row_id > 0


# ===========================================================================
# Predictor — tested against real pkl models
# ===========================================================================

AMENITIES_FULL = {
    "has_pool": 0, "has_terrace": 1, "has_view": 0, "has_garden": 1,
    "has_transport": 1, "is_quiet": 1, "has_fireplace": 0, "needs_work": 0,
}

MODELS_DIR = Path(__file__).parent.parent / "models"


@pytest.fixture(scope="module")
def predictor():
    from model.predictor import Predictor
    return Predictor(MODELS_DIR)


def test_predictor_loads(predictor):
    assert predictor is not None


def test_predictor_predict_ols_returns_result(predictor):
    from model.predictor import PredictionResult
    result = predictor.predict(
        surface_m2=85.0, bedrooms=2, dpe_class="C", image_count=10,
        property_type="apartment", amenities=AMENITIES_FULL, model="OLS",
    )
    assert isinstance(result, PredictionResult)


def test_predictor_predict_rf_returns_result(predictor):
    from model.predictor import PredictionResult
    result = predictor.predict(
        surface_m2=85.0, bedrooms=2, dpe_class="C", image_count=10,
        property_type="apartment", amenities=AMENITIES_FULL, model="RandomForest",
    )
    assert isinstance(result, PredictionResult)


def test_predictor_price_positive(predictor):
    result = predictor.predict(
        surface_m2=85.0, bedrooms=2, dpe_class="C", image_count=10,
        property_type="apartment", amenities=AMENITIES_FULL, model="OLS",
    )
    assert result.price_estimate > 0


def test_predictor_pi_ordered(predictor):
    """price_low <= price_estimate <= price_high."""
    result = predictor.predict(
        surface_m2=85.0, bedrooms=2, dpe_class="C", image_count=10,
        property_type="apartment", amenities=AMENITIES_FULL, model="OLS",
    )
    assert result.price_low <= result.price_estimate <= result.price_high


def test_predictor_predict_both_returns_two(predictor):
    ols_r, rf_r = predictor.predict_both(
        surface_m2=100.0, bedrooms=3, dpe_class="B", image_count=12,
        property_type="house", amenities=AMENITIES_FULL,
    )
    assert ols_r.model_name == "OLS"
    assert rf_r.model_name == "RandomForest"


def test_predictor_invalid_surface_raises(predictor):
    with pytest.raises(ValueError, match="surface_m2"):
        predictor.predict(
            surface_m2=0.0, bedrooms=2, dpe_class="C", image_count=10,
            property_type="apartment", amenities=AMENITIES_FULL, model="OLS",
        )


def test_predictor_invalid_dpe_raises(predictor):
    with pytest.raises(ValueError, match="DPE"):
        predictor.predict(
            surface_m2=85.0, bedrooms=2, dpe_class="Z", image_count=10,
            property_type="apartment", amenities=AMENITIES_FULL, model="OLS",
        )


@pytest.mark.parametrize("surface,bedrooms,dpe,ptype", [
    (15.0,  0, "G", "land"),
    (85.0,  2, "C", "apartment"),
    (200.0, 4, "A", "house"),
    (500.0, 6, "B", "house"),
], ids=["tiny-land", "typical-apartment", "large-house", "very-large-house"])
def test_predictor_various_inputs(predictor, surface, bedrooms, dpe, ptype):
    result = predictor.predict(
        surface_m2=surface, bedrooms=bedrooms,
        dpe_class=dpe, image_count=5,
        property_type=ptype, amenities=AMENITIES_FULL, model="OLS",
    )
    assert result.price_estimate > 0
    assert result.price_low <= result.price_estimate <= result.price_high


@pytest.mark.parametrize("price,expected_label", [
    (100000.0, "Okazyjna 🟢"),
    (250000.0, "Przeciętna 🟡"),
    (500000.0, "Za wysoka 🔴"),
], ids=["bargain", "average", "overpriced"])
def test_predictor_valuation_label_thresholds(predictor, price, expected_label):
    label = predictor._valuation_label(price, predictor._price_p25, predictor._price_p75)
    assert label == expected_label


def test_predictor_feature_names_list(predictor):
    assert isinstance(predictor.feature_names, list)
    assert len(predictor.feature_names) > 0


def test_predictor_model_metrics_keys(predictor):
    m = predictor.model_metrics
    assert "OLS R² (test)" in m
    assert "RF  R² (test)" in m


# ===========================================================================
# SimilarListingsFinder
# ===========================================================================

@pytest.fixture()
def mock_finder(tmp_path):
    from model.similar import SimilarListingsFinder
    data = pd.DataFrame({
        "price":         [150000, 220000, 310000, 95000, 430000],
        "surface_m2":    [60.0,   85.0,   110.0,  45.0,  140.0],
        "bedrooms":      [1,      2,      3,      1,     4],
        "property_type": ["apartment","apartment","house","apartment","house"],
        "city":          ["Paris","Lyon","Lyon","Paris","Marseille"],
        "dpe_class":     ["C","D","B","E","A"],
        "url":           ["http://a","http://b","http://c","http://d","http://e"],
        "title":         ["T1","T2","T3","T4","T5"],
        "price_per_m2":  [2500.0, 2588.0, 2818.0, 2111.0, 3071.0],
    })
    csv_path = tmp_path / "iad_clean.csv"
    data.to_csv(csv_path, index=False)
    return SimilarListingsFinder(csv_path)


def test_finder_returns_list(mock_finder):
    results = mock_finder.find(
        surface_m2=80.0, bedrooms=2,
        property_type="apartment", price_estimate=200000.0, n=3,
    )
    assert isinstance(results, list)


def test_finder_respects_n(mock_finder):
    results = mock_finder.find(
        surface_m2=80.0, bedrooms=2,
        property_type="apartment", price_estimate=200000.0, n=2,
    )
    assert len(results) <= 2


def test_finder_result_has_required_fields(mock_finder):
    results = mock_finder.find(
        surface_m2=80.0, bedrooms=2,
        property_type="apartment", price_estimate=200000.0, n=3,
    )
    for r in results:
        assert hasattr(r, "price")
        assert hasattr(r, "surface_m2")
        assert hasattr(r, "city")
        assert hasattr(r, "similarity_pct")
        assert hasattr(r, "url")


def test_finder_similarity_pct_range(mock_finder):
    results = mock_finder.find(
        surface_m2=80.0, bedrooms=2,
        property_type="apartment", price_estimate=200000.0, n=5,
    )
    for r in results:
        assert 0 <= r.similarity_pct <= 100


@pytest.mark.parametrize("surface,bedrooms,ptype,price", [
    (60.0,  1, "apartment", 150000.0),
    (110.0, 3, "house",     310000.0),
    (45.0,  1, "apartment",  95000.0),
], ids=["small-apartment", "medium-house", "tiny-apartment"])
def test_finder_various_queries(mock_finder, surface, bedrooms, ptype, price):
    results = mock_finder.find(
        surface_m2=surface, bedrooms=bedrooms,
        property_type=ptype, price_estimate=price, n=3,
    )
    assert isinstance(results, list)


def test_finder_empty_csv(tmp_path):
    from model.similar import SimilarListingsFinder
    empty = pd.DataFrame(columns=[
        "price","surface_m2","bedrooms","property_type",
        "city","dpe_class","url","title","price_per_m2",
    ])
    csv_path = tmp_path / "empty.csv"
    empty.to_csv(csv_path, index=False)
    finder = SimilarListingsFinder(csv_path)
    results = finder.find(
        surface_m2=80.0, bedrooms=2,
        property_type="apartment", price_estimate=200000.0, n=3,
    )
    assert results == []
