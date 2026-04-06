"""CSV-based market service - reads from EA-generated CSV files, no polling."""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from .config import settings
from .market_structure_detector import (
    MarketState,
    detect_market_structure,
    get_state_description,
)

logger = logging.getLogger(__name__)

# CSV data root - should match where EA writes
CSV_DATA_ROOT = getattr(settings, 'csv_data_root', r"C:\Users\Administrator\AppData\Roaming\MetaQuotes\Terminal\Common\Files\openclaw_data")

# Time column candidates
TIME_COLUMNS = [
    "time_broker", "time_local", "timestamp_epoch", "timestamp_ms", "timestamp",
    "time", "time_beijing", "datetime", "t"
]

# Price columns
BID_COLUMNS = ["bid", "Bid", "BID"]
ASK_COLUMNS = ["ask", "Ask", "ASK"]
CLOSE_COLUMNS = ["close", "Close", "last", "Last", "price"]


def get_latest_date_folder(root: str) -> Optional[str]:
    """Find latest YYYY-MM-DD folder."""
    root_path = Path(root)
    if not root_path.exists():
        logger.warning("CSV data root not found: %s", root)
        return None
    
    folders = []
    for item in root_path.iterdir():
        if item.is_dir() and len(item.name) == 10 and item.name[4] == "-" and item.name[7] == "-":
            try:
                datetime.strptime(item.name, "%Y-%m-%d")
                folders.append(item.name)
            except ValueError:
                pass
    
    if not folders:
        return None
    return sorted(folders, reverse=True)[0]


def load_csv_file(file_path: str) -> Optional[pd.DataFrame]:
    """Load a CSV file."""
    try:
        df = pd.read_csv(file_path, engine="python")
        if df.empty:
            return None
        return df
    except Exception as exc:
        logger.debug("Failed to load CSV %s: %s", file_path, exc)
        return None


def get_latest_from_csv(symbol: str, date_folder: str) -> Optional[dict]:
    """Get latest tick from CSV for a symbol."""
    root = Path(CSV_DATA_ROOT)
    csv_path = root / date_folder / f"{symbol.upper()}.csv"
    
    if not csv_path.exists():
        # Try lowercase
        csv_path = root / date_folder / f"{symbol.lower()}.csv"
        if not csv_path.exists():
            return None
    
    df = load_csv(str(csv_path))
    if df is None or df.empty:
        return None
    
    columns = list(df.columns)
    
    # Find time column
    time_col = None
    for col in TIME_COLUMNS:
        if col in columns:
            time_col = col
            break
    if time_col is None:
        time_col = columns[0]
    
    # Find price columns
    bid_col = next((c for c in BID_COLUMNS if c in columns), None)
    ask_col = next((c for c in ASK_COLUMNS if c in columns), None)
    close_col = next((c for c in CLOSE_COLUMNS if c in columns), None)
    
    # Get last row
    last = df.iloc[-1]
    
    result = {
        "symbol": symbol.upper(),
        "bid": float(last[bid_col]) if bid_col else None,
        "ask": float(last[ask_col]) if ask_col else None,
        "last": float(last[close_col]) if close_col else None,
    }
    
    # Try to get timestamp
    try:
        ts_val = last[time_col]
        if pd.notna(ts_val):
            if isinstance(ts_val, (int, float)):
                if ts_val > 1e12:
                    result["time"] = datetime.fromtimestamp(ts_val / 1000, tz=timezone.utc).isoformat()
                else:
                    result["time"] = datetime.fromtimestamp(ts_val, tz=timezone.utc).isoformat()
            else:
                result["time"] = str(ts_val)
    except Exception:
        pass
    
    return result


