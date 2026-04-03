from .config import settings
from .file_store import FileMalformedError, file_store
from .schemas import SignalResponse
from .time_utils import now_beijing_str


class SignalService:
    def write_signal(self, symbol: str, signal: dict) -> SignalResponse:
        symbol_key = symbol.upper()
        updated_at = now_beijing_str()
        payload = {
            "symbol": symbol_key,
            "signal": signal,
            "updated_at_beijing": updated_at,
        }

        latest_path = file_store.resolve_path(settings.signals_dir, f"latest_{symbol_key}.json")
        history_path = file_store.resolve_path(settings.signals_dir, f"history_{symbol_key}.jsonl")
        file_store.write_json(latest_path, payload)
        file_store.append_jsonl(history_path, payload)
        return SignalResponse(**payload)

    def get_latest_signal(self, symbol: str) -> SignalResponse:
        symbol_key = symbol.upper()
        path = file_store.resolve_path(settings.signals_dir, f"latest_{symbol_key}.json")
        if not file_store.exists(path):
            raise FileNotFoundError(f"Latest signal not found for {symbol}")

        payload = file_store.read_json(path)
        if "signal" not in payload:
            raise FileMalformedError(f"Malformed latest signal file for {symbol}")
        return SignalResponse(**payload)

    def get_signal_history(self, symbol: str, limit: int = 20) -> list[dict]:
        symbol_key = symbol.upper()
        path = file_store.resolve_path(settings.signals_dir, f"history_{symbol_key}.jsonl")
        if not file_store.exists(path):
            raise FileNotFoundError(f"Signal history not found for {symbol}")

        rows = file_store.read_jsonl(path)
        return rows[-limit:]


signal_service = SignalService()
