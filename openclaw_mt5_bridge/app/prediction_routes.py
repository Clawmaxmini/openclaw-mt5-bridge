"""Price prediction API routes."""
import asyncio
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from .prediction_service import background_prediction_verifier, prediction_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/prediction", tags=["prediction"])

# Start background verifier on module load
_verifier_task = None


def start_background_verifier():
    global _verifier_task
    if _verifier_task is None:
        _verifier_task = asyncio.create_task(background_prediction_verifier())
        logger.info("Background prediction verifier started")


@router.on_event("startup")
async def startup():
    start_background_verifier()


@router.post("/create/{symbol}")
async def create_prediction(symbol: str):
    """Create a new price prediction for a symbol (10 minutes ahead)."""
    result = await prediction_service.create_prediction(symbol.upper())
    if result is None:
        raise HTTPException(status_code=500, detail="Failed to create prediction")
    return {
        "status": "created",
        "prediction": {
            "symbol": result.symbol,
            "predicted_price": result.predicted_price,
            "target_time": result.target_time,
            "predicted_at": result.predicted_at,
            "status": result.status,
        }
    }


@router.get("/pending")
async def get_pending():
    """Get all pending predictions."""
    pending = prediction_service.get_pending_predictions()
    return {
        "count": len(pending),
        "predictions": [
            {
                "symbol": p.symbol,
                "predicted_price": p.predicted_price,
                "target_time": p.target_time,
                "time_remaining_seconds": max(0, int(
                    (datetime.fromisoformat(p.target_time.replace("Z", "+00:00")) - datetime.now(timezone.utc)).total_seconds()
                ))
            }
            for p in pending
        ]
    }


@router.get("/history")
async def get_history(symbol: str = None, limit: int = 20):
    """Get prediction history."""
    history = prediction_service.get_predictions(symbol=symbol, limit=limit)
    return {
        "count": len(history),
        "predictions": [
            {
                "symbol": p.symbol,
                "predicted_price": p.predicted_price,
                "actual_price": p.actual_price,
                "target_time": p.target_time,
                "verified_at": p.verified_at,
                "error_pct": p.error_pct,
                "status": p.status,
            }
            for p in history
        ]
    }


@router.get("/statistics")
async def get_statistics():
    """Get prediction accuracy statistics."""
    return prediction_service.get_statistics()


@router.post("/verify")
async def force_verify():
    """Force verification of all pending predictions."""
    verified = await prediction_service.verify_predictions()
    return {
        "verified_count": len(verified),
        "predictions": [
            {
                "symbol": p.symbol,
                "predicted_price": p.predicted_price,
                "actual_price": p.actual_price,
                "error_pct": p.error_pct,
            }
            for p in verified
        ]
    }
