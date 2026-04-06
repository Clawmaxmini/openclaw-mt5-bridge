"""Market Structure Detector - Detects trend, range, and reversal patterns."""
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


class MarketState(str, Enum):
    """Market structure states."""
    TREND_UP = "TREND_UP"
    TREND_DOWN = "TREND_DOWN"
    RANGE = "RANGE"
    V_SHAPE = "V_SHAPE"  # Reversal bottom
    INVERSE_V = "INVERSE_V"  # Reversal top
    UNKNOWN = "UNKNOWN"


@dataclass
class StructureResult:
    """Result of market structure detection."""
    state: MarketState
    confidence: float  # 0-1
    slope: float
    consistency: float  # 0-1
    displacement: float
    volatility: float
    curvature: float
    trend_score: float
    reversal_score: float
    range_score: float


# Thresholds
TREND_SLOPE_THRESHOLD = 0.6
CONSISTENCY_THRESHOLD = 0.65
DISPLACEMENT_THRESHOLD = 1.5
REVERSAL_SLOPE_CHANGE = 1.2
CURVATURE_THRESHOLD = 0.4

# Weights for scoring
W1 = 0.4  # slope weight
W2 = 0.3  # consistency weight
W3 = 0.3  # displacement weight
W4 = 0.5  # slope change weight
W5 = 0.5  # curvature weight


def calculate_slope(prices: np.ndarray) -> float:
    """Calculate linear regression slope."""
    if len(prices) < 2:
        return 0.0
    x = np.arange(len(prices))
    slope, _ = np.polyfit(x, prices, 1)
    return float(slope)


def calculate_consistency(prices: np.ndarray) -> float:
    """Calculate direction consistency (ratio of up bars)."""
    if len(prices) < 2:
        return 0.5
    diffs = np.diff(prices)
    up_count = np.sum(diffs > 0)
    return float(up_count) / float(len(diffs))


def calculate_displacement(prices: np.ndarray, atr: float) -> float:
    """Calculate displacement relative to ATR."""
    if len(prices) < 2 or atr <= 0:
        return 0.0
    displacement = (prices[-1] - prices[0]) / atr
    return float(abs(displacement))


def calculate_curvature(prices: np.ndarray) -> float:
    """Calculate second derivative (curvature) using quadratic fit."""
    if len(prices) < 3:
        return 0.0
    x = np.arange(len(prices))
    try:
        coeffs = np.polyfit(x, prices, 2)
        return float(coeffs[0])  # a in ax^2 + bx + c
    except Exception:
        return 0.0


def calculate_volatility(prices: np.ndarray) -> float:
    """Calculate volatility as standard deviation of returns."""
    if len(prices) < 2:
        return 0.0
    returns = np.diff(prices) / prices[:-1]
    return float(np.std(returns))


def calculate_atr(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray) -> float:
    """Calculate Average True Range."""
    if len(highs) < 2:
        return 1.0
    tr = np.maximum(
        highs[1:] - lows[1:],
        np.maximum(
            np.abs(highs[1:] - closes[:-1]),
            np.abs(lows[1:] - closes[:-1])
        )
    )
    return float(np.mean(tr))


def detect_market_structure(
    prices: np.ndarray,
    highs: Optional[np.ndarray] = None,
    lows: Optional[np.ndarray] = None,
    window_short: int = 20,
    window_long: int = 100,
) -> StructureResult:
    """
    Detect market structure from price data.
    
    Args:
        prices: Array of close prices
        highs: Array of high prices (optional)
        lows: Array of low prices (optional)
        window_short: Short window for trend detection
        window_long: Long window for structure detection
    
    Returns:
        StructureResult with detected state and metrics
    """
    if len(prices) < window_long:
        return StructureResult(
            state=MarketState.UNKNOWN,
            confidence=0.0,
            slope=0.0,
            consistency=0.5,
            displacement=0.0,
            volatility=0.0,
            curvature=0.0,
            trend_score=0.0,
            reversal_score=0.0,
            range_score=1.0,
        )
    
    # Use recent window for analysis
    recent_prices = prices[-window_long:]
    
    # Calculate metrics
    slope = calculate_slope(recent_prices)
    consistency = calculate_consistency(recent_prices)
    
    # Normalize slope by price level
    price_level = np.mean(recent_prices)
    normalized_slope = abs(slope) / price_level if price_level > 0 else 0.0
    
    # Calculate ATR and displacement
    if highs is not None and lows is not None:
        atr = calculate_atr(highs[-window_long:], lows[-window_long:], recent_prices)
    else:
        atr = calculate_volatility(recent_prices) * price_level
    
    displacement = calculate_displacement(recent_prices, atr if atr > 0 else 1.0)
    
    # Calculate curvature
    curvature = calculate_curvature(recent_prices)
    
    # Calculate volatility
    volatility = calculate_volatility(recent_prices)
    
    # Calculate trend score
    trend_score = W1 * min(normalized_slope * 1000, 1.0) + W2 * consistency + W3 * min(displacement / 3.0, 1.0)
    
    # Calculate reversal score
    if len(prices) >= window_short + window_long:
        long_prices = prices[-window_long:-window_short]
        short_prices = prices[-window_short:]
        slope_long = calculate_slope(long_prices)
        slope_short = calculate_slope(short_prices)
        slope_change = abs(slope_short - slope_long) / (abs(slope_long) + 0.0001)
    else:
        slope_change = 0.0
    
    reversal_score = W4 * min(slope_change / REVERSAL_SLOPE_CHANGE, 1.0) + W5 * min(abs(curvature) / CURVATURE_THRESHOLD, 1.0)
    
    # Calculate range score
    range_score = 1.0 - min(trend_score, 1.0)
    
    # Determine state
    if trend_score > 0.7:
        if slope > 0:
            state = MarketState.TREND_UP
        else:
            state = MarketState.TREND_DOWN
        confidence = trend_score
    elif reversal_score > 0.6 and abs(curvature) > CURVATURE_THRESHOLD:
        if curvature > 0:
            state = MarketState.V_SHAPE
        else:
            state = MarketState.INVERSE_V
        confidence = reversal_score
    else:
        state = MarketState.RANGE
        confidence = range_score
    
    return StructureResult(
        state=state,
        confidence=round(confidence, 3),
        slope=round(slope, 5),
        consistency=round(consistency, 3),
        displacement=round(displacement, 3),
        volatility=round(volatility, 5),
        curvature=round(curvature, 5),
        trend_score=round(trend_score, 3),
        reversal_score=round(reversal_score, 3),
        range_score=round(range_score, 3),
    )


def get_state_description(result: StructureResult) -> str:
    """Get human-readable description of detected structure."""
    state = result.state
    conf = result.confidence
    
    if state == MarketState.TREND_UP:
        return f"单边上涨结构（置信度{int(conf*100)}%），斜率{result.slope:.4f}，一致性{int(result.consistency*100)}%"
    elif state == MarketState.TREND_DOWN:
        return f"单边下跌结构（置信度{int(conf*100)}%），斜率{result.slope:.4f}，一致性{int(result.consistency*100)}%"
    elif state == MarketState.V_SHAPE:
        return f"V型反转结构（置信度{int(conf*100)}%），曲率{result.curvature:.4f}"
    elif state == MarketState.INVERSE_V:
        return f"倒V反转结构（置信度{int(conf*100)}%），曲率{result.curvature:.4f}"
    elif state == MarketState.RANGE:
        return f"震荡结构（置信度{int(conf*100)}%），波动率{result.volatility:.5f}"
    else:
        return "结构未知，数据不足"
