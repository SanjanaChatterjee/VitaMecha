"""Basic API contract tests."""
import pandas as pd
from fastapi.testclient import TestClient
from api.main import app
from src.config import TEST_PROCESSED


def _payload():
    df = pd.read_csv(TEST_PROCESSED)
    row = df[df.unit_id == 1].sort_values('cycle').iloc[0]
    data = {
        'machine_id': 'pytest_engine',
        'cycle': int(row.cycle),
        'op_setting_1': float(row.op_setting_1),
        'op_setting_2': float(row.op_setting_2),
        'op_setting_3': float(row.op_setting_3),
    }
    for c in [c for c in df.columns if c.startswith('sensor_')]:
        data[c] = float(row[c])
    return data


def test_root_and_health():
    with TestClient(app) as client:
        assert client.get('/').status_code == 200
        assert client.get('/health').status_code == 200


def test_predict_contract():
    with TestClient(app) as client:
        response = client.post('/predict', json=_payload())
        assert response.status_code == 200
        body = response.json()
        assert 0 <= body['predicted_rul'] <= 125
        assert body['health_status'] in {'HEALTHY', 'WARNING', 'DEGRADED', 'CRITICAL'}
        assert 'recommendation' in body
        assert 'top_features' in body


def test_invalid_cycle_rejected():
    payload = _payload(); payload['cycle'] = 0
    with TestClient(app) as client:
        assert client.post('/predict', json=payload).status_code == 422
