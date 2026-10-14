from fastapi.testclient import TestClient

from backend.app.main import app


def test_render_healthcheck_is_public_and_lightweight():
    response = TestClient(app).get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
