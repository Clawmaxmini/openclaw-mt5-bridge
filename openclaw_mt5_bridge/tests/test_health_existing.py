import pytest
fastapi = pytest.importorskip("fastapi")
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes import router


def test_health_endpoint_existing_behavior(monkeypatch):
    app = FastAPI()
    app.include_router(router)

    from app import routes as routes_module

    monkeypatch.setattr(routes_module.mt5_service, "is_connected", lambda: True)

    client = TestClient(app)
    resp = client.get("/health")

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "mt5_connected": True}
