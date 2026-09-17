"""Operator-reported machine problem triage for VitaMecha.

Important: C-MAPSS sensor channels are anonymized. Free-text symptoms such as
"machine is overheating" cannot be scientifically mapped to a particular
C-MAPSS sensor or RUL without a labelled symptom-to-telemetry dataset.

This module therefore provides a transparent operator-report triage layer. It
never pretends that text is a substitute for telemetry. It extracts symptoms,
assigns an advisory severity, identifies measurements that should be collected,
and prepares context that can be shown alongside a model-based RUL assessment.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
import re
from typing import List


SYMPTOMS = {
    "overheating": {
        "terms": ["heat", "hot", "overheat", "overheating", "temperature", "thermal", "too warm"],
        "severity": 3,
        "label": "Overheating / abnormal temperature",
        "measurements": ["Temperature", "Cooling-system condition", "Load / operating condition"],
    },
    "abnormal_sound": {
        "terms": ["sound", "noise", "noisy", "loud", "buzz", "humming", "grinding", "squeal", "rattle", "vibration"],
        "severity": 3,
        "label": "Abnormal sound / vibration",
        "measurements": ["Vibration", "Acoustic level", "Rotational speed", "Bearing condition"],
    },
    "efficiency_loss": {
        "terms": ["efficiency", "inefficient", "inefficiency", "power loss", "performance drop", "performance loss", "fuel consumption", "output drop"],
        "severity": 2,
        "label": "Efficiency / performance loss",
        "measurements": ["Input/output power", "Fuel or energy consumption", "Load", "Operating condition"],
    },
    "pressure_issue": {
        "terms": ["pressure", "pressur", "pressure drop", "low pressure", "high pressure"],
        "severity": 2,
        "label": "Pressure abnormality",
        "measurements": ["Pressure", "Flow rate", "Valve/pump state"],
    },
    "smoke_or_burning": {
        "terms": ["smoke", "burning", "burnt", "burn smell", "scorch"],
        "severity": 4,
        "label": "Smoke / burning indication",
        "measurements": ["Temperature", "Electrical current", "Fuel/air conditions", "Visual inspection"],
    },
    "leak": {
        "terms": ["leak", "leaking", "leakage", "fluid loss", "oil leak", "coolant leak"],
        "severity": 4,
        "label": "Possible fluid leak",
        "measurements": ["Fluid level", "Pressure", "Temperature", "Visual inspection"],
    },
    "instability": {
        "terms": ["unstable", "fluctuat", "surge", "oscillat", "intermittent", "erratic"],
        "severity": 3,
        "label": "Unstable / fluctuating operation",
        "measurements": ["Time-series sensor readings", "Operating settings", "Load", "Vibration"],
    },
}

@dataclass
class ProblemAssessment:
    summary: str
    symptoms: List[str]
    severity: str
    severity_score: int
    measurements: List[str]
    urgent: bool
    note: str

    def to_dict(self) -> dict:
        return asdict(self)


def assess_problem(description: str) -> ProblemAssessment:
    """Extract operator-reported issues using transparent keyword rules."""
    text = re.sub(r"\s+", " ", (description or "").strip().lower())
    if not text:
        return ProblemAssessment(
            summary="No machine problem was entered.",
            symptoms=[], severity="Unknown", severity_score=0, measurements=[], urgent=False,
            note="Describe the observed symptom(s), then provide measured telemetry for model-based RUL estimation.",
        )

    matched = []
    score = 0
    measurements = []
    for key, spec in SYMPTOMS.items():
        if any(term in text for term in spec["terms"]):
            matched.append(spec["label"])
            score += spec["severity"]
            measurements.extend(spec["measurements"])

    measurements = list(dict.fromkeys(measurements))
    immediate = any(term in text for key in ("smoke_or_burning", "leak") for term in SYMPTOMS[key]["terms"])
    if not matched:
        severity, urgent = "Unclassified", False
        summary = "The report could not be mapped to a known symptom category."
    elif immediate or score >= 7:
        severity, urgent = "High", True
        summary = "Multiple or high-severity machine symptoms were reported."
    elif score >= 4:
        severity, urgent = "Medium", False
        summary = "The reported symptoms warrant closer inspection and telemetry review."
    else:
        severity, urgent = "Low–Medium", False
        summary = "A machine anomaly was reported; collect telemetry before making a maintenance decision."

    return ProblemAssessment(
        summary=summary,
        symptoms=matched,
        severity=severity,
        severity_score=score,
        measurements=measurements,
        urgent=urgent,
        note=(
            "Operator text is contextual decision support only. C-MAPSS sensor channels are anonymized, "
            "so the current RUL model does not treat free text as a sensor measurement or physical cause. "
            "Use telemetry for a model-based RUL prediction."
        ),
    )
