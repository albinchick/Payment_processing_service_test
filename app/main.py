import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from app.api import router
from app.core.config import settings
from app.db import engine
from app.models import Base

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Convenient for local development; production deployments should run Alembic migrations.
    yield
    await engine.dispose()


app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)
app.include_router(router)


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
