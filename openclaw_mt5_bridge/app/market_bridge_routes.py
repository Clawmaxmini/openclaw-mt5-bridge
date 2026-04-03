import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/market_bridge", tags=["market bridge"])

SNAPSHOT_FILE = Path(r"C:\Users\Administrator\Downloads\数据采集脚本\market_snapshot.json")


@router.get("/latest")
def market_bridge_latest() -> dict:
    if not SNAPSHOT_FILE.exists():
        raise HTTPException(status_code=404, detail="market snapshot file not found")

    try:
        with SNAPSHOT_FILE.open("r", encoding="utf-8") as f:
            payload = json.load(f)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail="market snapshot file is malformed") from exc
    except OSError as exc:
        raise HTTPException(status_code=500, detail="failed to read market snapshot file") from exc

    if not isinstance(payload, dict):
        raise HTTPException(status_code=500, detail="market snapshot content must be a JSON object")

    return payload
