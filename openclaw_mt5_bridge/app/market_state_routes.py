"""Market state API routes - CSV based."""
import logging

from fastapi import APIRouter, HTTPException

from .csv_market_service import csv_market_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/market_state", tags=["market_state"])


@router.get("/latest")
def get_latest_states():
    """Get latest market states for all symbols."""
    try:
        return csv_market_service.get_all_prices()
    except Exception as exc:
        logger.error("Failed to get market states: %s", exc)
        raise HTTPException(status_code=500, detail=f"Failed: {exc}") from exc


@router.get("/{symbol}")
def get_symbol_state(symbol: str):
    """Get detailed state for a specific symbol."""
    try:
        state = csv_market_service.detect_structure(symbol.upper())
        if state is None:
            raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found")
        return state
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed for %s: %s", symbol, exc)
        raise HTTPException(status_code=500, detail=f"Failed: {exc}") from exc
