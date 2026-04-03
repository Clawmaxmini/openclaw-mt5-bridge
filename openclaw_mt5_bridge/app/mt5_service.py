import logging
from typing import Any

import MetaTrader5 as mt5

from .config import settings

logger = logging.getLogger(__name__)


_TIMEFRAME_MAP = {
    "M1": mt5.TIMEFRAME_M1,
    "M5": mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
    "M30": mt5.TIMEFRAME_M30,
    "H1": mt5.TIMEFRAME_H1,
    "H4": mt5.TIMEFRAME_H4,
    "D1": mt5.TIMEFRAME_D1,
}


class MT5Service:
    def __init__(self) -> None:
        self.connected = False

    def initialize(self) -> bool:
        logger.info("Initializing MetaTrader5 connection")
        self.connected = mt5.initialize(
            path=settings.mt5_path or None,
            login=settings.mt5_login or None,
            password=settings.mt5_password or None,
            server=settings.mt5_server or None,
            timeout=settings.mt5_timeout,
        )
        if not self.connected:
            logger.error("MT5 initialization failed: %s", mt5.last_error())
            return False

        terminal_info = mt5.terminal_info()
        account_info = mt5.account_info()
        if terminal_info is None or account_info is None:
            logger.error("MT5 terminal not running or account not available")
            self.shutdown()
            return False

        logger.info("MT5 connected. Terminal: %s", terminal_info.name)
        return True

    def shutdown(self) -> None:
        mt5.shutdown()
        self.connected = False
        logger.info("MT5 connection closed")

    def is_connected(self) -> bool:
        if not self.connected:
            return False
        return mt5.terminal_info() is not None and mt5.account_info() is not None

    def _normalize_symbol(self, symbol: str) -> str:
        """
        Map generic user-facing aliases to broker-specific MT5 symbols.
        If the symbol is already valid, keep it unchanged.
        """

        if not symbol:
            return symbol

        raw = symbol.strip().upper()

        alias_map = {
            # Metals
            "GOLD": "XAUUSD",
            "SILVER": "XAGUSD",
            # Energy
            "USOIL": "XTIUSD",
            "WTI": "XTIUSD",
            "UKOIL": "XBRUSD",
            "BRENT": "XBRUSD",
            "NATGAS": "XNGUSD",
            "NGAS": "XNGUSD",
            # Equity indices
            "NAS100": "USTEC",
            "US100": "USTEC",
            "SPX500": "US500",
            "SP500": "US500",
            "DJ30": "US30",
            "US30CASH": "US30",
            "RUSSELL": "US2000",
            "JPN225": "JP225",
            "GER40": "DE40",
            "HSI": "HK50",
            "CN50": "CHINA50",
            # Crypto
            "BTC": "BTCUSD",
            "ETH": "ETHUSD",
        }

        mapped = alias_map.get(raw, raw)

        if mt5.symbol_info(mapped) is not None:
            return mapped

        if mt5.symbol_info(raw) is not None:
            return raw

        return mapped

    def _ensure_symbol_selected(self, symbol: str) -> str:
        """
        Normalize symbol name and ensure it is visible in MT5 MarketWatch.
        Returns the resolved symbol name actually used for trading.
        """
        resolved = self._normalize_symbol(symbol)
        info = mt5.symbol_info(resolved)

        if info is None:
            logger.warning("MT5 symbol not found: input=%s resolved=%s", symbol, resolved)
            return resolved

        if not info.visible:
            selected = mt5.symbol_select(resolved, True)
            if selected:
                logger.info("Symbol enabled in MarketWatch: %s", resolved)
            else:
                logger.warning("Failed to enable symbol in MarketWatch: %s", resolved)

        return resolved

    def get_account_info(self) -> dict[str, Any]:
        account = mt5.account_info()
        if account is None:
            raise RuntimeError(f"Failed to retrieve account info: {mt5.last_error()}")

        return {
            "login": account.login,
            "balance": account.balance,
            "equity": account.equity,
            "margin": account.margin,
            "margin_free": account.margin_free,
        }

    def get_positions(self, symbol: str | None = None) -> list[dict[str, Any]]:
        positions = mt5.positions_get(symbol=symbol) if symbol else mt5.positions_get()
    def get_positions(self) -> list[dict[str, Any]]:
        positions = mt5.positions_get()
        if positions is None:
            raise RuntimeError(f"Failed to retrieve positions: {mt5.last_error()}")

        result: list[dict[str, Any]] = []
        for position in positions:
            result.append(
                {
                    "ticket": position.ticket,
                    "symbol": position.symbol,
                    "type": position.type,
                    "volume": position.volume,
                    "price_open": position.price_open,
                    "sl": position.sl,
                    "tp": position.tp,
                    "profit": position.profit,
                    "comment": position.comment,
                }
            )
        return result

    def get_candles(self, symbol: str, timeframe: str, bars: int) -> list[dict[str, Any]]:
        mt5_timeframe = _TIMEFRAME_MAP.get(timeframe.upper())
        if mt5_timeframe is None:
            raise ValueError(f"Unsupported timeframe: {timeframe}")

        rates = mt5.copy_rates_from_pos(symbol, mt5_timeframe, 0, bars)
        if rates is None:
            raise RuntimeError(f"Failed to retrieve candle data: {mt5.last_error()}")

        candles: list[dict[str, Any]] = []
        for rate in rates:
            candles.append(
                {
                    "time": int(rate["time"]),
                    "open": float(rate["open"]),
                    "high": float(rate["high"]),
                    "low": float(rate["low"]),
                    "close": float(rate["close"]),
                    "tick_volume": int(rate["tick_volume"]),
                }
            )
        return candles

    def send_market_order(
        self,
        symbol: str,
        side: str,
        volume: float,
        sl: float,
        tp: float,
        comment: str,
    ) -> dict[str, Any]:
        if side not in {"buy", "sell"}:
            raise ValueError("side must be 'buy' or 'sell'")

        original_symbol = symbol
        symbol = self._ensure_symbol_selected(symbol)
        logger.info(
            "Sending market order: input_symbol=%s resolved_symbol=%s side=%s volume=%s",
            original_symbol,
            symbol,
            side,
            volume,
        )

        order_type = mt5.ORDER_TYPE_BUY if side == "buy" else mt5.ORDER_TYPE_SELL
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            raise RuntimeError(f"Unable to fetch tick data for {symbol}: {mt5.last_error()}")

        price = tick.ask if side == "buy" else tick.bid
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": order_type,
            "price": price,
            "deviation": settings.mt5_deviation,
            "magic": settings.mt5_magic,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        if sl and sl > 0:
            request["sl"] = sl
        if tp and tp > 0:
            request["tp"] = tp

        result = mt5.order_send(request)
        if result is None:
            raise RuntimeError(f"order_send failed: {mt5.last_error()}")

        return {
            "retcode": result.retcode,
            "order": result.order,
            "deal": result.deal,
            "volume": result.volume,
            "price": result.price,
            "comment": result.comment,
            "request_id": result.request_id,
        }

    def close_position(self, ticket: int, symbol: str | None = None) -> dict[str, Any]:
        position = self._find_position(ticket=ticket, symbol=symbol)
        if position is None:
            raise RuntimeError(f"Position not found for ticket {ticket}")

        # First try TRADE_ACTION_CLOSE_BY
        request = {
            "action": mt5.TRADE_ACTION_CLOSE_BY,
            "position": position.ticket,
            "symbol": position.symbol,
            "volume": position.volume,
            "type": mt5.ORDER_TYPE_CLOSE_BY,
        }
        result = mt5.order_send(request)

        # If close_by is not supported, fallback to opposite order
        if result is None or (
            result.retcode != mt5.TRADE_RETCODE_DONE
            and result.retcode != mt5.TRADE_RETCODE_PLACED
        ):
            logger.warning(
                "close_by not supported (retcode=%s), falling back to opposite order",
                result.retcode if result else "None",
            )
            return self._close_by_opposite(position)

        return {"retcode": result.retcode, "order": result.order, "deal": result.deal}

    def _close_by_opposite(self, position) -> dict[str, Any]:
        """Fallback: close position by sending an opposite market order."""
        side = "sell" if position.type == mt5.POSITION_TYPE_BUY else "buy"
        order_type = mt5.ORDER_TYPE_SELL if side == "sell" else mt5.ORDER_TYPE_BUY
        tick = mt5.symbol_info_tick(position.symbol)
        if tick is None:
            raise RuntimeError(f"Unable to fetch tick data for {position.symbol}: {mt5.last_error()}")

        price = tick.bid if side == "sell" else tick.ask
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": position.symbol,
            "volume": position.volume,
            "type": order_type,
            "position": position.ticket,
            "price": price,
            "deviation": settings.mt5_deviation,
            "magic": settings.mt5_magic,
            "comment": f"close #{position.ticket}",
            "comment": "close_position",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        result = mt5.order_send(request)
        if result is None:
            raise RuntimeError(f"Close by opposite order failed: {mt5.last_error()}")
        return {"retcode": result.retcode, "order": result.order, "deal": result.deal}

    def modify_position(
        self, ticket: int, sl: float, tp: float, symbol: str | None = None
    ) -> dict[str, Any]:
            raise RuntimeError(f"Close position failed: {mt5.last_error()}")
        return {"retcode": result.retcode, "order": result.order, "deal": result.deal}

    def modify_position(self, ticket: int, sl: float, tp: float, symbol: str | None = None) -> dict[str, Any]:
        position = self._find_position(ticket=ticket, symbol=symbol)
        if position is None:
            raise RuntimeError(f"Position not found for ticket {ticket}")

        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": position.ticket,
            "symbol": position.symbol,
            "sl": sl,
            "tp": tp,
        }
        result = mt5.order_send(request)
        if result is None:
            raise RuntimeError(f"Modify position failed: {mt5.last_error()}")
        return {"retcode": result.retcode, "order": result.order}

    def close_all_positions(self, symbol: str | None = None) -> list[dict[str, Any]]:
        positions = mt5.positions_get(symbol=symbol) if symbol else mt5.positions_get()
        if positions is None:
            raise RuntimeError(f"Failed to retrieve positions: {mt5.last_error()}")

        results = []
        for position in positions:
            results.append(self.close_position(position.ticket, symbol=position.symbol))
        return results

    def modify_all_positions(self, sl: float, tp: float, symbol: str | None = None) -> list[dict[str, Any]]:
        positions = mt5.positions_get(symbol=symbol) if symbol else mt5.positions_get()
        if positions is None:
            raise RuntimeError(f"Failed to retrieve positions: {mt5.last_error()}")

        results = []
        for position in positions:
            results.append(self.modify_position(position.ticket, sl=sl, tp=tp, symbol=position.symbol))
        return results

    @staticmethod
    def _find_position(ticket: int, symbol: str | None = None) -> Any:
        positions = mt5.positions_get(ticket=ticket)
        if positions:
            if symbol is None:
                return positions[0]
            for position in positions:
                if position.symbol == symbol:
                    return position
        return None


mt5_service = MT5Service()
