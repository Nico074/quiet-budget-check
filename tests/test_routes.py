from fastapi.testclient import TestClient
from app import app

client = TestClient(app)


def test_public_routes():
    for path in ("/", "/pricing", "/privacy", "/terms", "/login", "/register"):
        resp = client.get(path)
        assert resp.status_code == 200


def test_auth_required_routes_redirect():
    for path in ("/dashboard", "/run-check", "/history", "/goals", "/wallet", "/account", "/billing", "/upgrade"):
        resp = client.get(path, allow_redirects=False)
        assert resp.status_code in (302, 303)


def test_settings_redirect():
    resp = client.get("/settings", allow_redirects=False)
    assert resp.status_code in (302, 303)
