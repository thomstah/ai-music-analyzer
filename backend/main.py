import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.songs import router
import services.billboard as billboard_service

logger = logging.getLogger(__name__)


async def _warm_billboard_cache():
    """Pre-warm the Billboard Hot 100 cache so the first home-page load is fast."""
    try:
        await asyncio.to_thread(billboard_service.get_hot_100, 10)
        logger.info("Billboard cache pre-warmed")
    except Exception as exc:
        logger.warning("Failed to pre-warm Billboard cache: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Run on startup, don't block boot
    asyncio.create_task(_warm_billboard_cache())
    yield


app = FastAPI(title="AI Music Analyzer", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
async def health():
    return {"status": "ok"}
