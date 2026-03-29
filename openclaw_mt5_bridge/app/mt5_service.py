import logging
from typing import Any

import MetaTrader5 as mt5

from .config import settings

logger = logging.getLogger(__name__)


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


mt5_service = MT5Service()
