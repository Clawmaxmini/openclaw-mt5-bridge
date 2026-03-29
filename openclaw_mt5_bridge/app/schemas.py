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
