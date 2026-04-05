"""CSV snapshot aggregation service for MT5 EA data."""
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

import pandas as pd

logger = logging.getLogger(__name__)

# Default configuration
CSV_DATA_ROOT = r"C:\Users\Administrator\AppData\Roaming\MetaQuotes\Terminal\Common\Files\openclaw_data"
SNAPSHOT_LOOKBACK_HOURS = 6
SNAPSHOT_REFRESH_SECONDS = 30
SNAPSHOT_OUTPUT_FILE = r"C:\Users\Administrator\AppData\Roaming\MetaQuotes\Terminal\Common\Files\openclaw_data\market_snapshot.json"

# Time column candidates (in order of priority)
TIME_COLUMNS = [
    "timestamp_ms", "timestamp", "time", "time_beijing", "time_local",
    "datetime", "datetime_beijing", "time_broker", "broker_time"
]

# Price column candidates
BID_COLUMNS = ["bid", "Bid", "BID"]
ASK_COLUMNS = ["ask", "Ask", "ASK"]
LAST_COLUMNS = ["last", "Last", "close", "Close", "price", "Price"]
POINTS_COLUMNS = ["points", "point", "pts", "Points"]


def get_latest_date_folder(root: str) -> Optional[str]:
    """
    Find the latest YYYY-MM-DD folder under root.
    Returns folder name string, or None if not found.
    """
    root_path = Path(root)
    if not root_path.exists():
        logger.warning("CSV data root does not exist: %s", root)
        return None
    
    date_folders = []
    for item in root_path.iterdir():
        if item.is_dir():
            name = item.name
            # Check if folder name matches YYYY-MM-DD pattern
            if len(name) == 10 and name[4] == "-" and name[7] == "-":
                try:
                    datetime.strptime(name, "%Y-%m-%d")
                    date_folders.append(name)
                except ValueError:
                    pass
    
    if not date_folders:
        logger.warning("No date folders found in: %s", root)
        return None
    
    # Return most recent (sorted desc, take first)
    latest = sorted(date_folders, reverse=True)[0]
    logger.info("Latest date folder: %s", latest)
    return latest


def load_symbol_csv(file_path: str) -> Optional[Any]:
    """
    Load a CSV file using pandas.
    Returns DataFrame or None on failure.
    """
    try:
        df = pd.read_csv(file_path, engine="python")
        if df.empty:
            logger.debug("Empty CSV file: %s", file_path)
            return None
        return df
    except Exception as exc:
        logger.warning("Failed to load CSV %s: %s", file_path, exc)
        return None


def _find_column(df_columns: list, candidates: list) -> Optional[str]:
    """Find first matching column name from candidates."""
    for col in candidates:
        if col in df_columns:
            return col
    return None


def _parse_timestamp(value: Any) -> Optional[datetime]:
    """Parse timestamp value to datetime."""
    if value is None:
        return None
    
    try:
        # Try numeric (ms or s)
        val = float(value)
        if val > 1e12:  # milliseconds
            return datetime.fromtimestamp(val / 1000, tz=timezone.utc)
        else:  # seconds
            return datetime.fromtimestamp(val, tz=timezone.utc)
    except (ValueError, TypeError, OSError):
        pass
    
    # Try string parsing
    try:
        return pd.to_datetime(value, errors="coerce").to_pydatetime()
    except Exception:
        return None


def normalize_symbol_snapshot(symbol: str, df: Any, lookback_hours: int = 6) -> Optional[dict]:
    """
    Convert a symbol DataFrame into a normalized snapshot dict.
    Returns None if insufficient data.
    """
    if df is None or df.empty:
        return None
    
    columns = list(df.columns)
    
    # Find time column
    time_col = _find_column(columns, TIME_COLUMNS)
    if time_col is None:
        logger.debug("No time column found in %s, columns: %s", symbol, columns)
        return None
    
    # Parse timestamps
    try:
        # Parse with UTC and unified timezone
        df["_parsed_time"] = pd.to_datetime(df[time_col], errors="coerce", utc=True)
        df = df.dropna(subset=["_parsed_time"])
        if df.empty:
            logger.debug("No valid timestamps after parsing for %s", symbol)
            return None
    except Exception as exc:
        logger.warning("Time parsing failed for %s: %s", symbol, exc)
        return None
    
    # Filter by lookback window
    now_ts = pd.Timestamp.utcnow()
    cutoff_time = now_ts - pd.Timedelta(hours=lookback_hours)
    df_recent = df[df["_parsed_time"] >= cutoff_time].copy()
    
    if df_recent.empty:
        logger.debug("No data within %d hours for %s", lookback_hours, symbol)
        return None
    
    # Find price columns
    bid_col = _find_column(columns, BID_COLUMNS)
    ask_col = _find_column(columns, ASK_COLUMNS)
    last_col = _find_column(columns, LAST_COLUMNS)
    points_col = _find_column(columns, POINTS_COLUMNS)
    
    # Get latest row
    latest = df_recent.iloc[-1]
    last_time = latest["_parsed_time"]
    
    # Determine prices
    bid = None
    ask = None
    last_price = None
    spread = None
    
    if bid_col and ask_col:
        try:
            bid = float(latest[bid_col])
            ask = float(latest[ask_col])
            spread = ask - bid
            if last_col:
                last_price = float(latest[last_col])
            else:
                last_price = (bid + ask) / 2
        except (ValueError, TypeError):
            pass
    elif last_col:
        try:
            last_price = float(latest[last_col])
        except (ValueError, TypeError):
            return None
    else:
        logger.debug("No price columns found for %s", symbol)
        return None
    
    # Get points
    points = None
    if points_col:
        try:
            points = int(latest[points_col])
        except (ValueError, TypeError):
            pass
    
    # Count rows used
    rows_used = len(df_recent)
    
    # Format time string
    last_update = last_time.strftime("%Y-%m-%dT%H:%M:%S") if last_time else None
    
    return {
        "symbol": symbol,
        "last_price": last_price,
        "bid": bid,
        "ask": ask,
        "spread": spread,
        "points": points,
        "last_update": last_update,
        "rows_used": rows_used,
    }


