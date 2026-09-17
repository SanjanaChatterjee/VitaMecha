"""Causal feature engineering for VitaMecha.

All temporal features use only the current observation and preceding observations
from the same machine. No feature uses the future end-of-life cycle, which keeps
training/evaluation compatible with sequential inference.
"""
from __future__ import annotations

import logging
from typing import List
import numpy as np
import pandas as pd
from src.config import ROLLING_WINDOW

logger = logging.getLogger(__name__)


def get_sensor_columns(df: pd.DataFrame) -> List[str]:
    return sorted(c for c in df.columns if c.startswith("sensor_"))


def get_op_setting_columns(df: pd.DataFrame) -> List[str]:
    return sorted(c for c in df.columns if c.startswith("op_setting_"))


def add_rolling_features(df: pd.DataFrame, window: int = ROLLING_WINDOW, min_periods: int = 1, include_extrema: bool = True) -> pd.DataFrame:
    df = df.sort_values(["unit_id", "cycle"]).copy()
    sensors = get_sensor_columns(df)
    groups = df.groupby("unit_id", sort=True)
    for sensor in sensors:
        g = groups[sensor]
        df[f"{sensor}_roll_mean"] = g.transform(lambda x: x.rolling(window, min_periods=min_periods).mean())
        df[f"{sensor}_roll_std"] = g.transform(lambda x: x.rolling(window, min_periods=min_periods).std(ddof=0)).fillna(0.0)
        if include_extrema:
            df[f"{sensor}_roll_min"] = g.transform(lambda x: x.rolling(window, min_periods=min_periods).min())
            df[f"{sensor}_roll_max"] = g.transform(lambda x: x.rolling(window, min_periods=min_periods).max())
    return df


def add_difference_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values(["unit_id", "cycle"]).copy()
    sensors = get_sensor_columns(df)
    for sensor in sensors:
        df[f"{sensor}_diff"] = df.groupby("unit_id")[sensor].diff().fillna(0.0)
    return df


def add_cycle_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add online-safe elapsed-cycle features.

    ``cycle`` itself is retained.  ``cycle_log`` is a monotonic transform that
    does not require knowing the eventual failure cycle or future observations.
    """
    df = df.copy()
    df["cycle_log"] = np.log1p(df["cycle"].astype(float))
    return df


def add_degradation_index(df: pd.DataFrame) -> pd.DataFrame:
    """Add an online-safe degradation index based on training statistics.

    This function is retained for API compatibility.  It computes a simple
    mean of per-sensor robustly scaled values using *global* statistics of the
    supplied frame. For the final model this feature is not selected unless it
    is demonstrably useful. It should not be interpreted as a physical health
    state.
    """
    df = df.copy()
    sensors = get_sensor_columns(df)
    if not sensors:
        df["degradation_index"] = 0.0
        return df
    med = df[sensors].median()
    mad = (df[sensors] - med).abs().median().replace(0, 1.0)
    df["degradation_index"] = ((df[sensors] - med) / mad).mean(axis=1)
    return df


def engineer_features(
    df: pd.DataFrame,
    window: int = ROLLING_WINDOW,
    add_rolling: bool = True,
    add_extrema: bool = True,
    add_diff: bool = True,
    add_cycle: bool = True,
    add_deg_index: bool = False,
) -> pd.DataFrame:
    """Apply the causal VitaMecha feature pipeline."""
    required = {"unit_id", "cycle"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    out = df.sort_values(["unit_id", "cycle"]).copy()
    if add_rolling:
        out = add_rolling_features(out, window=window, include_extrema=add_extrema)
    if add_diff:
        out = add_difference_features(out)
    if add_cycle:
        out = add_cycle_features(out)
    if add_deg_index:
        out = add_degradation_index(out)
    return out.fillna(0.0)


def get_feature_names(df: pd.DataFrame, include_cycle: bool = False) -> List[str]:
    exclude = {"unit_id", "RUL"}
    if not include_cycle:
        exclude.add("cycle")
    return [c for c in df.columns if c not in exclude]
