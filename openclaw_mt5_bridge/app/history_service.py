import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

from .config import settings
from .file_store import FileMalformedError, file_store
from .schemas import HistoryBar, HistoryResponse, MultiHistoryResponse, PriceSnapshot
from .time_utils import parse_time_to_beijing

logger = logging.getLogger(__name__)


class HistoryService:
    """Service layer providing access to historical market data and snapshots."""

    def list_symbols(self) -> list[str]:
        """
        List all symbols with available snapshot or bar data.

        Returns:
            list[str]: Sorted, uppercase symbol list.
        """
        snapshot_dir = Path(settings.snapshot_dir)
        bars_dir = Path(settings.bars_dir)
        symbols: set[str] = set()

        for directory, pattern in (
            (snapshot_dir, "*.jsonl"),
            (bars_dir, "*_*.csv"),
        ):
            try:
                if directory.exists():
                    for path in directory.glob(pattern):
                        stem = path.stem.upper()
                        if pattern.endswith("*.jsonl"):
                            symbols.add(stem)
                        else:
                            symbols.add(stem.split("_")[0])
            except OSError:
                logger.exception("Failed to read directory %s", directory)

        return sorted(symbols)

    def get_latest_price(self, symbol: str) -> PriceSnapshot:
        """
        Retrieve the latest price snapshot for a symbol.

        Args:
            symbol (str): Symbol to query.

        Raises:
            ValueError: If symbol is invalid.
            FileNotFoundError: If the snapshot file is missing.
            FileMalformedError: If the snapshot file is malformed.

        Returns:
            PriceSnapshot: Latest available snapshot data.
        """
        symbol = self._validate_symbol(symbol)
        path = file_store.resolve_path(settings.snapshot_dir, f"{symbol}.jsonl")

        if not file_store.exists(path):
            msg = f"Snapshot not found for symbol {symbol}"
            logger.error(msg)
            raise FileNotFoundError(msg)

        try:
            rows = file_store.read_jsonl(path)
        except FileMalformedError:
            logger.exception("Malformed snapshot file for %s", symbol)
            raise

        if not rows:
            msg = f"No valid snapshot rows for {symbol}"
            logger.error(msg)
            raise FileMalformedError(msg)

        last = rows[-1]
        timestamp_utc, timestamp_beijing = parse_time_to_beijing(
            str(last.get("timestamp_utc") or last.get("time") or "")
        )

        snapshot = PriceSnapshot(
            symbol=str(last.get("symbol") or symbol).upper(),
            bid=float(last.get("bid", 0)),
            ask=float(last.get("ask", 0)),
            last=float(last["last"]) if last.get("last") is not None else None,
            spread=float(last.get("spread", 0)),
            timestamp_utc=timestamp_utc,
            timestamp_beijing=timestamp_beijing,
        )
        logger.debug("Retrieved latest price for %s", symbol)
        return snapshot

    def _bars_file(self, symbol: str, timeframe: str) -> Path:
        """Build the expected CSV path for a symbol and timeframe."""
        return file_store.resolve_path(settings.bars_dir, f"{symbol.upper()}_{self._validate_timeframe(timeframe)}.csv")

    def get_history(self, symbol: str, timeframe: str, hours: int, limit: int | None) -> HistoryResponse:
        """
        Retrieve historical bar data.

        Args:
            symbol (str): Symbol to query.
            timeframe (str): Bar timeframe (e.g., M1, H1).
            hours (int): Lookback window in hours.
            limit (int | None): Optional bar limit.

        Raises:
            ValueError: If inputs are invalid.
            FileNotFoundError: If the bar file is missing.
            FileMalformedError: If rows are malformed.

        Returns:
            HistoryResponse: Structured historical data.
        """
        symbol_upper = self._validate_symbol(symbol)
        timeframe_upper = self._validate_timeframe(timeframe)
        self._validate_hours(hours)
        self._validate_limit(limit)

        path = self._bars_file(symbol_upper, timeframe_upper)
        if not file_store.exists(path):
            msg = f"Bars file not found for {symbol_upper} {timeframe_upper}"
            logger.error(msg)
            raise FileNotFoundError(msg)

        try:
            rows = file_store.read_csv(path)
        except FileMalformedError:
            logger.exception("Malformed bars file for %s %s", symbol_upper, timeframe_upper)
            raise

        if not rows:
            logger.warning("No bar rows found for %s %s", symbol_upper, timeframe_upper)
            return HistoryResponse(symbol=symbol_upper, timeframe=timeframe_upper, hours=hours, count=0, bars=[])

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
                    logger.debug("Failed to parse datetime %s in %s", time_utc, path)

            try:
                bar = HistoryBar(
                    symbol=symbol_upper,
                    timeframe=timeframe_upper,
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
            except (ValueError, TypeError) as exc:
                logger.exception("Malformed bar row in %s: %s", path, row)
                raise FileMalformedError(f"Malformed bar row in {path}") from exc

            bars.append(bar)

        if limit is not None:
            bars = bars[-limit:]

        logger.debug(
            "Retrieved %d bars for %s %s (limit=%s, hours=%d)",
            len(bars),
            symbol_upper,
            timeframe_upper,
            limit,
            hours,
        )

        return HistoryResponse(
            symbol=symbol_upper,
            timeframe=timeframe_upper,
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
        """
        Retrieve historical data for multiple symbols.

        Args:
            symbols (list[str]): Symbols to query.
            timeframe (str): Bar timeframe.
            hours (int): Lookback window in hours.
            limit (int | None): Optional per-symbol limit.

        Returns:
            MultiHistoryResponse: Aggregated history data.
        """
        symbols = self._validate_symbols(symbols)
        timeframe_upper = self._validate_timeframe(timeframe)
        self._validate_hours(hours)
        self._validate_limit(limit)

        data: dict[str, list[HistoryBar]] = {}
        for symbol in symbols:
            history = self.get_history(symbol, timeframe_upper, hours, limit)
            data[symbol.upper()] = history.bars

        logger.debug(
            "Retrieved multi history for %d symbols (%s)",
            len(symbols),
            ", ".join(symbols),
        )
        return MultiHistoryResponse(timeframe=timeframe_upper, hours=hours, data=data)

    @staticmethod
    def _validate_symbol(symbol: str) -> str:
        if not isinstance(symbol, str) or not symbol.strip():
            raise ValueError("Symbol must be a non-empty string")
        return symbol.strip().upper()

    @staticmethod
    def _validate_symbols(symbols: Iterable[str]) -> list[str]:
        if not isinstance(symbols, Iterable):
            raise ValueError("Symbols must be an iterable of strings")
        validated = []
        for symbol in symbols:
            validated.append(HistoryService._validate_symbol(symbol))
        if not validated:
            raise ValueError("At least one symbol must be provided")
        return validated

    @staticmethod
    def _validate_timeframe(timeframe: str) -> str:
        if not isinstance(timeframe, str) or not timeframe.strip():
            raise ValueError("Timeframe must be a non-empty string")
        return timeframe.strip().upper()

    @staticmethod
    def _validate_hours(hours: int) -> None:
        if not isinstance(hours, int) or hours <= 0:
            raise ValueError("Hours must be a positive integer")

    @staticmethod
    def _validate_limit(limit: int | None) -> None:
        if limit is not None and (not isinstance(limit, int) or limit <= 0):
            raise ValueError("Limit must be a positive integer or None")


history_service = HistoryService()
