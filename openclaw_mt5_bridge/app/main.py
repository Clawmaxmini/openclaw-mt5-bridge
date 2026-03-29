import logging

from fastapi import FastAPI

from .config import settings
from .mt5_service import mt5_service
from .routes import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

app = FastAPI(title=settings.app_name)
app.include_router(router)


@app.on_event("startup")
def on_startup() -> None:
    mt5_service.initialize()


@app.on_event("shutdown")
def on_shutdown() -> None:
    mt5_service.shutdown()
