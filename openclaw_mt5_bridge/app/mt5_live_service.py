"""MT5 Live Service - Direct connection to local MT5 terminal for real-time data."""
import logging
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Try to import MetaTrader5
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    logger.warning("MetaTrader5 package not installed")


# Timeframe mapping
TIMEFRAME_MAP = {
    "M1": 1, "M5": 5, "M15": 15, "M30": 30,
    "H1": 16385, "H4": 16386, "D1": 16387,
    "W1": 16388, "MN1": 16389,
}


class MT5LiveService:
    """Service for direct MT5 real-time data access."""

    def __init__(self) -> None:
        self.connected = False

    def initialize(self) -> bool:
        """Initialize MT5 connection."""
        if not MT5_AVAILABLE:
            logger.error("MetaTrader5 package not installed")
            return False

        try:
            initialized = mt5.initialize()
            if not initialized:
                logger.error("MT5 initialization failed: %s", mt5.last_error())
                return False

            terminal_info = mt5.terminal_info()
            if terminal_info is None:
                logger.error("MT5 terminal not accessible")
                mt5.shutdown()
                return False

            self.connected = True
            logger.info("MT5 Live Service connected: %s", terminal_info.name)
            return True

        except Exception as exc:
            logger.error("MT5 initialization error: %s", exc)
            return False

    def shutdown(self) -> None:
        """Shutdown MT5 connection."""
        if self.connected:
            mt5.shutdown()
            self.connected = False
            logger.info("MT5 Live Service disconnected")

    def is_connected(self) -> bool:
        """Check if MT5 is connected."""
        if not self.connected or not MT5_AVAILABLE:
            return False
        try:
            return mt5.terminal_info() is not None
        except Exception:
            return False

    def get_tick(self, symbol: str) -> Optional[dict]:
        """
        Get latest tick for a symbol.
        Returns dict with bid, ask, time, etc.
        """
        if not self.is_connected():
            return None

        try:
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                return None

            return {
                "symbol": symbol,
                "bid": tick.bid,
                "ask": tick.ask,
                "last": tick.last,
                "volume": tick.volume,
                "time_msc": tick.time_msc,
                "flags": tick.flags,
                "time": datetime.fromtimestamp(tick.time, tz=timezone.utc).isoformat() if tick.time else None,
            }
        except Exception as exc:
            logger.warning("Failed to get tick for %s: %s", symbol, exc)
            return None

    def get_candles(
        self,
        symbol: str,
        timeframe: str = "M1",
        count: int = 100,
    ) -> Optional[list[dict]]:
        """
        Get historical candles for a symbol.
        timeframe: M1, M5, M15, M30, H1, H4, D1, W1, MN1
        count: number of candles to retrieve
        """
        if not self.is_connected():
            return None

        tf = TIMEFRAME_MAP.get(timeframe.upper(), 1)

        try:
            rates = mt5.copy_rates_from_pos(symbol, tf, 0, count)
            if rates is None:
                logger.warning("No candles for %s %s", symbol, timeframe)
                return None

            result = []
            for rate in rates:
                result.append({
                    "time": datetime.fromtimestamp(rate["time"], tz=timezone.utc).isoformat(),
                    "time_epoch": rate["time"],
                    "open": float(rate["open"]),
                    "high": float(rate["high"]),
                    "low": float(rate["low"]),
                    "close": float(rate["close"]),
                    "volume": int(rate["tick_volume"]),
                })

            return result

        except Exception as exc:
            logger.warning("Failed to get candles for %s: %s", symbol, exc)
            return None

    def get_account_info(self) -> Optional[dict]:
        """Get MT5 account information."""
        if not self.is_connected():
            return None

        try:
            info = mt5.account_info()
            if info is None:
                return None

            return {
                "login": info.login,
                "balance": info.balance,
                "equity": info.equity,
                "margin": info.margin,
                "margin_free": info.margin_free,
                "profit": info.profit,
                "server": info.server,
                "currency": info.currency,
            }
        except Exception as exc:
            logger.warning("Failed to get account info: %s", exc)
            return None

    def get_positions(self, symbol: Optional[str] = None) -> list[dict]:
        """Get open positions, optionally filtered by symbol."""
        if not self.is_connected():
            return []

        try:
            if symbol:
                positions = mt5.positions_get(symbol=symbol)
            else:
                positions = mt5.positions_get()

            if positions is None:
                return []

            result = []
            for pos in positions:
                result.append({
                    "ticket": pos.ticket,
                    "symbol": pos.symbol,
                    "type": "buy" if pos.type == 0 else "sell",
                    "volume": pos.volume,
                    "price_open": pos.price_open,
                    "sl": pos.sl,
                    "tp": pos.tp,
                    "profit": pos.profit,
                    "comment": pos.comment,
                    "time": datetime.fromtimestamp(pos.time, tz=timezone.utc).isoformat() if pos.time else None,
                })

            return result

        except Exception as exc:
            logger.warning("Failed to get positions: %s", exc)
            return []

    def get_symbol_info(self, symbol: str) -> Optional[dict]:
        """Get symbol information."""
        if not self.is_connected():
            return None

        try:
            info = mt5.symbol_info(symbol)
            if info is None:
                return None

            return {
                "symbol": info.name,
                "bid": info.bid,
                "ask": info.ask,
                "last": info.last,
                "volume": info.volume,
                "spread": info.spread,
                "digits": info.digits,
                "point": info.point,
                "description": info.description,
                "visible": info.visible,
            }
        except Exception as exc:
            logger.warning("Failed to get symbol info for %s: %s", symbol, exc)
            return None


# Global instance
mt5_live_service = MT5LiveService()
