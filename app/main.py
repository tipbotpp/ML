from fastapi import FastAPI
from app.api.tts import router as tts
from app.api.moderation import router as moderation
from fastapi.responses import JSONResponse
from fastapi.requests import Request


app = FastAPI()

app.include_router(tts)

app.include_router(moderation)


@app.get("/health")

async def health():

    return {"status": "ok"}


@app.exception_handler(Exception)
async def global_exception_handler(
    request: Request,
    exc: Exception
):

    return JSONResponse(

        status_code=500,

        content={

            "error": True,

            "code": "INTERNAL_ERROR",

            "message": "Internal server error"
        }
    )