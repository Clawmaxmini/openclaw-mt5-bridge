"""History tracking service - stores market structure history for visualization."""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

HISTORY_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "history"
HISTORY_DIR.mkdir(parents=True, exist_ok=True)


class HistoryService:
    """Service to track and store market structure history."""

    def __init__(self):
        self.history_file = HISTORY_DIR / "structure_history.json"
        self._history: dict = {}
        self._load()

    def _load(self):
        """Load history from disk."""
        try:
            if self.history_file.exists():
                with open(self.history_file, "r", encoding="utf-8") as f:
                    self._history = json.load(f)
                logger.info("Loaded history for %d symbols", len(self._history))
        except Exception as e:
            logger.warning("Failed to load history: %s", e)
            self._history = {}

    def _save(self):
        """Save history to disk."""
        try:
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(self._history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error("Failed to save history: %s", e)

    def record(self, symbol: str, data: dict):
        """Record a data point for a symbol."""
        if symbol not in self._history:
            self._history[symbol] = []

        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "bid": data.get("bid"),
            "ask": data.get("ask"),
            "state": data.get("state"),
            "confidence": data.get("confidence"),
            "slope": data.get("slope"),
            "consistency": data.get("consistency"),
            "displacement": data.get("displacement"),
            "volatility": data.get("volatility"),
            "curvature": data.get("curvature"),
        }

        self._history[symbol].append(entry)

        # Keep only last 1000 entries per symbol
        if len(self._history[symbol]) > 1000:
            self._history[symbol] = self._history[symbol][-1000:]

        self._save()

    def get_history(self, symbol: str, limit: int = 100) -> list:
        """Get history for a symbol."""
        if symbol not in self._history:
            return []
        return self._history[symbol][-limit:]

    def get_all_symbols(self) -> list:
        """Get all symbols with history."""
        return list(self._history.keys())


# Global instance
history_service = HistoryService()
