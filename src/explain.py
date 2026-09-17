"""
VitaMecha — SHAP Explainability Module
========================================
Provides both global and local SHAP explanations for RUL predictions.

Global explanation:  Mean |SHAP value| across all test samples — identifies
                     which sensors are generally important for RUL prediction.

Local explanation:   Per-prediction SHAP values — identifies why THIS
                     machine received THIS specific RUL prediction.

IMPORTANT academic note on causality:
    SHAP values quantify each feature's contribution to the model's prediction,
    not the physical cause of degradation.  Language such as "Sensor 11 is
    causing failure" is INCORRECT and MUST be avoided.  Correct framing:
    "Sensor 11's current reading is a strong predictor of reduced RUL in
    this model."

This distinction is consistent with Lundberg & Lee (2017) and the guidance
on responsible use of SHAP in industrial prognostics (Fan et al., 2023).
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
import shap

from src.config import (
    FEATURE_LIST_PATH,
    IMPROVED_MODEL,
    SCALER_PATH,
    SHAP_TOP_N_FEATURES,
)
from src.evaluate import load_model_artefacts

logger = logging.getLogger(__name__)


# ─── Explainer Class ──────────────────────────────────────────────────────────


class VitaMechaExplainer:
    """SHAP-based explainability engine for VitaMecha predictions.

    Uses SHAP TreeExplainer for fast, exact Shapley value computation
    with tree-based models (Random Forest, XGBoost).

    Attributes:
        model:        Trained model.
        explainer:    shap.TreeExplainer instance.
        feature_names: Feature column names.
    """

    def __init__(self, model, feature_names: List[str]) -> None:
        self.model = model
        self.feature_names = feature_names
        self.explainer = shap.TreeExplainer(model)
        logger.info("VitaMechaExplainer initialised (TreeExplainer).")

    @classmethod
    def from_disk(
        cls,
        model_path: Path = IMPROVED_MODEL,
        scaler_path: Path = SCALER_PATH,
        feature_list_path: Path = FEATURE_LIST_PATH,
    ) -> "VitaMechaExplainer":
        """Load model artefacts from disk and create an explainer.

        Args:
            model_path:        Path to saved model.
            scaler_path:       Path to saved scaler.
            feature_list_path: Path to feature list JSON.

        Returns:
            Initialised VitaMechaExplainer.
        """
        model, _scaler, feature_names = load_model_artefacts(model_path, scaler_path, feature_list_path)
        instance = cls(model, feature_names)
        return instance

    def explain_local(
        self,
        X_row: pd.DataFrame,
        top_n: int = SHAP_TOP_N_FEATURES,
    ) -> List[dict]:
        """Generate a local (per-prediction) SHAP explanation.

        Args:
            X_row: Single-row scaled feature DataFrame.
            top_n: Number of top features to return.

        Returns:
            List of dicts, sorted by absolute SHAP impact (desc):
            [{"feature": str, "impact": float, "description": str}, ...]
        """
        shap_vals = self.explainer.shap_values(X_row)
        if shap_vals.ndim > 1:
            shap_vals = shap_vals[0]  # single row

        contributions = pd.Series(shap_vals, index=self.feature_names)
        top = contributions.reindex(
            contributions.abs().sort_values(ascending=False).index
        ).head(top_n)

        result = []
        for feature, impact in top.items():
            result.append({
                "feature": str(feature),
                "impact": round(float(impact), 4),
                "description": _describe_contribution(str(feature), float(impact)),
            })
        return result

    def explain_global(
        self,
        X_scaled: pd.DataFrame,
        top_n: int = SHAP_TOP_N_FEATURES,
    ) -> pd.DataFrame:
        """Compute global SHAP feature importance (mean |SHAP|).

        Args:
            X_scaled: Scaled feature matrix (many rows).
            top_n:    Number of features to return.

        Returns:
            DataFrame with columns ['feature', 'mean_abs_shap'] sorted desc.
        """
        logger.info("Computing global SHAP values for %d samples...", len(X_scaled))
        shap_vals = self.explainer.shap_values(X_scaled)
        mean_abs = np.abs(shap_vals).mean(axis=0)
        importance = pd.DataFrame({
            "feature": self.feature_names,
            "mean_abs_shap": mean_abs,
        }).sort_values("mean_abs_shap", ascending=False).head(top_n)
        importance = importance.reset_index(drop=True)
        logger.info("Global SHAP computed. Top feature: %s (%.4f)",
                    importance.iloc[0]["feature"], importance.iloc[0]["mean_abs_shap"])
        return importance

    def get_expected_value(self) -> float:
        """Return the SHAP base (expected) value.

        This is the mean model prediction and represents the model's output
        when no feature information is available.

        Returns:
            Expected value scalar.
        """
        ev = self.explainer.expected_value
        if hasattr(ev, "__len__"):
            return float(ev[0])
        return float(ev)


# ─── Natural Language Descriptions ────────────────────────────────────────────


def _describe_contribution(feature: str, impact: float) -> str:
    """Generate a plain-English description of a SHAP feature contribution.

    The description follows responsible XAI framing: it describes the
    feature's effect on the MODEL's prediction, not physical causality.

    Args:
        feature: Feature name.
        impact:  SHAP impact value (negative = reduces predicted RUL).

    Returns:
        Human-readable advisory string.
    """
    abs_impact = abs(impact)

    if abs_impact < 0.5:
        magnitude = "minimal"
    elif abs_impact < 2.0:
        magnitude = "moderate"
    elif abs_impact < 5.0:
        magnitude = "significant"
    else:
        magnitude = "strong"

    direction = (
        "is reducing the predicted remaining life"
        if impact < 0
        else "is associated with higher predicted remaining life"
    )

    return (
        f"'{feature}' has a {magnitude} influence and {direction} "
        f"for this engine in the current model prediction "
        f"(SHAP contribution: {impact:+.2f} cycles)."
    )


def format_explanation_text(local_shap: List[dict]) -> str:
    """Format a local SHAP explanation as a readable text block.

    Args:
        local_shap: Output of VitaMechaExplainer.explain_local().

    Returns:
        Formatted multi-line string.
    """
    lines = ["Top Influencing Features (SHAP):"]
    for item in local_shap:
        direction = "▼" if item["impact"] < 0 else "▲"
        lines.append(
            f"  {direction} {item['feature']:<35} {item['impact']:+.3f} cycles"
        )
    lines.append(
        "\nNote: SHAP values show feature contributions to this model's "
        "prediction, not physical causes of degradation."
    )
    return "\n".join(lines)
