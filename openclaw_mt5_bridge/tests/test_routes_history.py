import pytest
fastapi = pytest.importorskip("fastapi")
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes import router


def test_history_route_returns_404(monkeypatch):
    app = FastAPI()
    app.include_router(router)

    from app import routes as routes_module

    def _raise(*args, **kwargs):
        raise FileNotFoundError("Bars file not found")

    monkeypatch.setattr(routes_module.history_service, "get_history", _raise)

    client = TestClient(app)
    resp = client.get("/history/BTCUSD")
    assert resp.status_code == 404
