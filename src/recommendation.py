"""
VitaMecha — Maintenance Recommendation Engine
===============================================
Converts a health assessment + SHAP explanation into a structured, actionable
maintenance recommendation.

Design philosophy:
    VitaMecha is a DECISION-SUPPORT SYSTEM.  Final maintenance decisions
    remain with qualified human engineers.  All recommendations are framed
    as advisory guidance, not autonomous commands.

    Recommendations are generated from a transparent rule table keyed on
    health status and degradation trend, so that operators can audit,
    understand, and override them.

    Where SHAP feature explanations are available, the recommendation
    includes sensor-specific guidance (e.g., "Monitor Sensor 11 closely").

Output structure:
    RecommendationResult.action      — Primary action (e.g., "Continue operation")
    RecommendationResult.priority    — Priority level (ROUTINE / MONITOR / URGENT / EMERGENCY)
    RecommendationResult.details     — Bullet list of specific guidance steps
    RecommendationResult.sensor_note — Sensor-specific guidance from SHAP top features
    RecommendationResult.disclaimer  — Mandatory human-authority disclaimer
"""

from dataclasses import dataclass, field
from typing import List, Optional

from src.health import HealthAssessment


# ─── Data Classes ─────────────────────────────────────────────────────────────


@dataclass
class RecommendationResult:
    """Maintenance recommendation for a single machine assessment.

    Attributes:
        action:      Short primary action statement.
        priority:    Priority level: ROUTINE / MONITOR / URGENT / EMERGENCY.
        details:     List of specific maintenance guidance steps.
        sensor_note: Sensor-specific advisory derived from SHAP top features.
        disclaimer:  Mandatory advisory disclaimer.
    """
    action: str
    priority: str
    details: List[str]
    sensor_note: str = ""
    disclaimer: str = (
        "VitaMecha provides decision support only. All maintenance actions "
        "must be validated and executed by qualified engineers."
    )

    def to_dict(self) -> dict:
        """Serialise to dictionary for API responses."""
        return {
            "action": self.action,
            "priority": self.priority,
            "details": self.details,
            "sensor_note": self.sensor_note,
            "disclaimer": self.disclaimer,
        }

    def to_plain_text(self) -> str:
        """Format as a human-readable plain-text summary."""
        lines = [
            f"[{self.priority}] {self.action}",
            "",
            "Recommended steps:",
        ]
        for i, step in enumerate(self.details, 1):
            lines.append(f"  {i}. {step}")
        if self.sensor_note:
            lines.append("")
            lines.append(f"Sensor note: {self.sensor_note}")
        lines.append("")
        lines.append(f"Note: {self.disclaimer}")
        return "\n".join(lines)


# ─── Rule Table ───────────────────────────────────────────────────────────────

# Keyed on (health_status, trend)
# If trend is not matched, falls back to (health_status, None)
_RULE_TABLE = {
    ("HEALTHY", None): {
        "action": "Continue normal operation.",
        "priority": "ROUTINE",
        "details": [
            "No immediate maintenance action required.",
            "Continue scheduled monitoring at normal intervals.",
            "Record sensor baselines for future comparison.",
        ],
    },
    ("WARNING", None): {
        "action": "Schedule inspection within the next maintenance window.",
        "priority": "MONITOR",
        "details": [
            "Review sensor trends for signs of acceleration.",
            "Inspect high-contribution components at next planned stop.",
            "Increase monitoring frequency.",
            "Prepare spare parts if lead time is long.",
        ],
    },
    ("WARNING", "Rapidly Declining"): {
        "action": "Expedite inspection — degradation is accelerating.",
        "priority": "URGENT",
        "details": [
            "Do not defer inspection to the next scheduled window.",
            "Increase sensor sampling frequency immediately.",
            "Review maintenance history for root-cause clues.",
            "Alert maintenance supervisor.",
        ],
    },
    ("DEGRADED", None): {
        "action": "Plan maintenance soon — machine health is degrading.",
        "priority": "URGENT",
        "details": [
            "Schedule maintenance within the next 1–2 operating periods.",
            "Reduce load or operating intensity if operationally feasible.",
            "Inspect components associated with top-contributing sensors.",
            "Do not postpone — RUL window is narrowing.",
            "Prepare replacement parts.",
        ],
    },
    ("DEGRADED", "Rapidly Declining"): {
        "action": "Immediate maintenance planning required.",
        "priority": "EMERGENCY",
        "details": [
            "Alert maintenance team immediately.",
            "Evaluate operational risk of continued use.",
            "Inspect all high-contribution sensor components.",
            "Prepare for emergency maintenance if needed.",
        ],
    },
    ("CRITICAL", None): {
        "action": "Immediate inspection — machine is at critical RUL.",
        "priority": "EMERGENCY",
        "details": [
            "Stop or reduce operations immediately if safe to do so.",
            "Initiate emergency maintenance inspection.",
            "Inspect all components associated with top-contributing sensors.",
            "Do NOT operate without engineer sign-off.",
            "Document all recent sensor anomalies for root-cause analysis.",
        ],
    },
}


def _generate_sensor_note(top_features: Optional[List[dict]]) -> str:
    """Generate a plain-English sensor advisory from SHAP top features.

    Args:
        top_features: List of dicts with 'feature' and 'impact' keys,
                      sorted by absolute impact (highest first).
                      May be None or empty.

    Returns:
        Advisory string, or empty string if no features available.
    """
    if not top_features:
        return ""

    # Find top negative contributors (those reducing predicted RUL)
    degrading = [f for f in top_features if f.get("impact", 0) < 0][:3]
    if not degrading:
        return ""

    names = ", ".join(f["feature"] for f in degrading)
    return (
        f"The following sensor(s) are showing patterns associated with "
        f"reduced remaining life: {names}. "
        f"Consider focused inspection of the corresponding components."
    )


# ─── Recommendation Function ──────────────────────────────────────────────────


def generate_recommendation(
    assessment: HealthAssessment,
    trend: str = "Unknown",
    top_features: Optional[List[dict]] = None,
) -> RecommendationResult:
    """Generate a maintenance recommendation from health assessment and context.

    The recommendation is looked up from the transparent rule table.  If the
    exact (health_status, trend) key is not found, falls back to the
    (health_status, None) default.

    Args:
        assessment:   HealthAssessment from health.classify_health().
        trend:        RUL trend string from health.get_trend().
        top_features: SHAP top features list from explain module.

    Returns:
        RecommendationResult dataclass.
    """
    status = assessment.health_status

    # Try specific trend rule first, then fall back to default
    rule = _RULE_TABLE.get((status, trend)) or _RULE_TABLE.get((status, None))

    if rule is None:
        # Safety fallback — should not occur with valid health_status
        rule = {
            "action": "Inspect machine — health state could not be determined.",
            "priority": "MONITOR",
            "details": ["Contact maintenance engineer for manual assessment."],
        }

    sensor_note = _generate_sensor_note(top_features)

    return RecommendationResult(
        action=rule["action"],
        priority=rule["priority"],
        details=rule["details"].copy(),
        sensor_note=sensor_note,
    )
