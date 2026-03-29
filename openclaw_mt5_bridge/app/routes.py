import logging

from fastapi import APIRouter, HTTPException

from .mt5_service import mt5_service
from .schemas import AccountResponse, HealthResponse, OrderRequest

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    return HealthResponse(status="ok", mt5_connected=mt5_service.is_connected())


@router.get("/account", response_model=AccountResponse)
def get_account() -> AccountResponse:
    if not mt5_service.is_connected():
        raise HTTPException(status_code=503, detail="MT5 connection unavailable")

    try:
        return AccountResponse(**mt5_service.get_account_info())
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/positions")
def get_positions() -> list[dict]:
    if not mt5_service.is_connected():
        raise HTTPException(status_code=503, detail="MT5 connection unavailable")

    try:
        return mt5_service.get_positions()
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/order")
def place_order(payload: OrderRequest) -> dict:
    logger.info(
        "Trade request received: symbol=%s side=%s volume=%s comment=%s reason_payload=%s",
        payload.symbol,
        payload.side,
        payload.volume,
        payload.comment,
        payload.reason_payload.model_dump(),
    )

    if not mt5_service.is_connected():
        raise HTTPException(status_code=503, detail="MT5 connection unavailable")

    try:
        order_result = mt5_service.send_market_order(
            symbol=payload.symbol,
            side=payload.side,
            volume=payload.volume,
            sl=payload.sl,
            tp=payload.tp,
            comment=payload.comment or "",
        )
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "status": "submitted",
        "order_result": order_result,
        "reason_payload": payload.reason_payload,
    }
