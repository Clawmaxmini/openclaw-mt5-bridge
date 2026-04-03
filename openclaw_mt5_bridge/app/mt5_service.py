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

    def _ensure_symbol_selected(self, symbol: str) -> None:
        """Ensure symbol is visible in MT5 MarketWatch"""
        info = mt5.symbol_info(symbol)
        if info is None:
            logger.warning("Symbol %s not found in MT5", symbol)
            return
        if not info.visible:
            mt5.symbol_select(symbol, True)
            logger.info("Symbol %s added to MarketWatch", symbol)

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

        self._ensure_symbol_selected(symbol)

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
            "comment": "close_position",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        result = mt5.order_send(request)

        return {
            "retcode": result.retcode,
            "order": result.order,
            "deal": result.deal,
        }

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

        return {
            "retcode": result.retcode,
            "order": result.order,
        }

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
