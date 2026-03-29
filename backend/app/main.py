from contextlib import asynccontextmanager

from fastapi import FastAPI
from loguru import logger

from app.api.routes import router
from app.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up — initializing database")
    await init_db()
    yield
    logger.info("Shutting down")


app = FastAPI(title="ProNexus Pipeline", lifespan=lifespan)
app.include_router(router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok"}
