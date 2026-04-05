"""MT5 Live API routes."""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException

from .mt5_live_service import mt5_live_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/mt5", tags=["mt5_live"])


def require_mt5():
    """Raise 503 if MT5 not connected."""
    if not mt5_live_service.is_connected():
        raise HTTPException(status_code=503, detail="MT5 not connected")


@router.get("/live/tick/{symbol}")
def get_live_tick(symbol: str):
    """Get latest tick for a symbol."""
    require_mt5()
    tick = mt5_live_service.get_tick(symbol.upper())
    if tick is None:
        raise HTTPException(status_code=404, detail=f"No tick for {symbol}")
    return tick


@router.get("/live/candles/{symbol}")
def get_live_candles(
    symbol: str,
    timeframe: str = "M1",
    count: int = 100,
):
    """Get historical candles for a symbol."""
    require_mt5()
    candles = mt5_live_service.get_candles(symbol.upper(), timeframe, count)
    if candles is None:
        raise HTTPException(status_code=404, detail=f"No candles for {symbol}")
    return {
        "symbol": symbol.upper(),
        "timeframe": timeframe,
        "count": len(candles),
        "candles": candles,
    }


@router.get("/live/account")
def get_live_account():
    """Get MT5 account info."""
    require_mt5()
    info = mt5_live_service.get_account_info()
    if info is None:
        raise HTTPException(status_code=503, detail="Cannot get account info")
    return info


@router.get("/live/positions")
def get_live_positions(symbol: Optional[str] = None):
    """Get open positions."""
    require_mt5()
    return mt5_live_service.get_positions(symbol.upper() if symbol else None)


@router.get("/live/symbol/{symbol}")
def get_live_symbol(symbol: str):
    """Get symbol info."""
    require_mt5()
    info = mt5_live_service.get_symbol_info(symbol.upper())
    if info is None:
        raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found")
    return info


@router.get("/live/status")
def get_live_status():
    """Check MT5 live connection status."""
    return {
        "connected": mt5_live_service.is_connected(),
        "available": mt5_live_service.connected if hasattr(mt5_live_service, 'connected') else False,
    }
