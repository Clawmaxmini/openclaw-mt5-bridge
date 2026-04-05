"""CSV snapshot API routes."""
import logging

from fastapi import APIRouter, HTTPException

from .csv_snapshot_service import (
    CSV_DATA_ROOT,
    SNAPSHOT_LOOKBACK_HOURS,
    build_market_snapshot,
    get_or_build_snapshot,
    load_market_snapshot_file,
    save_market_snapshot,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/csv_snapshot", tags=["csv_snapshot"])


@router.get("/latest")
def get_latest_snapshot():
    """
    Get the latest market snapshot.
    If cached file exists and is fresh, return it.
    Otherwise rebuild on demand.
    """
    try:
        snapshot = get_or_build_snapshot(
            data_root=CSV_DATA_ROOT,
            lookback_hours=SNAPSHOT_LOOKBACK_HOURS,
        )
        return snapshot
    except Exception as exc:
        logger.error("Failed to get snapshot: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/rebuild")
def rebuild_snapshot():
    """
    Force rebuild the market snapshot from CSV files.
    Returns a summary of the rebuild operation.
    """
    try:
        snapshot = build_market_snapshot(
            data_root=CSV_DATA_ROOT,
            lookback_hours=SNAPSHOT_LOOKBACK_HOURS,
        )
        
        success = save_market_snapshot(snapshot)
        
        symbol_count = len(snapshot.get("symbols", {}))
        
        return {
            "ok": success,
            "symbol_count": symbol_count,
            "latest_folder": snapshot.get("latest_folder"),
            "generated_at": snapshot.get("generated_at"),
        }
    except Exception as exc:
        logger.error("Failed to rebuild snapshot: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/symbol/{symbol}")
def get_symbol_snapshot(symbol: str):
    """
    Get snapshot for a specific symbol.
    Returns 404 if symbol not found.
    """
    try:
        snapshot = get_or_build_snapshot(
            data_root=CSV_DATA_ROOT,
            lookback_hours=SNAPSHOT_LOOKBACK_HOURS,
        )
        
        symbol_upper = symbol.upper()
        if symbol_upper not in snapshot.get("symbols", {}):
            raise HTTPException(
                status_code=404,
                detail=f"Symbol {symbol_upper} not found in snapshot"
            )
        
        return snapshot["symbols"][symbol_upper]
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get symbol snapshot: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
