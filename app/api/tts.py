import uuid

from fastapi import APIRouter, Depends

from app.exceptions import TTSGenerationException
from app.schemas.tts import TTSRequest, TTSResponse
from app.services.silero import silero
from app.services.s3 import S3Client
from app.dependencies import verify_internal_secret, get_s3
from app.config import settings

from app.services.logger import get_logger

logger = get_logger().bind(module="tts")

router = APIRouter()


@router.post("/tts/synthesize", response_model=TTSResponse)
async def synthesize(
    request: TTSRequest,
    s3: S3Client = Depends(get_s3),
    _ = Depends(verify_internal_secret),
):
    try:
        text = f"{request.donor_name} задонатил {request.amount} монет. {request.text}"

        audio_bytes, duration_sec = silero.generate(text, voice=request.voice)

        key = f"tts/{request.donation_id}/{uuid.uuid4()}.wav"
        audio_key = await s3.upload(
            bucket=settings.S3_BUCKET_AUDIO,
            key=key,
            data=audio_bytes,
            content_type="audio/wav",
        )

        return TTSResponse(
            audio_key=audio_key,
            duration_sec=duration_sec,
            donation_id=request.donation_id,
        )

    except Exception as e:
        logger.error("tts.synthesize failed", exc_info=True)
        raise TTSGenerationException()
