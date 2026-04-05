import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


def _resolve_data_dir() -> Path:
    """Resolve data directory relative to this file, not hardcoded paths."""
    base = Path(__file__).resolve().parent.parent
    data_root = os.getenv("DATA_ROOT", "")
    if data_root:
        return Path(data_root)
    return base / "data"


BASE_DIR = _resolve_data_dir()
DATA_DIR = BASE_DIR / "data"
SNAPSHOT_DIR = DATA_DIR / "snapshots"
BARS_DIR = DATA_DIR / "bars"
SIGNALS_DIR = DATA_DIR / "signals"
LOGS_DIR = DATA_DIR / "logs"

for _dir in [DATA_DIR, SNAPSHOT_DIR, BARS_DIR, SIGNALS_DIR, LOGS_DIR]:
    _dir.mkdir(parents=True, exist_ok=True)


# CSV Snapshot configuration
CSV_DATA_ROOT = os.getenv(
    "CSV_DATA_ROOT",
    r"C:\Users\Administrator\AppData\Roaming\MetaQuotes\Terminal\Common\Files\openclaw_data"
)
SNAPSHOT_LOOKBACK_HOURS = int(os.getenv("SNAPSHOT_LOOKBACK_HOURS", "6"))
SNAPSHOT_REFRESH_SECONDS = int(os.getenv("SNAPSHOT_REFRESH_SECONDS", "30"))
SNAPSHOT_OUTPUT_FILE = os.getenv(
    "SNAPSHOT_OUTPUT_FILE",
    os.path.join(CSV_DATA_ROOT, "market_snapshot.json")
)


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "OpenClaw-MT5-Bridge")
    app_env: str = os.getenv("APP_ENV", "dev")
    app_host: str = os.getenv("APP_HOST", "0.0.0.0")
    app_port: int = int(os.getenv("APP_PORT", "8080"))

    mt5_login: int = int(os.getenv("MT5_LOGIN", "0"))
    mt5_password: str = os.getenv("MT5_PASSWORD", "")
    mt5_server: str = os.getenv("MT5_SERVER", "")
    mt5_path: str = os.getenv("MT5_PATH", "")
    mt5_timeout: int = int(os.getenv("MT5_TIMEOUT", "10000"))
    mt5_deviation: int = int(os.getenv("MT5_DEVIATION", "20"))
    mt5_magic: int = int(os.getenv("MT5_MAGIC", "910001"))

    data_root: str = os.getenv("DATA_ROOT", str(DATA_DIR))
    snapshot_dir: str = os.getenv("SNAPSHOT_DIR", str(SNAPSHOT_DIR))
    bars_dir: str = os.getenv("BARS_DIR", str(BARS_DIR))
    signals_dir: str = os.getenv("SIGNALS_DIR", str(SIGNALS_DIR))
    logs_dir: str = os.getenv("LOGS_DIR", str(LOGS_DIR))
    default_timezone: str = os.getenv("DEFAULT_TIMEZONE", "Asia/Shanghai")
    default_bar_timeframe: str = os.getenv("DEFAULT_BAR_TIMEFRAME", "M1")
    default_history_hours: int = int(os.getenv("DEFAULT_HISTORY_HOURS", "6"))
    default_history_limit: int = int(os.getenv("DEFAULT_HISTORY_LIMIT", "360"))

    # CSV Snapshot settings
    csv_data_root: str = CSV_DATA_ROOT
    snapshot_lookback_hours: int = SNAPSHOT_LOOKBACK_HOURS
    snapshot_refresh_seconds: int = SNAPSHOT_REFRESH_SECONDS
    snapshot_output_file: str = SNAPSHOT_OUTPUT_FILE


settings = Settings()
