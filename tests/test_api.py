from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_is_public():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_payments_requires_api_key():
    response = client.get("/api/v1/payments/00000000-0000-0000-0000-000000000001")
    assert response.status_code == 401