def get_candles_from_csv(symbol: str, date_folder: str, lookback_minutes: int = 180) -> Optional[list[dict]]:
    """Get historical candles from CSV for structure analysis."""
    root = Path(CSV_DATA_ROOT)
    csv_path = root / date_folder / f"{symbol.upper()}.csv"
    
    if not csv_path.exists():
        return None
    
    df = load_csv(str(csv_path))
    if df is None or df.empty:
        return None
    
    columns = list(df.columns)
    
    # Find time column
    time_col = None
    for col in TIME_COLUMNS:
        if col in columns:
            time_col = col
            break
    if time_col is None:
        time_col = columns[0]
    
    # Find price columns
    high_col = "high" if "high" in columns else None
    low_col = "low" if "low" in columns else None
    close_col = next((c for c in CLOSE_COLUMNS if c in columns), None)
    open_col = "open" if "open" in columns else None
    
    # Parse timestamps and filter by lookback
    try:
        df["_ts"] = pd.to_datetime(df[time_col], errors="coerce", utc=True, unit="ms")
        if df["_ts"].isna().all():
            df["_ts"] = pd.to_datetime(df[time_col], errors="coerce", utc=True, unit="s")
        df = df.dropna(subset=["_ts"])
        
        cutoff = pd.Timestamp.utcnow() - pd.Timedelta(minutes=lookback_minutes)
        df = df[df["_ts"] >= cutoff]
        df = df.sort_values("_ts")
    except Exception as exc:
        logger.warning("Time parsing failed for %s: %s", symbol, exc)
        return None
    
    if df.empty:
        return None
    
    # Convert to candles format
    candles = []
    for _, row in df.iterrows():
        candle = {
            "time": row["_ts"].strftime("%Y-%m-%dT%H:%M:%S"),
            "open": float(row[open_col]) if open_col and pd.notna(row.get(open_col)) else float(row.get(close_col, 0)),
            "high": float(row[high_col]) if high_col and pd.notna(row.get(high_col)) else float(row.get(close_col, 0)),
            "low": float(row[low_col]) if low_col and pd.notna(row.get(low_col)) else float(row.get(close_col, 0)),
            "close": float(row[close_col]) if close_col and pd.notna(row.get(close_col)) else 0,
            "volume": int(row.get("volume", 0)) if "volume" in columns else 0,
        }
        candles.append(candle)
    
    return candles


class CSVMarketService:
    """Unified service reading from CSV files - no MT5 polling."""
    
    def __init__(self):
        self.data_root = CSV_DATA_ROOT
        self.latest_folder: Optional[str] = None
    
    def get_latest_folder(self) -> Optional[str]:
        """Get latest date folder."""
        self.latest_folder = get_latest_date_folder(self.data_root)
        return self.latest_folder
    
    def get_all_prices(self) -> dict:
        """Get latest prices from all CSV files."""
        folder = self.get_latest_folder()
        if folder is None:
            return {"error": "No data folder found", "prices": {}}
        
        root = Path(self.data_root) / folder
        csv_files = list(root.glob("*.csv"))
        
        prices = {}
        for csv_file in csv_files:
            symbol = csv_file.stem.upper()
            price_data = get_latest_from_csv(symbol, folder)
            if price_data:
                prices[symbol] = price_data
        
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "data_root": self.data_root,
            "latest_folder": folder,
            "count": len(prices),
            "prices": prices,
        }
    
    def get_price(self, symbol: str) -> Optional[dict]:
        """Get latest price for one symbol."""
        folder = self.get_latest_folder()
        if folder is None:
            return None
        return get_latest_from_csv(symbol.upper(), folder)
    
    def get_candles(self, symbol: str, lookback_minutes: int = 180) -> Optional[list[dict]]:
        """Get historical candles for structure analysis."""
        folder = self.get_latest_folder()
        if folder is None:
            return None
        return get_candles_from_csv(symbol.upper(), folder, lookback_minutes)
    
    def detect_structure(self, symbol: str, lookback_minutes: int = 180) -> Optional[dict]:
        """Detect market structure from CSV data."""
        candles = self.get_candles(symbol, lookback_minutes)
        if candles is None or len(candles) < 50:
            return None
        
        import numpy as np
        
        closes = np.array([c["close"] for c in candles])
        highs = np.array([c["high"] for c in candles])
        lows = np.array([c["low"] for c in candles])
        
        result = detect_market_structure(closes, highs, lows)
        
        return {
            "symbol": symbol.upper(),
            "state": result.state.value,
            "description": get_state_description(result),
            "confidence": result.confidence,
            "metrics": {
                "slope": result.slope,
                "consistency": result.consistency,
                "displacement": result.displacement,
                "volatility": result.volatility,
                "curvature": result.curvature,
            },
            "scores": {
                "trend_score": result.trend_score,
                "reversal_score": result.reversal_score,
                "range_score": result.range_score,
            },
            "candles_count": len(candles),
            "lookback_minutes": lookback_minutes,
        }
    
    def detect_all_structures(self, symbols: list, lookback_minutes: int = 180) -> dict:
        """Detect structures for multiple symbols."""
        results = {}
        for symbol in symbols:
            try:
                struct = self.detect_structure(symbol, lookback_minutes)
                if struct:
                    results[symbol.upper()] = struct
            except Exception as exc:
                logger.warning("Structure detection failed for %s: %s", symbol, exc)
        
        return {
            "lookback_minutes": lookback_minutes,
            "count": len(results),
            "structures": results,
        }


# Global instance
csv_market_service = CSVMarketService()
