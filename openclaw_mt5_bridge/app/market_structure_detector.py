"""Market Structure Detector - Pure Python implementation, no numpy."""
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class MarketState(str, Enum):
    TREND_UP = "TREND_UP"
    TREND_DOWN = "TREND_DOWN"
    RANGE = "RANGE"
    V_SHAPE = "V_SHAPE"
    INVERSE_V = "INVERSE_V"
    UNKNOWN = "UNKNOWN"


@dataclass
class StructureResult:
    state: MarketState
    confidence: float
    slope: float
    consistency: float
    displacement: float
    volatility: float
    curvature: float
    trend_score: float
    reversal_score: float
    range_score: float


def mean(data: list) -> float:
    return sum(data) / len(data) if data else 0.0


def std(data: list) -> float:
    if len(data) < 2:
        return 0.0
    m = mean(data)
    variance = sum((x - m) ** 2 for x in data) / len(data)
    return variance ** 0.5


def linear_slope(prices: list) -> float:
    """Calculate slope using least squares."""
    n = len(prices)
    if n < 2:
        return 0.0
    x = list(range(n))
    x_mean = mean(x)
    y_mean = mean(prices)
    numerator = sum((x[i] - x_mean) * (prices[i] - y_mean) for i in range(n))
    denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
    if denominator == 0:
        return 0.0
    return numerator / denominator


def consistency(prices: list) -> float:
    """Calculate direction consistency (ratio of up bars)."""
    if len(prices) < 2:
        return 0.5
    ups = sum(1 for i in range(1, len(prices)) if prices[i] > prices[i-1])
    return ups / (len(prices) - 1)


def displacement(prices: list, atr: float) -> float:
    """Calculate displacement relative to ATR."""
    if len(prices) < 2 or atr <= 0:
        return 0.0
    return abs(prices[-1] - prices[0]) / atr


def curvature(prices: list) -> float:
    """Calculate second derivative using 3-point approximation."""
    if len(prices) < 3:
        return 0.0
    # Second difference at the end approximates curvature
    return prices[-1] - 2 * prices[-2] + prices[-3]


def volatility(prices: list) -> float:
    """Calculate volatility as coefficient of variation of returns."""
    if len(prices) < 2:
        return 0.0
    returns = [(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices)) if prices[i-1] != 0]
    if not returns:
        return 0.0
    return std(returns)


def detect_market_structure(
    prices: list,
    highs: Optional[list] = None,
    lows: Optional[list] = None,
    window_short: int = 20,
    window_long: int = 100,
) -> StructureResult:
    """Detect market structure from price data using pure Python."""
    if len(prices) < window_long:
        return StructureResult(
            state=MarketState.UNKNOWN, confidence=0.0,
            slope=0.0, consistency=0.5, displacement=0.0,
            volatility=0.0, curvature=0.0,
            trend_score=0.0, reversal_score=0.0, range_score=1.0,
        )
    
    recent = prices[-window_long:]
    price_level = mean(recent)
    
    slope = linear_slope(recent)
    cons = consistency(recent)
    vol = volatility(recent)
    curv = curvature(recent)
    
    # Normalize slope
    normalized_slope = abs(slope) / price_level if price_level > 0 else 0.0
    
    # Calculate ATR
    if highs and lows and len(highs) >= window_long and len(lows) >= window_long:
        recent_highs = highs[-window_long:]
        recent_lows = lows[-window_long:]
        trs = [max(highs[i] - lows[i],
                    abs(highs[i] - prices[i-1] if i > 0 else 0),
                    abs(lows[i] - prices[i-1] if i > 0 else 0))
                for i in range(1, len(recent_highs))]
        atr = mean(trs) if trs else 1.0
    else:
        atr = price_level * vol if vol > 0 else 1.0
    
    disp = displacement(recent, atr if atr > 0 else 1.0)
    
    # Scores
    trend_score = min(normalized_slope * 1000, 1.0) * 0.4 + cons * 0.3 + min(disp / 3.0, 1.0) * 0.3
    
    # Reversal detection
    if len(prices) >= window_short + window_long:
        long_part = prices[-window_long:-window_short]
        short_part = prices[-window_short:]
        slope_long = linear_slope(long_part)
        slope_short = linear_slope(short_part)
        slope_change = abs(slope_short - slope_long) / (abs(slope_long) + 0.0001)
    else:
        slope_change = 0.0
    
    reversal_score = min(slope_change / 1.2, 1.0) * 0.5 + min(abs(curv) / 0.4, 1.0) * 0.5
    range_score = 1.0 - trend_score
    
    # Determine state
    if trend_score > 0.7:
        state = MarketState.TREND_UP if slope > 0 else MarketState.TREND_DOWN
        confidence = trend_score
    elif reversal_score > 0.6 and abs(curv) > 0.4:
        state = MarketState.V_SHAPE if curv > 0 else MarketState.INVERSE_V
        confidence = reversal_score
    else:
        state = MarketState.RANGE
        confidence = range_score
    
    return StructureResult(
        state=state,
        confidence=round(confidence, 3),
        slope=round(slope, 5),
        consistency=round(cons, 3),
        displacement=round(disp, 3),
        volatility=round(vol, 5),
        curvature=round(curv, 5),
        trend_score=round(trend_score, 3),
        reversal_score=round(reversal_score, 3),
        range_score=round(range_score, 3),
    )


def get_state_description(result: StructureResult) -> str:
    """Get human-readable description."""
    state = result.state
    conf = result.confidence
    
    descriptions = {
        MarketState.TREND_UP: f"单边上涨结构（置信度{int(conf*100)}%），斜率{result.slope:.4f}，一致性{int(result.consistency*100)}%",
        MarketState.TREND_DOWN: f"单边下跌结构（置信度{int(conf*100)}%），斜率{result.slope:.4f}，一致性{int(result.consistency*100)}%",
        MarketState.V_SHAPE: f"V型反转结构（置信度{int(conf*100)}%），曲率{result.curvature:.4f}",
        MarketState.INVERSE_V: f"倒V反转结构（置信度{int(conf*100)}%），曲率{result.curvature:.4f}",
        MarketState.RANGE: f"震荡结构（置信度{int(conf*100)}%），波动率{result.volatility:.5f}",
        MarketState.UNKNOWN: "结构未知，数据不足",
    }
    return descriptions.get(state, "未知状态")
