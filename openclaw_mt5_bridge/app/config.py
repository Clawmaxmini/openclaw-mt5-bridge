import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


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

    data_root: str = os.getenv("DATA_ROOT", "C:/MT5BridgeData")
    snapshot_dir: str = os.getenv("SNAPSHOT_DIR", os.path.join(data_root, "snapshots"))
    bars_dir: str = os.getenv("BARS_DIR", os.path.join(data_root, "bars"))
    signals_dir: str = os.getenv("SIGNALS_DIR", os.path.join(data_root, "signals"))
    logs_dir: str = os.getenv("LOGS_DIR", os.path.join(data_root, "logs"))
    default_timezone: str = os.getenv("DEFAULT_TIMEZONE", "Asia/Shanghai")
    default_bar_timeframe: str = os.getenv("DEFAULT_BAR_TIMEFRAME", "M1")
    default_history_hours: int = int(os.getenv("DEFAULT_HISTORY_HOURS", "6"))
    default_history_limit: int = int(os.getenv("DEFAULT_HISTORY_LIMIT", "360"))


settings = Settings()
