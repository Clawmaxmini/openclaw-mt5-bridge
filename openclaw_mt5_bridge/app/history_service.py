from datetime import datetime, timezone, timedelta
from pathlib import Path

from .config import settings
from .file_store import FileMalformedError, file_store
from .schemas import HistoryBar, HistoryResponse, MultiHistoryResponse, PriceSnapshot
from .time_utils import parse_time_to_beijing


class HistoryService:
    def list_symbols(self) -> list[str]:
        snapshot_dir = Path(settings.snapshot_dir)
        bars_dir = Path(settings.bars_dir)
        symbols = set()

        if snapshot_dir.exists():
            for path in snapshot_dir.glob("*.jsonl"):
                symbols.add(path.stem.upper())

        if bars_dir.exists():
            for path in bars_dir.glob("*_*.csv"):
                symbols.add(path.stem.split("_")[0].upper())

        return sorted(symbols)

    def get_latest_price(self, symbol: str) -> PriceSnapshot:
        path = file_store.resolve_path(settings.snapshot_dir, f"{symbol.upper()}.jsonl")
        if not file_store.exists(path):
            raise FileNotFoundError(f"Snapshot not found for symbol {symbol}")

        rows = file_store.read_jsonl(path)
        if not rows:
            raise FileMalformedError(f"No valid snapshot rows for {symbol}")

        last = rows[-1]
        timestamp_utc, timestamp_beijing = parse_time_to_beijing(
            str(last.get("timestamp_utc") or last.get("time") or "")
        )
        return PriceSnapshot(
            symbol=str(last.get("symbol") or symbol).upper(),
            bid=float(last.get("bid", 0)),
            ask=float(last.get("ask", 0)),
            last=float(last["last"]) if last.get("last") is not None else None,
            spread=float(last.get("spread", 0)),
            timestamp_utc=timestamp_utc,
            timestamp_beijing=timestamp_beijing,
        )

    def _bars_file(self, symbol: str, timeframe: str) -> Path:
        return file_store.resolve_path(settings.bars_dir, f"{symbol.upper()}_{timeframe.upper()}.csv")

    def get_history(self, symbol: str, timeframe: str, hours: int, limit: int | None) -> HistoryResponse:
        path = self._bars_file(symbol, timeframe)
        if not file_store.exists(path):
            raise FileNotFoundError(f"Bars file not found for {symbol} {timeframe}")

        rows = file_store.read_csv(path)
        if not rows:
            return HistoryResponse(symbol=symbol.upper(), timeframe=timeframe.upper(), hours=hours, count=0, bars=[])

        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        bars: list[HistoryBar] = []
        for row in rows:
            tval = row.get("time") or row.get("time_utc") or row.get("timestamp")
            time_utc, time_beijing = parse_time_to_beijing(tval)
            if time_utc:
                try:
                    utc_dt = datetime.fromisoformat(time_utc.replace("Z", "+00:00"))
                    if utc_dt.replace(tzinfo=None) < cutoff.replace(tzinfo=None):
                        continue
                except Exception:
                    pass

            try:
                bar = HistoryBar(
                    symbol=symbol.upper(),
                    timeframe=timeframe.upper(),
                    time_utc=time_utc,
                    time_beijing=time_beijing,
                    open=float(row.get("open", 0)),
                    high=float(row.get("high", 0)),
                    low=float(row.get("low", 0)),
                    close=float(row.get("close", 0)),
                    volume=float(row["volume"]) if row.get("volume") not in (None, "") else None,
                    tick_volume=float(row["tick_volume"]) if row.get("tick_volume") not in (None, "") else None,
                    spread=float(row["spread"]) if row.get("spread") not in (None, "") else None,
                )
            except ValueError as exc:
                raise FileMalformedError(f"Malformed bar row in {path}") from exc
            bars.append(bar)

        if limit is not None:
            bars = bars[-limit:]

        return HistoryResponse(
            symbol=symbol.upper(),
            timeframe=timeframe.upper(),
            hours=hours,
            count=len(bars),
            bars=bars,
        )

    def get_multi_history(
        self,
        symbols: list[str],
        timeframe: str,
        hours: int,
        limit: int | None,
    ) -> MultiHistoryResponse:
        data = {}
        for symbol in symbols:
            history = self.get_history(symbol, timeframe, hours, limit)
            data[symbol.upper()] = history.bars
        return MultiHistoryResponse(timeframe=timeframe.upper(), hours=hours, data=data)


history_service = HistoryService()
