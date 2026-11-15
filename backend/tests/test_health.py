from fastapi.testclient import TestClient

from app.main import app


def test_health():
    r = TestClient(app).get("/health")
    assert r.status_code == 200
    assert r.json() == {
        "status": "ok",
        "version": "0.1.0",
        "cache": {"enabled": False, "circuit_open": False},  # REQ-554
    }
