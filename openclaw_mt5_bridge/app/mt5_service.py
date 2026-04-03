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

    def _get_account_position_mode(self) -> str:
        """
        Return account position mode: 'netting' or 'hedging'.
        """
        account = mt5.account_info()
        if account is None:
            logger.warning("Unable to read account info for position mode, defaulting to hedging")
            return "hedging"

        margin_mode = getattr(account, "margin_mode", None)
        if margin_mode in {
            getattr(mt5, "ACCOUNT_MARGIN_MODE_RETAIL_NETTING", -1),
            getattr(mt5, "ACCOUNT_MARGIN_MODE_EXCHANGE", -1),
        }:
            return "netting"
        if margin_mode == getattr(mt5, "ACCOUNT_MARGIN_MODE_RETAIL_HEDGING", -2):
            return "hedging"
        return "hedging"

    def _get_symbol_position(self, symbol: str) -> dict[str, Any] | None:
        positions = mt5.positions_get(symbol=symbol)
        if not positions:
            return None

        position = positions[0]
        side = "buy" if position.type == mt5.POSITION_TYPE_BUY else "sell"
        return {
            "ticket": position.ticket,
            "symbol": position.symbol,
            "type": side,
            "volume": float(position.volume),
            "price_open": float(position.price_open),
        }

    def _build_close_request(self, position: dict[str, Any], volume: float) -> dict[str, Any]:
        """
        Build reverse DEAL request for full/partial close on netting accounts.
        """
        close_type = mt5.ORDER_TYPE_SELL if position["type"] == "buy" else mt5.ORDER_TYPE_BUY
        tick = mt5.symbol_info_tick(position["symbol"])
        if tick is None:
            raise RuntimeError(
                f"Unable to fetch tick data for {position['symbol']}: {mt5.last_error()}"
            )
        price = tick.bid if close_type == mt5.ORDER_TYPE_SELL else tick.ask
        return {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": position["symbol"],
            "position": position["ticket"],
            "volume": volume,
            "type": close_type,
            "price": price,
            "deviation": settings.mt5_deviation,
            "magic": settings.mt5_magic,
            "comment": f"close #{position['ticket']}",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

    def _send_order_request(self, request: dict[str, Any]) -> Any:
        logger.info("MT5 order_send request: %s", request)
        result = mt5.order_send(request)
        if result is None:
            raise RuntimeError(f"order_send failed: {mt5.last_error()}")
        logger.info(
            "MT5 order_send result: retcode=%s comment=%s order=%s deal=%s",
            result.retcode,
            result.comment,
            result.order,
            result.deal,
        )
        return result

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
        mode = self._get_account_position_mode()
        existing_position = self._get_symbol_position(symbol)
        logger.info(
            "Sending market order: input_symbol=%s resolved_symbol=%s side=%s volume=%s mode=%s existing_position=%s",
            original_symbol,
            symbol,
            side,
            volume,
            mode,
            existing_position,
        )

        def _build_open_request(open_volume: float) -> dict[str, Any]:
            order_type = mt5.ORDER_TYPE_BUY if side == "buy" else mt5.ORDER_TYPE_SELL
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                raise RuntimeError(f"Unable to fetch tick data for {symbol}: {mt5.last_error()}")
            price = tick.ask if side == "buy" else tick.bid
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": open_volume,
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
            return request

        decision = "open"
        result = None
        message = "Opened new position"

        if existing_position is None:
            decision = "open"
            result = self._send_order_request(_build_open_request(volume))
            message = f"Opened {symbol} {side} {volume} successfully"
        else:
            existing_side = existing_position["type"]
            existing_volume = float(existing_position["volume"])
            if existing_side == side:
                decision = "add"
                result = self._send_order_request(_build_open_request(volume))
                message = f"Added {symbol} {side} {volume} successfully"
            else:
                if mode == "netting":
                    if volume == existing_volume:
                        decision = "close"
                        close_request = self._build_close_request(existing_position, volume)
                        result = self._send_order_request(close_request)
                        message = f"Closed {symbol} {volume} successfully"
                    elif volume < existing_volume:
                        decision = "partial_close"
                        close_request = self._build_close_request(existing_position, volume)
                        result = self._send_order_request(close_request)
                        remaining = round(existing_volume - volume, 8)
                        message = (
                            f"Partially closed {symbol} {volume}, remaining {existing_side} {remaining}"
                        )
                    else:
                        decision = "reverse"
                        close_request = self._build_close_request(existing_position, existing_volume)
                        close_result = self._send_order_request(close_request)
                        if close_result.retcode not in {
                            mt5.TRADE_RETCODE_DONE,
                            mt5.TRADE_RETCODE_PLACED,
                        }:
                            raise RuntimeError(
                                f"Close step failed before reverse: retcode={close_result.retcode}"
                            )
                        remaining = round(volume - existing_volume, 8)
                        result = self._send_order_request(_build_open_request(remaining))
                        message = (
                            f"Reversed {symbol}: closed {existing_side} {existing_volume} "
                            f"and opened {side} {remaining}"
                        )
                else:
                    decision = "hedge_open"
                    result = self._send_order_request(_build_open_request(volume))
                    message = f"Opened hedging order {symbol} {side} {volume} successfully"

        logger.info("send_market_order decision branch=%s", decision)

        return {
            "retcode": result.retcode,
            "order": result.order,
            "deal": result.deal,
            "volume": result.volume,
            "price": result.price,
            "comment": result.comment,
            "request_id": result.request_id,
            "message": message,
            "mode": mode,
            "decision": decision,
        }

    def close_position(self, ticket: int, volume: float | None = None) -> dict[str, Any]:
        positions = mt5.positions_get(ticket=ticket)
        if not positions:
            raise RuntimeError(f"Position not found for ticket {ticket}")

        position = positions[0]
        symbol = self._ensure_symbol_selected(position.symbol)
        close_volume = float(position.volume) if volume is None else float(volume)
        if close_volume <= 0:
            raise RuntimeError("Close volume must be greater than 0")
        if close_volume > float(position.volume):
            raise RuntimeError(
                f"Close volume {close_volume} exceeds position volume {position.volume}"
            )

        close_type = (
            mt5.ORDER_TYPE_SELL
            if position.type == mt5.POSITION_TYPE_BUY
            else mt5.ORDER_TYPE_BUY
        )
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            raise RuntimeError(f"Unable to fetch tick data for {symbol}: {mt5.last_error()}")
        price = tick.bid if close_type == mt5.ORDER_TYPE_SELL else tick.ask

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "position": ticket,
            "symbol": symbol,
            "volume": close_volume,
            "type": close_type,
            "price": price,
            "deviation": settings.mt5_deviation,
        }
        result = mt5.order_send(request)
        if result is None:
            raise RuntimeError(f"Close position failed: {mt5.last_error()}")

        success = result.retcode in {mt5.TRADE_RETCODE_DONE, mt5.TRADE_RETCODE_PLACED}
        message = (
            f"Closed {symbol} {close_volume} successfully"
            if success
            else f"Failed to close {symbol} {close_volume}: retcode={result.retcode}"
        )
        return {
            "success": success,
            "retcode": result.retcode,
            "order": result.order,
            "deal": result.deal,
            "message": message,
        }

    def _close_by_opposite(self, position) -> dict[str, Any]:
        """Fallback: close position by sending an opposite market order."""
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
            results.append(self.close_position(position.ticket))
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
