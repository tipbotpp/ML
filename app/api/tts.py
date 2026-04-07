import time

from fastapi import APIRouter, Depends
from app.exceptions import TTSGenerationException
from app.schemas.tts import TTSRequest
from app.services.silero import silero
from app.dependencies import verify_api_key


router = APIRouter()


@router.post("/generate/audio")
async def generate(
    request: TTSRequest,
    _ = Depends(verify_api_key)
):

    try:

        start = time.time()

        file = silero.generate(request.text)

        latency = time.time() - start

        return {
            "file": file,
            "latency": latency
        }

    except Exception:

        raise TTSGenerationException()