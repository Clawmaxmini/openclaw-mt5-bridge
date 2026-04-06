"""Structure detection API routes - Pure Python, no numpy required."""
import logging

from fastapi import APIRouter, HTTPException

from .csv_market_service import csv_market_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/structure", tags=["structure"])


@router.get("/detect/all")
def detect_all_structures(lookback: int = 180):
    """Detect structures for all available symbols from CSV."""
    symbols = [
        "XAUUSD", "BTCUSD", "EURUSD", "GBPUSD", "USDJPY",
        "JP225", "US500", "XAGUSD", "ETHUSD", "XBRUSD", "XTIUSD"
    ]
    results = {}
    for sym in symbols:
        try:
            struct = csv_market_service.detect_structure(sym, lookback)
            if struct:
                results[sym] = struct
        except Exception as e:
            logger.warning("Structure detection failed for %s: %s", sym, e)
    return {"lookback_minutes": lookback, "count": len(results), "structures": results}


@router.get("/detect/{symbol}")
def detect_symbol_structure(symbol: str, lookback: int = 180):
    """Detect market structure for a symbol from CSV."""
    result = csv_market_service.detect_structure(symbol.upper(), lookback)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Insufficient data for {symbol}")
    return result
