"""
VitaMecha — Health & Risk Classification Engine
=================================================
Converts a predicted RUL value into a human-readable health status and
risk level using a configurable threshold-based rule engine.

Design rationale:
    A transparent rule-based health layer is deliberately used here rather
    than a learned classifier, because:
    (1) Transparency — operators can audit and trust the decision logic.
    (2) Configurability — maintenance teams can adjust thresholds without
        retraining the prediction model.
    (3) Consistency with literature — similar health-state partitioning is
        used in Mathew et al. (2017), Lei et al. (2018), and subsequent work.

Thresholds are documented as empirically motivated from the C-MAPSS FD001
RUL distribution (EDA phase) and are NOT presented as universal facts.

Health States:
    HEALTHY   — RUL > 80 cycles
    WARNING   — 40 ≤ RUL ≤ 80 cycles
    DEGRADED  — 15 ≤ RUL < 40 cycles
    CRITICAL  — RUL < 15 cycles
"""

from dataclasses import dataclass
from typing import Optional

from src.config import HEALTH_THRESHOLDS


# ─── Data Classes ─────────────────────────────────────────────────────────────


@dataclass
class HealthAssessment:
    """Complete health assessment for a single machine observation.

    Attributes:
        predicted_rul:      Point prediction of remaining useful life (cycles).
        health_status:      One of: HEALTHY, WARNING, DEGRADED, CRITICAL.
        risk_level:         One of: Low, Medium, High, Critical.
        rul_lower:          Lower bound of prediction interval (optional).
        rul_upper:          Upper bound of prediction interval (optional).
        threshold_healthy:  Configured threshold for HEALTHY status.
        threshold_warning:  Configured threshold for WARNING status.
        threshold_degraded: Configured threshold for DEGRADED status.
    """
    predicted_rul: float
    health_status: str
    risk_level: str
    rul_lower: Optional[float] = None
    rul_upper: Optional[float] = None
    threshold_healthy: int = HEALTH_THRESHOLDS["HEALTHY"]
    threshold_warning: int = HEALTH_THRESHOLDS["WARNING"]
    threshold_degraded: int = HEALTH_THRESHOLDS["DEGRADED"]

    def to_dict(self) -> dict:
        """Serialise to dictionary for API responses."""
        return {
            "predicted_rul": round(self.predicted_rul, 2),
            "health_status": self.health_status,
            "risk_level": self.risk_level,
            "rul_lower": round(self.rul_lower, 2) if self.rul_lower is not None else None,
            "rul_upper": round(self.rul_upper, 2) if self.rul_upper is not None else None,
        }


# ─── Classification Logic ─────────────────────────────────────────────────────


_RISK_MAP = {
    "HEALTHY": "Low",
    "WARNING": "Medium",
    "DEGRADED": "High",
    "CRITICAL": "Critical",
}

_STATUS_EMOJI = {
    "HEALTHY": "🟢",
    "WARNING": "🟡",
    "DEGRADED": "🟠",
    "CRITICAL": "🔴",
}


def classify_health(
    predicted_rul: float,
    rul_lower: Optional[float] = None,
    rul_upper: Optional[float] = None,
    thresholds: Optional[dict] = None,
) -> HealthAssessment:
    """Classify a predicted RUL into a health status and risk level.

    The classification uses the *point prediction* (predicted_rul).  When
    prediction intervals are provided (rul_lower, rul_upper), they are
    included in the assessment for display but do NOT change the health
    classification — this avoids over-alerting on interval uncertainty.

    Args:
        predicted_rul: Predicted RUL in cycles (must be ≥ 0).
        rul_lower:     Optional lower prediction bound (e.g., q=0.10).
        rul_upper:     Optional upper prediction bound (e.g., q=0.90).
        thresholds:    Override HEALTH_THRESHOLDS from config if provided.

    Returns:
        HealthAssessment dataclass.
    """
    rul = max(0.0, float(predicted_rul))
    t = thresholds or HEALTH_THRESHOLDS

    if rul > t["HEALTHY"]:
        status = "HEALTHY"
    elif rul >= t["WARNING"]:
        status = "WARNING"
    elif rul >= t["DEGRADED"]:
        status = "DEGRADED"
    else:
        status = "CRITICAL"

    return HealthAssessment(
        predicted_rul=rul,
        health_status=status,
        risk_level=_RISK_MAP[status],
        rul_lower=rul_lower,
        rul_upper=rul_upper,
        threshold_healthy=t["HEALTHY"],
        threshold_warning=t["WARNING"],
        threshold_degraded=t["DEGRADED"],
    )


def get_status_emoji(health_status: str) -> str:
    """Return a colour-coded emoji for a health status string.

    Args:
        health_status: One of: HEALTHY, WARNING, DEGRADED, CRITICAL.

    Returns:
        Emoji character.
    """
    return _STATUS_EMOJI.get(health_status, "⚪")


def get_trend(rul_history: list) -> str:
    """Determine the RUL trend from a short history.

    Args:
        rul_history: List of recent RUL predictions (oldest -> newest).

    Returns:
        One of: 'Stable', 'Declining', 'Rapidly Declining', 'Unknown'.
    """
    if len(rul_history) < 2:
        return "Unknown"

    recent = rul_history[-min(5, len(rul_history)):]
    delta = recent[-1] - recent[0]
    n = len(recent) - 1
    rate = delta / n if n > 0 else 0

    if rate < -5:
        return "Rapidly Declining"
    if rate < -1:
        return "Declining"
    if abs(rate) <= 1:
        return "Stable"
    return "Improving"