def build_market_snapshot(
    data_root: str = CSV_DATA_ROOT,
    lookback_hours: int = SNAPSHOT_LOOKBACK_HOURS,
) -> dict:
    """
    Scan data_root for latest date folder, read all CSV files,
    aggregate into a unified snapshot dict.
    """
    snapshot = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
        "data_root": data_root,
        "latest_folder": None,
        "lookback_hours": lookback_hours,
        "symbols": {},
    }
    
    # Find latest date folder
    latest_folder = get_latest_date_folder(data_root)
    if latest_folder is None:
        logger.warning("No date folder found, returning empty snapshot")
        return snapshot
    
    snapshot["latest_folder"] = latest_folder
    date_path = Path(data_root) / latest_folder
    
    # Find all CSV files
    csv_files = list(date_path.glob("*.csv"))
    if not csv_files:
        logger.info("No CSV files in %s", date_path)
        return snapshot
    
    logger.info("Found %d CSV files in %s", len(csv_files), date_path)
    
    success_count = 0
    skip_count = 0
    
    for csv_file in csv_files:
        symbol = csv_file.stem.upper()
        
        if symbol in snapshot["symbols"]:
            # Already processed
            continue
        
        df = load_symbol_csv(str(csv_file))
        if df is None:
            skip_count += 1
            continue
        
        normalized = normalize_symbol_snapshot(symbol, df, lookback_hours)
        if normalized is None:
            skip_count += 1
            continue
        
        normalized["source_file"] = str(csv_file)
        snapshot["symbols"][symbol] = normalized
        success_count += 1
        logger.debug("Processed %s: %s", symbol, normalized.get("last_update"))
    
    logger.info(
        "Snapshot built: %d symbols ok, %d skipped",
        success_count, skip_count
    )
    
    return snapshot


def save_market_snapshot(snapshot: dict, output_file: str = SNAPSHOT_OUTPUT_FILE) -> bool:
    """Save snapshot dict to JSON file."""
    try:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, ensure_ascii=False, indent=2)
        
        logger.info("Snapshot saved to: %s", output_file)
        return True
    except Exception as exc:
        logger.error("Failed to save snapshot to %s: %s", output_file, exc)
        return False


def load_market_snapshot_file(output_file: str = SNAPSHOT_OUTPUT_FILE) -> Optional[dict]:
    """Load existing snapshot from JSON file."""
    try:
        file_path = Path(output_file)
        if not file_path.exists():
            logger.debug("Snapshot file not found: %s", output_file)
            return None
        
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        logger.warning("Failed to load snapshot from %s: %s", output_file, exc)
        return None


def get_or_build_snapshot(
    data_root: str = CSV_DATA_ROOT,
    output_file: str = SNAPSHOT_OUTPUT_FILE,
    lookback_hours: int = SNAPSHOT_LOOKBACK_HOURS,
) -> dict:
    """
    Get snapshot: try loading from file first, if stale or missing, rebuild.
    """
    snapshot = load_market_snapshot_file(output_file)
    
    if snapshot is None:
        logger.info("No existing snapshot, building new one")
        snapshot = build_market_snapshot(data_root, lookback_hours)
        save_market_snapshot(snapshot, output_file)
        return snapshot
    
    # Check if stale (older than 5 minutes)
    try:
        generated = datetime.fromisoformat(snapshot["generated_at"])
        age_seconds = (datetime.now(timezone.utc) - generated.replace(tzinfo=timezone.utc)).total_seconds()
        
        if age_seconds > 300:  # 5 minutes
            logger.info("Snapshot is %d seconds old, rebuilding", int(age_seconds))
            snapshot = build_market_snapshot(data_root, lookback_hours)
            save_market_snapshot(snapshot, output_file)
    except Exception as exc:
        logger.warning("Error checking snapshot age: %s, rebuilding", exc)
        snapshot = build_market_snapshot(data_root, lookback_hours)
        save_market_snapshot(snapshot, output_file)
    
    return snapshot
