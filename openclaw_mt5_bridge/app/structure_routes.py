"""Structure detection API routes."""
import logging

from fastapi import APIRouter, HTTPException

from .market_structure_detector import (
    MarketState,
    detect_market_structure,
    get_state_description,
)
from .mt5_live_service import mt5_live_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/structure", tags=["structure"])


@router.get("/detect/{symbol}")
def detect_symbol_structure(
    symbol: str,
    timeframe: str = "M1",
    count: int = 200,
):
    """
    Detect market structure for a symbol.
    
    Uses recent candles to determine if market is:
    - TREND_UP / TREND_DOWN (单边)
    - RANGE (震荡)
    - V_SHAPE / INVERSE_V (反转)
    """
    if not mt5_live_service.is_connected():
        raise HTTPException(status_code=503, detail="MT5 not connected")
    
    candles = mt5_live_service.get_candles(symbol.upper(), timeframe, count)
    if candles is None or len(candles) < 50:
        raise HTTPException(status_code=404, detail=f"Not enough data for {symbol}")
    
    import numpy as np
    
    closes = np.array([c["close"] for c in candles])
    highs = np.array([c["high"] for c in candles])
    lows = np.array([c["low"] for c in candles])
    
    result = detect_market_structure(closes, highs, lows)
    description = get_state_description(result)
    
    return {
        "symbol": symbol.upper(),
        "timeframe": timeframe,
        "state": result.state.value,
        "description": description,
        "confidence": result.confidence,
        "metrics": {
            "slope": result.slope,
            "consistency": result.consistency,
            "displacement": result.displacement,
            "volatility": result.volatility,
            "curvature": result.curvature,
        },
        "scores": {
            "trend_score": result.trend_score,
            "reversal_score": result.reversal_score,
            "range_score": result.range_score,
        },
    }


@router.get("/detect/all")
def detect_all_structures(timeframe: str = "M1", count: int = 200):
    """Detect structure for all available symbols."""
    if not mt5_live_service.is_connected():
        raise HTTPException(status_code=503, detail="MT5 not connected")
    
    import numpy as np
    
    symbols = ["XAUUSD", "BTCUSD", "EURUSD", "GBPUSD", "USDJPY", 
               "JP225", "US500", "XAGUSD"]
    
    results = {}
    for symbol in symbols:
        try:
            candles = mt5_live_service.get_candles(symbol, timeframe, count)
            if candles and len(candles) >= 50:
                closes = np.array([c["close"] for c in candles])
                highs = np.array([c["high"] for c in candles])
                lows = np.array([c["low"] for c in candles])
                
                result = detect_market_structure(closes, highs, lows)
                results[symbol] = {
                    "state": result.state.value,
                    "confidence": result.confidence,
                    "slope": result.slope,
                    "consistency": result.consistency,
                    "description": get_state_description(result),
                }
        except Exception as e:
            logger.warning(f"Failed to detect structure for {symbol}: {e}")
    
    return {
        "timeframe": timeframe,
        "count": len(results),
        "structures": results,
    }
