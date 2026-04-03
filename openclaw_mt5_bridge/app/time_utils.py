from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from .config import settings


def beijing_tz() -> ZoneInfo:
    return ZoneInfo(settings.default_timezone)


def now_beijing_str() -> str:
    return datetime.now(beijing_tz()).isoformat()


def utc_to_beijing_str(utc_dt: datetime) -> str:
    if utc_dt.tzinfo is None:
        utc_dt = utc_dt.replace(tzinfo=timezone.utc)
    return utc_dt.astimezone(beijing_tz()).isoformat()


def parse_time_to_beijing(value: str | None) -> tuple[str | None, str]:
    if not value:
        now_bj = now_beijing_str()
        return None, now_bj

    candidate = value.strip()
    try:
        if candidate.isdigit():
            dt = datetime.fromtimestamp(int(candidate), tz=timezone.utc)
            return dt.isoformat(), utc_to_beijing_str(dt)

        dt = datetime.fromisoformat(candidate.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            bj = dt.replace(tzinfo=beijing_tz())
            return None, bj.isoformat()
        utc_dt = dt.astimezone(timezone.utc)
        return utc_dt.isoformat(), utc_to_beijing_str(utc_dt)
    except Exception:
        now_bj = now_beijing_str()
        return None, now_bj
