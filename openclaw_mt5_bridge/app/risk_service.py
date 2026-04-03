from .config_manager import config_manager
from .schemas import RiskCheckRequest, RiskCheckResponse


class RiskService:
    def check(self, payload: RiskCheckRequest) -> RiskCheckResponse:
        active = config_manager.get_active()
        symbol_cfg = active.get("symbols", {}).get(payload.symbol.upper())
        if symbol_cfg is None:
            return RiskCheckResponse(allow=False, reason="symbol not configured", checks={"symbol_configured": False})

        checks = {
            "volume_positive": payload.volume > 0,
            "symbol_enabled": bool(symbol_cfg.get("enabled", False)),
            "max_single_order": payload.volume <= float(symbol_cfg.get("max_single_order", 0)),
        }
        allow = all(checks.values())
        reason = "ok" if allow else "risk checks failed"
        return RiskCheckResponse(allow=allow, reason=reason, checks=checks)


risk_service = RiskService()
