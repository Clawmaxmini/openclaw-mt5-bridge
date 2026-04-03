import logging
from typing import Any

logger = logging.getLogger(__name__)


class MarketStructureService:
    @staticmethod
    def detect_state(candles: list[dict[str, Any]]) -> tuple[float, str]:
        if not candles:
            return 0.0, "range"

        bullish_count = sum(1 for c in candles if c["close"] > c["open"])
        ratio = bullish_count / len(candles)

        if ratio >= 0.66:
            state = "trend_up"
        elif ratio <= 0.33:
            state = "trend_down"
        else:
            state = "range"

        logger.info(
            "Market structure calculated: bars=%s bullish_count=%s ratio=%.4f state=%s",
            len(candles),
            bullish_count,
            ratio,
            state,
        )
        return ratio, state


market_structure_service = MarketStructureService()
