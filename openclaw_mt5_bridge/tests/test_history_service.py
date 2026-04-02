import pytest
pytest.importorskip("dotenv")
import types

from app.history_service import HistoryService


def test_get_latest_price_from_jsonl(tmp_path, monkeypatch):
    snapshots = tmp_path / "snapshots"
    bars = tmp_path / "bars"
    snapshots.mkdir()
    bars.mkdir()

    (snapshots / "BTCUSD.jsonl").write_text(
        '{"symbol":"BTCUSD","bid":100,"ask":101,"spread":1,"timestamp_utc":"2026-04-02T00:00:00+00:00"}\n',
        encoding="utf-8",
    )

    import app.history_service as hs

    monkeypatch.setattr(
        hs,
        "settings",
        types.SimpleNamespace(snapshot_dir=str(snapshots), bars_dir=str(bars)),
    )

    service = HistoryService()
    snap = service.get_latest_price("BTCUSD")
    assert snap.symbol == "BTCUSD"
    assert snap.bid == 100


def test_get_history_reads_csv(tmp_path, monkeypatch):
    snapshots = tmp_path / "snapshots"
    bars = tmp_path / "bars"
    snapshots.mkdir()
    bars.mkdir()
    (bars / "BTCUSD_M1.csv").write_text(
        "time,open,high,low,close,volume\n"
        "2026-04-02T00:00:00+00:00,1,2,0.5,1.5,10\n",
        encoding="utf-8",
    )

    import app.history_service as hs

    monkeypatch.setattr(
        hs,
        "settings",
        types.SimpleNamespace(snapshot_dir=str(snapshots), bars_dir=str(bars)),
    )

    service = HistoryService()
    resp = service.get_history("BTCUSD", "M1", hours=24, limit=None)
    assert resp.symbol == "BTCUSD"
    assert resp.count == 1
