"""Price prediction service with MiniMax LLM."""
import asyncio
import json
import logging
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# MiniMax API Configuration
MINIMAX_API_URL = "https://api.minimax.chat/v1/text/chatcompletion_v2"
MINIMAX_API_KEY = os.getenv("MINIMAX_API_KEY", "")
MINIMAX_MODEL = "MiniMax-Text-01"

# Prediction settings
PREDICTION_MINUTES = 10  # Predict 10 minutes ahead
PREDICTION_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "predictions"
PREDICTION_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class Prediction:
    """A single price prediction."""
    symbol: str
    predicted_price: float
    actual_price: Optional[float]
    target_time: str  # ISO format
    predicted_at: str  # ISO format
    verified_at: Optional[str]  # ISO format
    error_pct: Optional[float]
    status: str  # "pending", "verified", "expired"


class PredictionService:
    """Service to create price predictions using LLM."""

    def __init__(self):
        self.predictions: list[Prediction] = []
        self._load_predictions()

    def _load_predictions(self):
        """Load existing predictions from disk."""
        try:
            file_path = PREDICTION_DIR / "predictions.json"
            if file_path.exists():
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.predictions = [Prediction(**p) for p in data]
                logger.info("Loaded %d predictions", len(self.predictions))
        except Exception as e:
            logger.warning("Failed to load predictions: %s", e)

    def _save_predictions(self):
        """Save predictions to disk."""
        try:
            file_path = PREDICTION_DIR / "predictions.json"
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump([asdict(p) for p in self.predictions], f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error("Failed to save predictions: %s", e)

    async def _call_minimax(self, prompt: str) -> Optional[str]:
        """Call MiniMax API for prediction."""
        if not MINIMAX_API_KEY:
            logger.warning("MiniMax API key not set")
            return None

        headers = {
            "Authorization": f"Bearer {MINIMAX_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": MINIMAX_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 100,
            "temperature": 0.3,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(MINIMAX_API_URL, headers=headers, json=payload)
                if response.status_code == 200:
                    data = response.json()
                    return data.get("choices", [{}])[0].get("message", {}).get("content", "")
                else:
                    logger.error("MiniMax API error: %s", response.text)
                    return None
        except Exception as e:
            logger.error("MiniMax API call failed: %s", e)
            return None

    def _get_current_data_for_symbol(self, symbol: str) -> dict:
        """Get current price and recent data for a symbol."""
        try:
            # Try to get from CSV market service
            from .csv_market_service import csv_market_service
            price_data = csv_market_service.get_price(symbol)
            if price_data:
                return price_data
        except Exception:
            pass

        # Fallback to snapshot file
        try:
            from .csv_snapshot_service import load_market_snapshot_file
            snapshot = load_market_snapshot_file()
            if snapshot and symbol in snapshot.get("symbols", {}):
                return snapshot["symbols"][symbol]
        except Exception:
            pass

        return {}

    def _build_prediction_prompt(self, symbol: str, current_price: float, lookback_data: list) -> str:
        """Build prompt for LLM to predict price."""
        # Format lookback data
        data_str = "\n".join([f"- {d.get('time', 'N/A')}: {d.get('bid', current_price):.5f}" for d in lookback_data[-10:]])

        prompt = f"""You are a financial analyst predicting {symbol} price movement.

Current price: {current_price:.5f}

Recent price history (last 10 data points):
{data_str}

Task: Predict the price of {symbol} exactly 10 minutes from now.

Based on the trend, volatility, and patterns in the data, predict what the price will be in 10 minutes.

Rules:
- Only output the predicted price as a number with 5 decimal places
- No explanation, no text, only the number
- Be confident and precise

Predicted price:"""
        return prompt

    async def create_prediction(self, symbol: str) -> Optional[Prediction]:
        """Create a new price prediction for a symbol."""
        # Get current data
        current_data = self._get_current_data_for_symbol(symbol)
        current_price = current_data.get("bid") or current_data.get("last_price")

        if not current_price:
            logger.error("Cannot get current price for %s", symbol)
            return None

        # Get lookback data (recent candles)
        lookback_data = []
        try:
            from .csv_market_service import csv_market_service
            candles = csv_market_service.get_candles(symbol, lookback_minutes=30)
            if candles:
                lookback_data = candles[-10:]
        except Exception:
            pass

        # Build prompt and call LLM
        prompt = self._build_prediction_prompt(symbol, current_price, lookback_data)
        prediction_text = await self._call_minimax(prompt)

        if not prediction_text:
            # Fallback: use simple trend extrapolation
            predicted_price = current_price
            logger.warning("LLM call failed, using fallback for %s", symbol)
        else:
            try:
                # Parse the prediction
                predicted_price = float(prediction_text.strip().split()[0])
            except ValueError:
                predicted_price = current_price
                logger.warning("Failed to parse prediction for %s: %s", symbol, prediction_text)

        # Calculate target time (10 minutes from now)
        target_time = datetime.now(timezone.utc) + timedelta(minutes=PREDICTION_MINUTES)

        prediction = Prediction(
            symbol=symbol.upper(),
            predicted_price=predicted_price,
            actual_price=None,
            target_time=target_time.isoformat(),
            predicted_at=datetime.now(timezone.utc).isoformat(),
            verified_at=None,
            error_pct=None,
            status="pending"
        )

        self.predictions.append(prediction)
        self._save_predictions()

        logger.info("Created prediction for %s: %.5f (target: %s)", symbol, predicted_price, target_time.isoformat())
        return prediction

    async def verify_predictions(self):
        """Check and verify any pending predictions that have reached their target time."""
        now = datetime.now(timezone.utc)
        verified = []

        for pred in self.predictions:
            if pred.status != "pending":
                continue

            target_time = datetime.fromisoformat(pred.target_time.replace("Z", "+00:00"))
            if now >= target_time:
                # Get actual price
                actual_data = self._get_current_data_for_symbol(pred.symbol)
                actual_price = actual_data.get("bid") or actual_data.get("last_price")

                if actual_price:
                    pred.actual_price = actual_price
                    pred.verified_at = now.isoformat()

                    # Calculate error percentage
                    if pred.predicted_price != 0:
                        pred.error_pct = abs((actual_price - pred.predicted_price) / pred.predicted_price * 100)
                    else:
                        pred.error_pct = None

                    pred.status = "verified"
                    verified.append(pred)
                    logger.info("Verified %s: predicted=%.5f, actual=%.5f, error=%.2f%%",
                               pred.symbol, pred.predicted_price, actual_price, pred.error_pct or 0)

        if verified:
            self._save_predictions()

        return verified

    def get_predictions(self, symbol: Optional[str] = None, limit: int = 20) -> list:
        """Get recent predictions, optionally filtered by symbol."""
        preds = self.predictions
        if symbol:
            preds = [p for p in preds if p.symbol.upper() == symbol.upper()]
        return sorted(preds, key=lambda x: x.predicted_at, reverse=True)[:limit]

    def get_pending_predictions(self) -> list:
        """Get all pending predictions."""
        return [p for p in self.predictions if p.status == "pending"]

    def get_statistics(self) -> dict:
        """Calculate prediction accuracy statistics."""
        verified = [p for p in self.predictions if p.status == "verified" and p.error_pct is not None]
        if not verified:
            return {"total": 0, "avg_error": 0, "max_error": 0, "min_error": 0}

        errors = [p.error_pct for p in verified]
        return {
            "total": len(verified),
            "avg_error": sum(errors) / len(errors),
            "max_error": max(errors),
            "min_error": min(errors),
            "pending": len(self.get_pending_predictions())
        }


# Global instance
prediction_service = PredictionService()


async def background_prediction_verifier():
    """Background task to verify pending predictions every minute."""
    while True:
        try:
            await asyncio.sleep(60)  # Check every minute
            verified = await prediction_service.verify_predictions()
            if verified:
                logger.info("Background verified %d predictions", len(verified))
        except asyncio.CancelledError:
            logger.info("Background prediction verifier cancelled")
            break
        except Exception as e:
            logger.error("Background verifier error: %s", e)
