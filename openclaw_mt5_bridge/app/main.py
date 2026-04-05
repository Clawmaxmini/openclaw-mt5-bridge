import logging

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from .config import settings
from .config_manager import config_manager
from .dashboard import get_dashboard_html
from .market_bridge_routes import router as market_bridge_router
from .market_state_routes import router as market_state_router
from .mt5_service import mt5_service
from .routes import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

app = FastAPI(title=settings.app_name)
app.include_router(router)
app.include_router(market_bridge_router)
app.include_router(market_state_router)


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard() -> HTMLResponse:
    """Simple dashboard for human viewing."""
    return HTMLResponse(content=get_dashboard_html())


@app.on_event("startup")
def on_startup() -> None:
    config_manager.reload()
    mt5_service.initialize()


@app.on_event("shutdown")
def on_shutdown() -> None:
    mt5_service.shutdown()
