import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from .config import settings
from .config_manager import config_manager
from .csv_market_routes import router as csv_market_router
from .csv_snapshot_routes import router as csv_snapshot_router
from .csv_snapshot_service import (
    CSV_DATA_ROOT,
    SNAPSHOT_LOOKBACK_HOURS,
    SNAPSHOT_REFRESH_SECONDS,
    build_market_snapshot,
    save_market_snapshot,
)
from .dashboard import get_dashboard_html
from .market_bridge_routes import router as market_bridge_router
from .market_state_routes import router as market_state_router
from .market_watch_routes import router as market_watch_router
from .prediction_routes import router as prediction_router
from .structure_routes import router as structure_router
from .mt5_service import mt5_service
from .routes import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger(__name__)


async def background_snapshot_refresh():
    """Background task: rebuild CSV snapshot every SNAPSHOT_REFRESH_SECONDS."""
    while True:
        try:
            await asyncio.sleep(SNAPSHOT_REFRESH_SECONDS)
            snapshot = build_market_snapshot(data_root=CSV_DATA_ROOT, lookback_hours=SNAPSHOT_LOOKBACK_HOURS)
            success = save_market_snapshot(snapshot)
            if success:
                logger.info("Snapshot refreshed: %d symbols", len(snapshot.get("symbols", {})))
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.error("Snapshot refresh error: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    config_manager.reload()
    mt5_service.initialize()
    task = asyncio.create_task(background_snapshot_refresh())
    logger.info("Started, refresh interval: %ds", SNAPSHOT_REFRESH_SECONDS)
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    mt5_service.shutdown()
    logger.info("Shutdown complete")


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(market_bridge_router)
app.include_router(market_state_router)
app.include_router(csv_snapshot_router)
app.include_router(csv_market_router)
app.include_router(market_watch_router)
app.include_router(structure_router)
app.include_router(prediction_router)


@app.get("/visualization", response_class=HTMLResponse)
def visualization() -> HTMLResponse:
    from .visualization_page import get_visualization_page_html
    return HTMLResponse(content=get_visualization_page_html())


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard() -> HTMLResponse:
    return HTMLResponse(content=get_dashboard_html())
