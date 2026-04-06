import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from .config import settings
from .config_manager import config_manager
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
from .structure_routes import router as structure_router
from .mt5_live_routes import router as mt5_live_router
from .mt5_live_service import mt5_live_service
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

            logger.info("Background: building market snapshot...")

            snapshot = build_market_snapshot(
                data_root=CSV_DATA_ROOT,
                lookback_hours=SNAPSHOT_LOOKBACK_HOURS,
            )

            success = save_market_snapshot(snapshot)

            if success:
                symbol_count = len(snapshot.get("symbols", {}))
                logger.info(
                    "Background: snapshot refreshed, %d symbols, folder=%s",
                    symbol_count,
                    snapshot.get("latest_folder")
                )
            else:
                logger.warning("Background: failed to save snapshot")

        except asyncio.CancelledError:
            logger.info("Background snapshot task cancelled")
            break
        except Exception as exc:
            logger.error("Background snapshot error: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    config_manager.reload()
    mt5_service.initialize()

    # Initialize MT5 Live Service
    if mt5_live_service.initialize():
        logger.info("MT5 Live Service initialized")
    else:
        logger.warning("MT5 Live Service not available (MT5 not running?)")

    # Start background CSV snapshot refresh task
    task = asyncio.create_task(background_snapshot_refresh())
    logger.info("Background CSV snapshot refresh task started (%d sec)", SNAPSHOT_REFRESH_SECONDS)

    yield

    # Shutdown
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    mt5_live_service.shutdown()
    mt5_service.shutdown()
    logger.info("Shutdown complete")


app = FastAPI(title=settings.app_name, lifespan=lifespan)

# Add CORS middleware for cross-origin requests
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
app.include_router(mt5_live_router)
app.include_router(market_watch_router)
app.include_router(structure_router)


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard() -> HTMLResponse:
    """Simple dashboard for human viewing."""
    return HTMLResponse(content=get_dashboard_html())
