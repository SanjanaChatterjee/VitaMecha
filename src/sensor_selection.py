"""
VitaMecha — Sensor Selection Module
=====================================
Provides both traditional correlation-based and SHAP-guided sensor selection
to identify the most informative features for RUL prediction.

Academic note:
    SHAP-based feature selection is increasingly used in prognostics and health
    management research to ground sensor selection in model-specific evidence
    rather than purely statistical correlation (Lundberg & Lee, 2017; Fan et al.,
    2023). This module supports both approaches so they can be compared
    experimentally.

Methods:
    1. Variance filtering    — remove near-constant features (post-engineering)
    2. Correlation filtering — remove highly correlated feature pairs
    3. SHAP importance       — rank features by mean |SHAP value| from a
                               trained tree-based model
    4. Top-N selection       — select a specified number of top features

Usage:
    # After training the improved model, run SHAP-guided selection:
    selector = SHAPSelector(model, X_train)
    selected_features = selector.select(top_n=30)
"""

import json
import logging
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd
import shap

logger = logging.getLogger(__name__)


# ─── Correlation-Based Filtering ─────────────────────────────────────────────


def remove_low_variance(
    df: pd.DataFrame,
    threshold: float = 0.01,
    exclude_cols: Optional[List[str]] = None,
) -> List[str]:
    """Return column names with variance above ``threshold``.

    Args:
        df:           Feature DataFrame (X only, no RUL/ids).
        threshold:    Minimum variance to keep a feature.
        exclude_cols: Columns to always retain (e.g., non-sensor features).

    Returns:
        List of column names that pass the variance filter.
    """
    exclude_cols = exclude_cols or []
    variances = df.var()
    keep = [c for c in df.columns if variances[c] >= threshold or c in exclude_cols]
    removed = [c for c in df.columns if c not in keep]
    if removed:
        logger.info("Low-variance filter removed %d features: %s", len(removed), removed)
    return keep


def remove_correlated_features(
    df: pd.DataFrame,
    threshold: float = 0.95,
    method: str = "pearson",
) -> List[str]:
    """Remove highly correlated features, keeping one from each correlated pair.

    This is a greedy approach: for each pair with |correlation| ≥ threshold,
    the second feature in alphabetical order is dropped.

    Args:
        df:        Feature DataFrame.
        threshold: Correlation magnitude above which a feature is dropped.
        method:    Correlation method ('pearson', 'spearman').

    Returns:
        List of column names remaining after filtering.
    """
    corr = df.corr(method=method).abs()
    upper_tri = corr.where(np.triu(np.ones(corr.shape), k=1).astype(bool))
    to_drop = [col for col in upper_tri.columns if any(upper_tri[col] > threshold)]
    logger.info(
        "Correlation filter (method=%s, threshold=%.2f) removed %d features.",
        method, threshold, len(to_drop),
    )
    keep = [c for c in df.columns if c not in to_drop]
    return keep


# ─── SHAP-Based Sensor Selection ─────────────────────────────────────────────


class SHAPSelector:
    """Select the most predictive features using SHAP importance from a
    trained tree-based model (RandomForest or XGBoost).

    Attributes:
        model:       Trained scikit-learn compatible model.
        X_train:     Training feature matrix used to compute SHAP values.
        shap_values: Computed SHAP values (after calling ``fit``).
        importance:  Feature importance Series indexed by feature name.
    """

    def __init__(self, model, X_train: pd.DataFrame) -> None:
        self.model = model
        self.X_train = X_train
        self.shap_values: Optional[np.ndarray] = None
        self.importance: Optional[pd.Series] = None

    def fit(self) -> "SHAPSelector":
        """Compute SHAP values using TreeExplainer (fast for tree models).

        Returns:
            self (for method chaining).
        """
        logger.info("Computing SHAP values for feature selection (%d samples)...", len(self.X_train))
        explainer = shap.TreeExplainer(self.model)
        self.shap_values = explainer.shap_values(self.X_train)
        # Mean absolute SHAP value per feature
        self.importance = pd.Series(
            np.abs(self.shap_values).mean(axis=0),
            index=self.X_train.columns,
            name="shap_importance",
        ).sort_values(ascending=False)
        logger.info("SHAP importance computed for %d features.", len(self.importance))
        return self

    def select(self, top_n: int) -> List[str]:
        """Return the names of the top ``top_n`` features by SHAP importance.

        Args:
            top_n: Number of features to select.

        Returns:
            List of selected feature names (highest SHAP importance first).

        Raises:
            RuntimeError: If ``fit`` has not been called yet.
        """
        if self.importance is None:
            raise RuntimeError("Call SHAPSelector.fit() before SHAPSelector.select().")
        selected = self.importance.head(top_n).index.tolist()
        logger.info("Selected top %d features by SHAP importance.", top_n)
        return selected

    def get_importance_df(self) -> pd.DataFrame:
        """Return a DataFrame of features and their SHAP importance scores.

        Returns:
            DataFrame with columns ['feature', 'shap_importance'].

        Raises:
            RuntimeError: If ``fit`` has not been called yet.
        """
        if self.importance is None:
            raise RuntimeError("Call SHAPSelector.fit() first.")
        return self.importance.reset_index().rename(columns={"index": "feature"})

    def save_feature_list(self, path: Path, top_n: int) -> None:
        """Save the selected feature list to a JSON file.

        Args:
            path:  Output file path.
            top_n: Number of top features to save.
        """
        selected = self.select(top_n)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(selected, f, indent=2)
        logger.info("Feature list saved to %s (%d features).", path, len(selected))


def load_feature_list(path: Path) -> List[str]:
    """Load a previously saved feature list from JSON.

    Args:
        path: Path to the JSON feature list file.

    Returns:
        List of feature names.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    if not path.exists():
        raise FileNotFoundError(
            f"Feature list not found: {path}\n"
            "Run sensor selection (python -m src.train --phase improved) first."
        )
    with open(path) as f:
        features = json.load(f)
    logger.info("Loaded %d features from %s.", len(features), path)
    return features
