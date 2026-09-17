"""
Tests for recommendation.py
"""

import sys
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.health import classify_health
from src.recommendation import RecommendationResult, generate_recommendation


def test_healthy_recommendation():
    assessment = classify_health(100.0)
    rec = generate_recommendation(assessment)
    assert rec.priority == "ROUTINE"
    assert len(rec.details) > 0


def test_warning_recommendation():
    assessment = classify_health(60.0)
    rec = generate_recommendation(assessment)
    assert rec.priority == "MONITOR"


def test_degraded_recommendation():
    assessment = classify_health(25.0)
    rec = generate_recommendation(assessment)
    assert rec.priority == "URGENT"


def test_critical_recommendation():
    assessment = classify_health(5.0)
    rec = generate_recommendation(assessment)
    assert rec.priority == "EMERGENCY"


def test_rapidly_declining_warning_becomes_urgent():
    assessment = classify_health(60.0)
    rec = generate_recommendation(assessment, trend="Rapidly Declining")
    assert rec.priority == "URGENT"


def test_rapidly_declining_degraded_becomes_emergency():
    assessment = classify_health(25.0)
    rec = generate_recommendation(assessment, trend="Rapidly Declining")
    assert rec.priority == "EMERGENCY"


def test_recommendation_includes_disclaimer():
    assessment = classify_health(5.0)
    rec = generate_recommendation(assessment)
    assert "disclaimer" in rec.to_dict()
    assert len(rec.disclaimer) > 10


def test_sensor_note_from_top_features():
    assessment = classify_health(25.0)
    top_features = [
        {"feature": "sensor_11", "impact": -4.2, "description": "..."},
        {"feature": "sensor_4", "impact": -2.1, "description": "..."},
        {"feature": "sensor_7", "impact": 1.0, "description": "..."},
    ]
    rec = generate_recommendation(assessment, top_features=top_features)
    # Sensor note should mention sensor_11 (top negative contributor)
    assert "sensor_11" in rec.sensor_note


def test_sensor_note_empty_when_no_features():
    assessment = classify_health(25.0)
    rec = generate_recommendation(assessment, top_features=[])
    assert rec.sensor_note == ""


def test_to_plain_text_returns_string():
    assessment = classify_health(60.0)
    rec = generate_recommendation(assessment)
    text = rec.to_plain_text()
    assert isinstance(text, str)
    assert len(text) > 50


def test_to_dict_has_required_keys():
    assessment = classify_health(60.0)
    rec = generate_recommendation(assessment)
    d = rec.to_dict()
    assert "action" in d
    assert "priority" in d
    assert "details" in d
    assert "disclaimer" in d
