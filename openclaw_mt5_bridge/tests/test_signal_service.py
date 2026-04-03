import pytest
pytest.importorskip("dotenv")
import types

from app.signal_service import SignalService


def test_write_and_read_signal(tmp_path, monkeypatch):
    signals = tmp_path / "signals"
    signals.mkdir()

    import app.signal_service as ss

    monkeypatch.setattr(ss, "settings", types.SimpleNamespace(signals_dir=str(signals)))

    service = SignalService()
    written = service.write_signal("BTCUSD", {"side": "buy"})
    assert written.symbol == "BTCUSD"

    latest = service.get_latest_signal("BTCUSD")
    assert latest.signal["side"] == "buy"

    history = service.get_signal_history("BTCUSD", limit=10)
    assert len(history) == 1
