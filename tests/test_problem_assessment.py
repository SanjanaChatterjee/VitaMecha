from src.problem_assessment import assess_problem


def test_problem_report_extracts_heat_and_efficiency():
    r = assess_problem("Machine is overheating and efficiency is dropping")
    assert "Overheating / abnormal temperature" in r.symptoms
    assert "Efficiency / performance loss" in r.symptoms
    assert r.severity_score >= 5
    assert "Temperature" in r.measurements


def test_problem_report_empty_is_safe():
    r = assess_problem("")
    assert r.severity == "Unknown"
    assert not r.urgent


def test_problem_report_smoke_is_high():
    r = assess_problem("There is smoke and a burning smell")
    assert r.severity == "High"
    assert r.urgent
