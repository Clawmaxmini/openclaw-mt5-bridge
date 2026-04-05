"""Market watch service - aggregated market prices."""
import logging
from datetime import datetime, timezone
from typing import Optional

from .mt5_live_service import mt5_live_service

logger = logging.getLogger(__name__)

# Default watch list - these should match what your MT5 terminal provides
DEFAULT_SYMBOLS = [
    # Precious Metals
    "XAUUSD", "XAGUSD", "XBRUSD", "XTIUSD", "XNGUSD",
    # Major Forex
    "EURUSD", "USDJPY", "GBPUSD", "AUDUSD", "USDCAD", "USDCNH",
    "EURJPY", "GBPJPY", "EURGBP", "NZDUSD",
    # Indices
    "US30", "US500", "USTEC", "US2000", "JP225",
    "DE40", "HK50", "CHINA50", "CHINAH", "UK100",
    # Crypto
    "BTCUSD", "ETHUSD",
]


class MarketWatchService:
    """Aggregated market prices service."""

    def __init__(self) -> None:
        self.symbols = DEFAULT_SYMBOLS

    def get_price(self, symbol: str) -> Optional[dict]:
        """Get price info for a single symbol."""
        tick = mt5_live_service.get_tick(symbol)
        if tick is None:
            return None

        # Try to get daily open for % change calculation
        candles = mt5_live_service.get_candles(symbol, "D1", 2)
        
        result = {
            "symbol": symbol,
            "bid": tick.get("bid"),
            "ask": tick.get("ask"),
            "last_update": tick.get("time"),
        }

        # Calculate % change from daily open
        if candles and len(candles) >= 2:
            daily_open = candles[0].get("open")
            current_price = tick.get("bid")
            if daily_open and current_price:
                change_pct = ((current_price - daily_open) / daily_open) * 100
                result["daily_open"] = daily_open
                result["change_pct"] = round(change_pct, 2)
            result["daily_high"] = candles[0].get("high")
            result["daily_low"] = candles[0].get("low")

        return result

    def get_all_prices(self) -> dict:
        """Get prices for all symbols in watch list."""
        results = {}
        available_count = 0
        unavailable_count = 0

        for symbol in self.symbols:
            price_info = self.get_price(symbol)
            if price_info:
                results[symbol] = price_info
                available_count += 1
            else:
                results[symbol] = {"symbol": symbol, "available": False}
                unavailable_count += 1

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "count_available": available_count,
            "count_unavailable": unavailable_count,
            "prices": results,
        }


# Global instance
market_watch_service = MarketWatchService()
