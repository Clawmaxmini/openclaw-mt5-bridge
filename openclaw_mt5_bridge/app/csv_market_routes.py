"""CSV-based market API routes - no MT5 polling required."""
import logging

from fastapi import APIRouter, HTTPException

from .csv_market_service import csv_market_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/csv", tags=["csv_market"])


@router.get("/prices")
def get_all_prices():
    """Get latest prices from all CSV files."""
    return csv_market_service.get_all_prices()


@router.get("/price/{symbol}")
def get_symbol_price(symbol: str):
    """Get latest price for a symbol from CSV."""
    price = csv_market_service.get_price(symbol.upper())
    if price is None:
        raise HTTPException(status_code=404, detail=f"No data for {symbol}")
    return price


@router.get("/candles/{symbol}")
def get_symbol_candles(symbol: str, lookback: int = 180):
    """Get historical candles for a symbol from CSV."""
    candles = csv_market_service.get_candles(symbol.upper(), lookback)
    if candles is None:
        raise HTTPException(status_code=404, detail=f"No data for {symbol}")
    return {
        "symbol": symbol.upper(),
        "lookback_minutes": lookback,
        "count": len(candles),
        "candles": candles,
    }


@router.get("/structure/{symbol}")
def detect_symbol_structure(symbol: str, lookback: int = 180):
    """Detect market structure for a symbol from CSV data."""
    result = csv_market_service.detect_structure(symbol.upper(), lookback)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Insufficient data for {symbol}")
    return result


@router.get("/structure/all")
def detect_all_structures(lookback: int = 180):
    """Detect structures for all symbols from CSV."""
    symbols = [
        "XAUUSD", "BTCUSD", "EURUSD", "GBPUSD", "USDJPY",
        "JP225", "US500", "XAGUSD", "ETHUSD", "XBRUSD", "XTIUSD"
    ]
    return csv_market_service.detect_all_structures(symbols, lookback)
