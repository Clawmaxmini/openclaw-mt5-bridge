"""Market state API routes."""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from .state_engine import market_state_engine
from .state_models import MarketStateSummary

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/market_state", tags=["market_state"])


@router.get("/latest", response_model=MarketStateSummary)
def get_latest_states() -> MarketStateSummary:
    """Get latest market states for all symbols."""
    try:
        return market_state_engine.get_all_states()
    except Exception as exc:
        logger.error("Failed to get market states: %s", exc)
        raise HTTPException(status_code=500, detail=f"Failed to get market states: {exc}") from exc


@router.get("/{symbol}")
def get_symbol_state(symbol: str) -> dict:
    """Get detailed market state for a specific symbol."""
    try:
        state = market_state_engine.get_state(symbol.upper())
        return state.model_dump()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found") from exc
    except Exception as exc:
        logger.error("Failed to get state for %s: %s", symbol, exc)
        raise HTTPException(status_code=500, detail=f"Failed to get state: {exc}") from exc
