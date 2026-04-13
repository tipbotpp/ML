import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.requests import Request
from fastapi.responses import JSONResponse

from app.api.tts import router as tts
from app.api.moderation import router as moderation
from app.api.image import router as image
from app.middlewares.logging import HTTPLoggingMiddleware
from app.services.logger import get_logger
from app.services.s3 import S3Client

logger = get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with S3Client() as s3:
        app.state.s3 = s3
        yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(HTTPLoggingMiddleware)

app.include_router(tts)
app.include_router(moderation)
app.include_router(image)


@app.get("/health")
async def health():
    return {"status": "ok"}


# @app.exception_handler(Exception)
# async def global_exception_handler(request: Request, exc: Exception):
#     logger.error("Unhandled exception", error=str(exc), traceback=traceback.format_exc())
#     return JSONResponse(
#         status_code=500,
#         content={
#             "error": True,
#             "code": "INTERNAL_ERROR",
#             "message": "Internal server error",
#         },
#     )
