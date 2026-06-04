import traceback
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.requests import Request
from fastapi.responses import JSONResponse

from app.api.tts import router as tts
from app.api.moderation import router as moderation
from app.api.image import router as image
from app.api.admin import router as admin
from app.middlewares.logging import HTTPLoggingMiddleware
from app.services.logger import get_logger
from app.services.s3 import S3Client
from app.config import settings

logger = get_logger()

_cleanup_task: asyncio.Task = None


async def _periodic_cache_cleanup():
    while True:
        try:
            await asyncio.sleep(settings.CACHE_CLEANUP_INTERVAL_SECONDS)
            from app.api.moderation import moderation_cache
            from app.api.tts import tts_cache
            from app.services.image_generation import image_cache
            
            removed = (
                moderation_cache.cleanup_expired()
                + tts_cache.cleanup_expired()
                + image_cache.cleanup_expired()
            )
            if removed > 0:
                logger.info("cache.periodic_cleanup", expired_removed=removed)
        except Exception as e:
            logger.error("cache.cleanup_error", error=str(e))


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _cleanup_task
    
    s3 = S3Client()
    await s3.__aenter__()
    app.state.s3 = s3
    
    if settings.CACHE_ENABLED:
        _cleanup_task = asyncio.create_task(_periodic_cache_cleanup())
    
    try:
        yield
    finally:
        if _cleanup_task:
            _cleanup_task.cancel()
            try:
                await _cleanup_task
            except asyncio.CancelledError:
                pass
        
        await s3.__aexit__(None, None, None)


app = FastAPI(lifespan=lifespan)

app.add_middleware(HTTPLoggingMiddleware)

app.include_router(tts)
app.include_router(moderation)
app.include_router(image)
app.include_router(admin)


@app.get("/health")
async def health():
    return {"status": "ok"}