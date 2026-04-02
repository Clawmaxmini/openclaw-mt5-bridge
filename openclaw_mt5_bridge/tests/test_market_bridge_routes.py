import json
from pathlib import Path

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.market_bridge_routes import router


def test_market_bridge_latest_404(monkeypatch, tmp_path):
    app = FastAPI()
    app.include_router(router)

    import app.market_bridge_routes as module

    monkeypatch.setattr(module, "SNAPSHOT_FILE", tmp_path / "missing.json")

    client = TestClient(app)
    response = client.get("/market_bridge/latest")

    assert response.status_code == 404


def test_market_bridge_latest_ok(monkeypatch, tmp_path):
    app = FastAPI()
    app.include_router(router)

    snapshot = tmp_path / "market_snapshot.json"
    snapshot.write_text(json.dumps({"status": "ok"}), encoding="utf-8")

    import app.market_bridge_routes as module

    monkeypatch.setattr(module, "SNAPSHOT_FILE", Path(snapshot))

    client = TestClient(app)
    response = client.get("/market_bridge/latest")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
