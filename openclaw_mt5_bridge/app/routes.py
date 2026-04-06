import logging

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from .config_manager import config_manager
from .history_service import history_service
from .mt5_service import mt5_service
from .risk_engine import risk_engine
from .risk_service import risk_service
from .schemas import (
    AccountResponse,
    CloseAllPositionsRequest,
    ClosePositionRequest,
    ConfigUpdateRequest,
    HealthResponse,
    MultiHistoryRequest,
    MultiHistoryResponse,
    ModifyAllPositionsRequest,
    ModifyPositionRequest,
    OrderRequest,
    RiskCheckRequest,
    RiskCheckResponse,
    SignalResponse,
    SignalWriteRequest,
    SymbolListResponse,
)
from .signal_service import signal_service

logger = logging.getLogger(__name__)
router = APIRouter()

# Placeholder for live MT5 router (can be enabled later)
mt5_live_router = APIRouter(prefix="/mt5/live", tags=["mt5 live"])

@mt5_live_router.get("/latest")
def latest_price():
    return {"status": "ok", "message": "live price placeholder"}


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
        "Trade request: symbol=%s side=%s volume=%s comment=%s",
        payload.symbol, payload.side, payload.volume, payload.comment,
    )
    if not mt5_service.is_connected():
        raise HTTPException(status_code=503, detail="MT5 connection unavailable")
    try:
        account_info = mt5_service.get_account_info()
        positions = mt5_service.get_positions()
        risk_ok, risk_result = risk_engine.validate_order(
            symbol=payload.symbol, side=payload.side, volume=payload.volume,
            account_info=account_info, positions=positions,
        )
        if not risk_ok:
            return JSONResponse(status_code=400, content={"status": "rejected", "error": "risk_check_failed", "risk": risk_result})
        active_cfg = config_manager.get_active()
        symbol_cfg = active_cfg["symbols"].get(payload.symbol, {})
        if symbol_cfg.get("close_on_opposite", False):
            opposite_type = 1 if payload.side == "buy" else 0
            for pos in positions:
                if pos.get("symbol") == payload.symbol and pos.get("type") == opposite_type:
                    mt5_service.close_position(ticket=pos["ticket"], symbol=payload.symbol)
        order_result = mt5_service.send_market_order(
            symbol=payload.symbol, side=payload.side, volume=payload.volume,
            sl=payload.sl, tp=payload.tp, comment=payload.comment or "",
        )
        risk_engine.register_executed_trade(payload.symbol)
    except HTTPException:
        raise
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "submitted", "order_result": order_result}


@router.get("/symbols", response_model=SymbolListResponse)
def list_symbols() -> SymbolListResponse:
    return SymbolListResponse(symbols=history_service.list_symbols())


@router.get("/price/{symbol}")
def get_price(symbol: str):
    try:
        return history_service.get_latest_price(symbol)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed: {exc}") from exc


@router.get("/history/{symbol}")
def get_history(symbol: str, tf: str = Query("M1"), hours: int = Query(6, ge=1), limit: int | None = Query(None, ge=1)):
    try:
        return history_service.get_history(symbol=symbol, timeframe=tf, hours=hours, limit=limit)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed: {exc}") from exc


@router.post("/multi-history", response_model=MultiHistoryResponse)
def post_multi_history(payload: MultiHistoryRequest) -> MultiHistoryResponse:
    try:
        return history_service.get_multi_history(symbols=payload.symbols, timeframe=payload.timeframe, hours=payload.hours, limit=payload.limit)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed: {exc}") from exc


@router.post("/signal", response_model=SignalResponse)
def post_signal(payload: SignalWriteRequest) -> SignalResponse:
    signal_data = payload.signal.model_dump() if hasattr(payload.signal, "model_dump") else payload.signal
    try:
        return signal_service.write_signal(symbol=payload.symbol, signal=signal_data)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed: {exc}") from exc


@router.get("/signal/latest/{symbol}", response_model=SignalResponse)
def get_latest_signal(symbol: str) -> SignalResponse:
    try:
        return signal_service.get_latest_signal(symbol)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed: {exc}") from exc


@router.get("/signal/history/{symbol}")
def get_signal_history(symbol: str, limit: int = Query(20, ge=1, le=500)) -> list[dict]:
    try:
        return signal_service.get_signal_history(symbol, limit)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed: {exc}") from exc


@router.post("/risk/check", response_model=RiskCheckResponse)
def post_risk_check(payload: RiskCheckRequest) -> RiskCheckResponse:
    return risk_service.check(payload)


@router.get("/candles")
def get_candles(symbol: str = Query(...), timeframe: str = Query("M5"), bars: int = Query(72, ge=1, le=2000)) -> list[dict]:
    if not mt5_service.is_connected():
        raise HTTPException(status_code=503, detail="MT5 unavailable")
    try:
        return mt5_service.get_candles(symbol=symbol, timeframe=timeframe, bars=bars)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/config")
def get_active_config() -> dict:
    return config_manager.get_active()


@router.get("/config/draft")
def get_draft_config() -> dict:
    return config_manager.get_draft()


@router.post("/config/draft")
def update_draft_config(payload: ConfigUpdateRequest) -> dict:
    return config_manager.update_draft(payload.model_dump(exclude_none=True))


@router.post("/config/apply")
def apply_draft_config() -> dict:
    return config_manager.apply_draft()


@router.post("/config/reset")
def reset_draft_config() -> dict:
    return config_manager.reset_draft()


@router.post("/close_position")
def close_position(payload: ClosePositionRequest) -> dict:
    if not mt5_service.is_connected():
        raise HTTPException(status_code=503, detail="MT5 unavailable")
    try:
        result = mt5_service.close_position(ticket=payload.ticket, symbol=payload.symbol)
        return {"status": "ok", "result": result}
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/modify_position")
def modify_position(payload: ModifyPositionRequest) -> dict:
    if not mt5_service.is_connected():
        raise HTTPException(status_code=503, detail="MT5 unavailable")
    try:
        result = mt5_service.modify_position(ticket=payload.ticket, symbol=payload.symbol, sl=payload.sl, tp=payload.tp)
        return {"status": "ok", "result": result}
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/close_all_positions")
def close_all_positions(payload: CloseAllPositionsRequest) -> dict:
    if not mt5_service.is_connected():
        raise HTTPException(status_code=503, detail="MT5 unavailable")
    try:
        results = mt5_service.close_all_positions(symbol=payload.symbol)
        return {"status": "ok", "results": results}
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/modify_all_positions")
def modify_all_positions(payload: ModifyAllPositionsRequest) -> dict:
    if not mt5_service.is_connected():
        raise HTTPException(status_code=503, detail="MT5 unavailable")
    try:
        results = mt5_service.modify_all_positions(symbol=payload.symbol, sl=payload.sl, tp=payload.tp)
        return {"status": "ok", "results": results}
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
