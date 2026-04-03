from typing import Any, Literal, Optional
from typing import Literal, Optional

from pydantic import BaseModel, Field


class ReasonPayload(BaseModel):
    agent_id: str
    strategy_type: str
    signal_source: str
    confidence: float = Field(ge=0, le=1)
    reason_text: str


class OrderRequest(BaseModel):
    symbol: str
    side: Literal["buy", "sell"]
    volume: float = Field(gt=0)
    sl: float = 0
    tp: float = 0
    comment: Optional[str] = ""
    reason_payload: Optional[ReasonPayload] = None
    reason_payload: ReasonPayload


class HealthResponse(BaseModel):
    status: str
    mt5_connected: bool


class AccountResponse(BaseModel):
    login: int
    balance: float
    equity: float
    margin: float
    margin_free: float


class SymbolListResponse(BaseModel):
    symbols: list[str]


class PriceSnapshot(BaseModel):
    symbol: str
    bid: float
    ask: float
    last: float | None = None
    spread: float | int
    timestamp_utc: str | None = None
    timestamp_beijing: str


class HistoryBar(BaseModel):
    symbol: str
    timeframe: str
    time_utc: str | None = None
    time_beijing: str
    open: float
    high: float
    low: float
    close: float
    volume: float | int | None = None
    tick_volume: float | int | None = None
    spread: float | int | None = None


class HistoryResponse(BaseModel):
    symbol: str
    timeframe: str
    hours: int
    count: int
    bars: list[HistoryBar]


class MultiHistoryRequest(BaseModel):
    symbols: list[str]
    timeframe: str = "M1"
    hours: int = 6
    limit: int | None = None


class MultiHistoryResponse(BaseModel):
    timeframe: str
    hours: int
    data: dict[str, list[HistoryBar]]


class SignalPayload(BaseModel):
    symbol: str
    side: Literal["buy", "sell", "flat"] | None = None
    volume: float | None = None
    sl: float | None = None
    tp: float | None = None
    comment: str | None = None
    reason_payload: dict[str, Any] = Field(default_factory=dict)
    decision_time_beijing: str | None = None


class SignalWriteRequest(BaseModel):
    symbol: str
    signal: SignalPayload | dict[str, Any]


class SignalResponse(BaseModel):
    symbol: str
    signal: dict[str, Any]
    updated_at_beijing: str


class RiskCheckRequest(BaseModel):
    symbol: str
    side: Literal["buy", "sell"]
    volume: float
    confidence: float | None = None
    strategy_type: str | None = None


class RiskCheckResponse(BaseModel):
    allow: bool
    reason: str
    checks: dict[str, bool] | None = None


class StandardMessageResponse(BaseModel):
    message: str


class ConfigUpdateRequest(BaseModel):
    symbols: Optional[dict[str, dict[str, Any]]] = None
    risk: Optional[dict[str, Any]] = None
    market_structure: Optional[dict[str, Any]] = None


class CandleResponse(BaseModel):
    time: int
    open: float
    high: float
    low: float
    close: float
    tick_volume: int


class ClosePositionRequest(BaseModel):
    ticket: int
    volume: float | None = None
    symbol: Optional[str] = None


class ModifyPositionRequest(BaseModel):
    ticket: int
    symbol: Optional[str] = None
    sl: float = 0
    tp: float = 0


class CloseAllPositionsRequest(BaseModel):
    symbol: Optional[str] = None


class ModifyAllPositionsRequest(BaseModel):
    symbol: Optional[str] = None
    sl: float = 0
    tp: float = 0
