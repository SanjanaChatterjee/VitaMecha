"""
Tests for feature_engineering.py
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.data_processing import drop_constant_sensors, label_train_rul
from src.feature_engineering import (
    add_cycle_features,
    add_degradation_index,
    add_difference_features,
    add_rolling_features,
    engineer_features,
    get_feature_names,
    get_sensor_columns,
)


@pytest.fixture
def sample_df() -> pd.DataFrame:
    """Synthetic C-MAPSS-like DataFrame with 2 engines."""
    rows = []
    for unit in [1, 2]:
        for cycle in range(1, 21):
            row = {"unit_id": unit, "cycle": cycle}
            for i in [2, 3, 4, 7, 8, 9]:
                row[f"sensor_{i}"] = float(i + cycle * 0.1 + np.random.randn() * 0.01)
            row["op_setting_1"] = 1.0
            row["op_setting_2"] = 0.5
            row["op_setting_3"] = 0.0
            rows.append(row)
    df = pd.DataFrame(rows)
    df = label_train_rul(df, rul_cap=50)
    return df


def test_get_sensor_columns(sample_df):
    """get_sensor_columns should return only sensor_* columns."""
    cols = get_sensor_columns(sample_df)
    assert all(c.startswith("sensor_") for c in cols)
    assert "unit_id" not in cols
    assert "cycle" not in cols


def test_add_rolling_features_shape(sample_df):
    """Rolling features should add 4 columns per sensor."""
    n_sensors = len(get_sensor_columns(sample_df))
    df_roll = add_rolling_features(sample_df.copy(), window=5)
    added = [c for c in df_roll.columns if "_roll_" in c]
    assert len(added) == n_sensors * 4


def test_add_rolling_features_no_cross_unit_leakage(sample_df):
    """Rolling features at cycle 1 of engine 2 should not use engine 1 data."""
    df_roll = add_rolling_features(sample_df.copy(), window=10)
    # Engine 2, cycle 1: rolling mean should equal sensor value (only 1 obs)
    eng2_c1 = df_roll[(df_roll["unit_id"] == 2) & (df_roll["cycle"] == 1)]
    assert len(eng2_c1) == 1
    for col in get_sensor_columns(sample_df):
        raw_val = eng2_c1[col].values[0]
        roll_mean = eng2_c1[f"{col}_roll_mean"].values[0]
        assert abs(raw_val - roll_mean) < 1e-6, f"Rolling mean cross-leakage for {col}"


def test_add_difference_features_first_row_zero(sample_df):
    """First-difference at cycle 1 of each engine should be 0 (no prior cycle)."""
    df_diff = add_difference_features(sample_df.copy())
    for unit in sample_df["unit_id"].unique():
        first_cycle = df_diff[df_diff["unit_id"] == unit]["cycle"].min()
        first_row = df_diff[(df_diff["unit_id"] == unit) & (df_diff["cycle"] == first_cycle)]
        for col in get_sensor_columns(sample_df):
            assert first_row[f"{col}_diff"].values[0] == 0.0, f"First diff should be 0 for {col}"


def test_add_cycle_features_range(sample_df):
    """cycle_log should be finite and monotonic with cycle."""
    df_cyc = add_cycle_features(sample_df.copy())
    assert "cycle_log" in df_cyc.columns
    assert np.isfinite(df_cyc["cycle_log"]).all()
    for _, g in df_cyc.groupby("unit_id"):
        assert (g["cycle_log"].diff().fillna(0) >= 0).all()


def test_add_degradation_index_no_nan(sample_df):
    """Degradation index should contain no NaN values."""
    df_deg = add_degradation_index(sample_df.copy())
    assert "degradation_index" in df_deg.columns
    assert df_deg["degradation_index"].isnull().sum() == 0


def test_engineer_features_no_nan(sample_df):
    """Full feature engineering should produce no NaN values."""
    df_eng = engineer_features(sample_df.copy())
    assert df_eng.isnull().sum().sum() == 0


def test_get_feature_names_excludes_ids(sample_df):
    """get_feature_names should exclude unit_id, cycle, and RUL."""
    df_eng = engineer_features(sample_df.copy())
    features = get_feature_names(df_eng)
    assert "unit_id" not in features
    assert "cycle" not in features
    assert "RUL" not in features


def test_engineer_features_row_count_preserved(sample_df):
    """Feature engineering should not drop or duplicate rows."""
    n_rows = len(sample_df)
    df_eng = engineer_features(sample_df.copy())
    assert len(df_eng) == n_rows
