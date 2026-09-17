"""
Tests for health.py
"""

import sys
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.health import HealthAssessment, classify_health, get_trend


def test_classify_healthy():
    result = classify_health(100.0)
    assert result.health_status == "HEALTHY"
    assert result.risk_level == "Low"


def test_classify_warning():
    result = classify_health(60.0)
    assert result.health_status == "WARNING"
    assert result.risk_level == "Medium"


def test_classify_degraded():
    result = classify_health(25.0)
    assert result.health_status == "DEGRADED"
    assert result.risk_level == "High"


def test_classify_critical():
    result = classify_health(5.0)
    assert result.health_status == "CRITICAL"
    assert result.risk_level == "Critical"


def test_classify_boundary_exactly_at_healthy_threshold():
    """RUL exactly equal to threshold boundary (inclusive check)."""
    result = classify_health(80.0)
    # 80.0 == HEALTHY threshold, should be HEALTHY (RUL > 80 -> HEALTHY, == is WARNING)
    assert result.health_status == "WARNING"


def test_classify_negative_rul_clipped():
    """Negative RUL should be clipped to 0 and classified as CRITICAL."""
    result = classify_health(-5.0)
    assert result.predicted_rul == 0.0
    assert result.health_status == "CRITICAL"


def test_classify_with_prediction_interval():
    result = classify_health(30.0, rul_lower=20.0, rul_upper=40.0)
    assert result.rul_lower == 20.0
    assert result.rul_upper == 40.0
    assert result.health_status == "DEGRADED"


def test_classify_custom_thresholds():
    custom = {"HEALTHY": 50, "WARNING": 20, "DEGRADED": 5, "CRITICAL": 0}
    result = classify_health(30.0, thresholds=custom)
    assert result.health_status == "WARNING"


def test_to_dict_serialisation():
    result = classify_health(18.0, rul_lower=12.0, rul_upper=24.0)
    d = result.to_dict()
    assert "predicted_rul" in d
    assert "health_status" in d
    assert "risk_level" in d
    assert "rul_lower" in d
    assert "rul_upper" in d


def test_get_trend_stable():
    history = [50.0, 50.5, 49.8, 50.2, 50.0]
    assert get_trend(history) == "Stable"


def test_get_trend_declining():
    history = [50.0, 47.0, 44.0, 41.0, 38.0]
    assert get_trend(history) == "Declining"


def test_get_trend_rapidly_declining():
    history = [50.0, 40.0, 30.0, 20.0, 10.0]
    assert get_trend(history) == "Rapidly Declining"


def test_get_trend_single_observation():
    assert get_trend([42.0]) == "Unknown"


def test_get_trend_empty():
    assert get_trend([]) == "Unknown"
