"""History API routes."""
import logging

from fastapi import APIRouter

from .history_service import history_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/history", tags=["history"])


@router.get("/{symbol}")
def get_symbol_history(symbol: str, limit: int = 100):
    """Get history for a symbol."""
    return {
        "symbol": symbol.upper(),
        "count": limit,
        "history": history_service.get_history(symbol.upper(), limit)
    }


@router.get("/")
def get_all_history():
    """Get all symbols with history."""
    return {
        "symbols": history_service.get_all_symbols(),
        "count": len(history_service.get_all_symbols())
    }
