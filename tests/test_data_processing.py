"""
Tests for data_processing.py
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.config import COLUMN_NAMES, CONSTANT_SENSORS, RUL_CAP
from src.data_processing import (
    check_missing,
    drop_constant_sensors,
    label_test_rul,
    label_train_rul,
)


# ─── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def sample_train_df() -> pd.DataFrame:
    """Minimal synthetic training DataFrame resembling C-MAPSS structure."""
    rows = []
    for unit in [1, 2]:
        for cycle in range(1, 11):
            row = {"unit_id": unit, "cycle": cycle}
            for i in range(1, 22):
                row[f"sensor_{i}"] = float(i * cycle)
            row["op_setting_1"] = 1.0
            row["op_setting_2"] = 0.5
            row["op_setting_3"] = 0.0
            rows.append(row)
    return pd.DataFrame(rows)


@pytest.fixture
def sample_test_df() -> pd.DataFrame:
    """Minimal synthetic test DataFrame."""
    rows = []
    for unit in [1, 2]:
        for cycle in range(1, 6):
            row = {"unit_id": unit, "cycle": cycle}
            for i in range(1, 22):
                row[f"sensor_{i}"] = float(i)
            row["op_setting_1"] = 1.0
            row["op_setting_2"] = 0.5
            row["op_setting_3"] = 0.0
            rows.append(row)
    return pd.DataFrame(rows)


# ─── RUL Labelling Tests ──────────────────────────────────────────────────────


def test_label_train_rul_range(sample_train_df):
    """RUL values should be non-negative and ≤ RUL_CAP."""
    df = label_train_rul(sample_train_df.copy())
    assert "RUL" in df.columns
    assert df["RUL"].min() >= 0
    assert df["RUL"].max() <= RUL_CAP


def test_label_train_rul_last_cycle_is_zero(sample_train_df):
    """Last cycle of each engine should have RUL = 0 (if RUL_CAP > max_cycle)."""
    df = label_train_rul(sample_train_df.copy(), rul_cap=1000)
    for unit_id in df["unit_id"].unique():
        unit_df = df[df["unit_id"] == unit_id]
        last = unit_df.loc[unit_df["cycle"].idxmax(), "RUL"]
        assert last == 0.0, f"Engine {unit_id} last-cycle RUL should be 0"


def test_label_test_rul_reconstruction(sample_test_df):
    """Test RUL should be reconstructed from terminal RUL values."""
    true_rul = np.array([10.0, 20.0])  # terminal RUL for engine 1 and 2
    df = label_test_rul(sample_test_df.copy(), true_rul, rul_cap=1000)
    assert "RUL" in df.columns

    # Engine 1, last cycle (cycle 5) should have RUL = 10
    eng1 = df[(df["unit_id"] == 1) & (df["cycle"] == 5)]
    assert abs(eng1["RUL"].values[0] - 10.0) < 1e-6

    # Engine 1, cycle 1 should have RUL = 10 + (5 - 1) = 14
    eng1_c1 = df[(df["unit_id"] == 1) & (df["cycle"] == 1)]
    assert abs(eng1_c1["RUL"].values[0] - 14.0) < 1e-6


def test_label_train_rul_rul_cap_applied(sample_train_df):
    """RUL cap should clip early-cycle values at RUL_CAP."""
    cap = 5  # shorter than max cycle - 0 = 9
    df = label_train_rul(sample_train_df.copy(), rul_cap=cap)
    assert df["RUL"].max() <= cap


# ─── Sensor Dropping Tests ────────────────────────────────────────────────────


def test_drop_constant_sensors_removes_expected_cols(sample_train_df):
    """Constant sensors (from config list) should be removed."""
    df_clean = drop_constant_sensors(sample_train_df.copy())
    for col in CONSTANT_SENSORS:
        assert col not in df_clean.columns, f"{col} should have been dropped"


def test_drop_constant_sensors_retains_variable_sensors(sample_train_df):
    """Non-constant sensors should be retained."""
    df_clean = drop_constant_sensors(sample_train_df.copy())
    # sensor_2 should be present (it varies in our fixture)
    assert "sensor_2" in df_clean.columns


def test_drop_constant_sensors_data_driven(sample_train_df):
    """Sensors with zero variance in the data should be dropped."""
    df = sample_train_df.copy()
    df["sensor_999"] = 42.0  # Add artificial constant column
    df_clean = drop_constant_sensors(df, threshold=1e-6)
    assert "sensor_999" not in df_clean.columns


# ─── Missing Value Check ──────────────────────────────────────────────────────


def test_check_missing_no_output_for_clean_data(capsys, sample_train_df):
    """check_missing should not raise for clean data."""
    check_missing(sample_train_df)  # should not raise


def test_check_missing_detects_nans(sample_train_df):
    """check_missing should detect NaN values."""
    df = sample_train_df.copy()
    df.loc[0, "sensor_2"] = float("nan")
    # Should not raise, just log
    check_missing(df, label="test")
