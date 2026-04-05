"""Market bridge routes for EA data collection."""
import json
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/bridge", tags=["bridge"])


class SnapshotUpload(BaseModel):
    """EA snapshot upload payload."""
    symbol: str
    bid: float
    ask: float
    spread_points: int
    time_broker: str
    time_local: str
    timestamp_epoch: int
    source: str = "MT5_EA"


@router.post("/snapshot/upload")
def upload_snapshot(payload: SnapshotUpload) -> dict:
    """
    Receive snapshot from MT5 EA and store in snapshot directory.
    
    EA should POST to this endpoint every 3 seconds with the latest price.
    File will be stored as {symbol}.jsonl (one JSON object per line).
    """
    try:
        symbol = payload.symbol.upper()
        
        # Ensure snapshot directory exists
        snapshot_dir = Path(settings.snapshot_dir)
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        
        # Write as JSONL format (append mode)
        file_path = snapshot_dir / f"{symbol}.jsonl"
        
        record = {
            "symbol": symbol,
            "bid": payload.bid,
            "ask": payload.ask,
            "spread_points": payload.spread_points,
            "time_broker": payload.time_broker,
            "time_local": payload.time_local,
            "timestamp_epoch": payload.timestamp_epoch,
            "source": payload.source,
        }
        
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        
        logger.debug(f"Snapshot stored: {symbol} @ {payload.bid}/{payload.ask}")
        
        return {
            "status": "ok",
            "symbol": symbol,
            "file": str(file_path),
        }
        
    except Exception as exc:
        logger.error(f"Failed to store snapshot: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/snapshot/{symbol}")
def get_snapshot(symbol: str) -> dict:
    """Get latest snapshot for a symbol."""
    try:
        symbol = symbol.upper()
        file_path = Path(settings.snapshot_dir) / f"{symbol}.jsonl"
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"No snapshot found for {symbol}")
        
        # Read last line (latest)
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        if not lines:
            raise HTTPException(status_code=404, detail=f"Empty snapshot file for {symbol}")
        
        last_record = json.loads(lines[-1].strip())
        return last_record
        
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Failed to read snapshot: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))
