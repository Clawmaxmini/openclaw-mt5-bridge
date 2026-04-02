import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from .config_manager import config_manager

logger = logging.getLogger(__name__)


class RiskEngine:
    def __init__(self) -> None:
        self.last_trade_by_symbol: dict[str, datetime] = {}
        self.daily_trade_counter: dict[str, int] = defaultdict(int)

    def _today_key(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def validate_order(
        self,
        *,
        symbol: str,
        side: str,
        volume: float,
        account_info: dict[str, Any],
        positions: list[dict[str, Any]],
    ) -> tuple[bool, dict[str, Any]]:
        active = config_manager.get_active()
        symbols_cfg = active["symbols"]
        risk_cfg = active["risk"]

        symbol_cfg = symbols_cfg.get(symbol)
        if not symbol_cfg:
            return self._failed("symbol_not_configured", f"Symbol {symbol} is not configured")

        if not symbol_cfg.get("enabled", False):
            return self._failed("symbol_disabled", f"Trading disabled for symbol {symbol}")

        if volume > float(symbol_cfg.get("max_single_order", 0)):
            return self._failed(
                "max_single_order_exceeded",
                f"Order volume {volume} exceeds max_single_order {symbol_cfg.get('max_single_order')}",
            )

        symbol_positions = [p for p in positions if p.get("symbol") == symbol]
        symbol_exposure = sum(float(p.get("volume", 0)) for p in symbol_positions)
        max_total_exposure = float(symbol_cfg.get("max_total_exposure", 0))
        if symbol_exposure + volume > max_total_exposure:
            return self._failed(
                "max_total_exposure_exceeded",
                f"Exposure {symbol_exposure + volume} exceeds max_total_exposure {max_total_exposure}",
            )

        max_positions = int(symbol_cfg.get("max_positions", 0))
        if len(symbol_positions) >= max_positions:
            return self._failed(
                "max_positions_exceeded",
                f"Open positions {len(symbol_positions)} reached max_positions {max_positions}",
            )

        last_trade_time = self.last_trade_by_symbol.get(symbol)
        cooldown_seconds = int(symbol_cfg.get("cooldown_seconds", 0))
        if last_trade_time and cooldown_seconds > 0:
            elapsed = (datetime.now(timezone.utc) - last_trade_time).total_seconds()
            if elapsed < cooldown_seconds:
                wait_seconds = int(cooldown_seconds - elapsed)
                return self._failed(
                    "cooldown_active",
                    f"Cooldown active for {symbol}. Wait {wait_seconds}s",
                )

        if not symbol_cfg.get("allow_same_direction", True):
            same_direction_exists = any(self._position_side(p.get("type")) == side for p in symbol_positions)
            if same_direction_exists:
                return self._failed(
                    "same_direction_blocked",
                    "Same-direction positions are disabled for this symbol",
                )

        if not symbol_cfg.get("allow_hedge", True):
            opposite_side = "sell" if side == "buy" else "buy"
            opposite_exists = any(self._position_side(p.get("type")) == opposite_side for p in symbol_positions)
            if opposite_exists:
                return self._failed("hedge_blocked", "Hedging is disabled for this symbol")

        if risk_cfg.get("pause_trading", False):
            return self._failed("trading_paused", "Trading is paused by risk configuration")

        balance = float(account_info.get("balance", 0))
        equity = float(account_info.get("equity", 0))
        if balance > 0:
            equity_ratio = equity / balance
            min_equity_ratio = float(risk_cfg.get("min_equity_ratio", 0))
            if equity_ratio < min_equity_ratio:
                return self._failed(
                    "min_equity_ratio_failed",
                    f"Equity ratio {equity_ratio:.4f} is below min_equity_ratio {min_equity_ratio}",
                )

        logger.info("Risk checks passed for symbol=%s side=%s volume=%s", symbol, side, volume)
        return True, {"code": "ok", "message": "Risk checks passed"}

    def register_executed_trade(self, symbol: str) -> None:
        self.last_trade_by_symbol[symbol] = datetime.now(timezone.utc)
        self.daily_trade_counter[self._today_key()] += 1

    def _failed(self, code: str, message: str) -> tuple[bool, dict[str, str]]:
        logger.info("Risk check failed: code=%s message=%s", code, message)
        return False, {"code": code, "message": message}

    @staticmethod
    def _position_side(position_type: int | None) -> str:
        if position_type == 0:
            return "buy"
        if position_type == 1:
            return "sell"
        return "unknown"


risk_engine = RiskEngine()
