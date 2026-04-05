"""Market watch API routes."""
import logging

from fastapi import APIRouter

from .market_watch_service import market_watch_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/market_watch", tags=["market_watch"])


@router.get("/prices")
def get_all_prices():
    """Get aggregated prices for all watch symbols."""
    return market_watch_service.get_all_prices()


@router.get("/price/{symbol}")
def get_symbol_price(symbol: str):
    """Get price for a specific symbol."""
    price_info = market_watch_service.get_price(symbol.upper())
    if price_info is None:
        return {"symbol": symbol.upper(), "available": False}
    return price_info
