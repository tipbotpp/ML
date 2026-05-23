import uuid
import hashlib

from fastapi import APIRouter, Depends

from app.exceptions import TTSGenerationException
from app.schemas.tts import TTSRequest, TTSResponse
from app.services.silero import silero
from app.services.s3 import S3Client
from app.services.cache import CacheManager
from app.dependencies import verify_internal_secret, get_s3
from app.utils.request_formatter import (
    RequestFormatter,
    ResponseFormatter,
    ErrorFormatter,
    ParameterValidator,
)
from app.config import settings
from app.services.logger import get_logger

logger = get_logger().bind(module="tts")

router = APIRouter()

tts_cache = CacheManager(
    default_ttl_seconds=settings.CACHE_TTS_TTL_SECONDS,
    max_entries=settings.CACHE_MAX_ENTRIES,
    max_memory_mb=settings.CACHE_MAX_MEMORY_MB * 0.5,
)


def _format_tts_request(request: TTSRequest) -> dict:
    return {
        "donation_id": request.donation_id,
        "donor_name": request.donor_name,
        "amount": request.amount,
        "voice": request.voice,
    }


def _build_tts_prompt(request: TTSRequest) -> str:
    return f"{request.donor_name} задонатил {request.amount} монет. {request.text}"


def _generate_tts_cache_key(text: str, voice: str) -> str:
    cache_data = f"{text}:{voice}"
    return hashlib.sha256(cache_data.encode()).hexdigest()


@router.post("/tts/synthesize", response_model=TTSResponse)
async def synthesize(
    request: TTSRequest,
    s3: S3Client = Depends(get_s3),
    _ = Depends(verify_internal_secret),
):
    try:
        try:
            validation = ParameterValidator.validate_tts_params(
                request.text,
                request.voice,
                settings.TTS_SAMPLE_RATE
            )
            logger.info("tts.validation", validation=validation)
        except ValueError as e:
            logger.error("tts.validation_error", error=str(e))
            raise TTSGenerationException(details={"reason": str(e)})

        text = _build_tts_prompt(request)
        formatted_request = RequestFormatter.format_tts_api_request(
            text,
            request.voice,
            settings.TTS_SAMPLE_RATE
        )
        logger.info("tts.formatted_request", data=formatted_request)

        sanitized_text = formatted_request["text"]
        voice = formatted_request["voice"]

        if settings.CACHE_ENABLED:
            cache_key = tts_cache.generate_key(sanitized_text, voice)
            cached_result = tts_cache.get(cache_key)
            if cached_result is not None:
                logger.info("tts.cache_hit", donation_id=request.donation_id)
                cached_audio_bytes, cached_duration = cached_result
                
                key = f"tts/{request.donation_id}/{uuid.uuid4()}.wav"
                audio_key = await s3.upload(
                    bucket=settings.S3_BUCKET_AUDIO,
                    key=key,
                    data=cached_audio_bytes,
                    content_type="audio/wav",
                )
                
                return TTSResponse(
                    audio_key=audio_key,
                    duration_sec=cached_duration,
                    donation_id=request.donation_id,
                )

        audio_bytes, duration_sec = silero.generate(sanitized_text, voice=voice)
        
        response_info = ResponseFormatter.format_tts_response(audio_bytes, duration_sec)
        logger.info("tts.generation_complete", response_info=response_info)

        if settings.CACHE_ENABLED:
            tts_cache.set(cache_key, (audio_bytes, duration_sec))
            logger.info("tts.cache_set", donation_id=request.donation_id)

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
        import traceback
        logger.error("tts.synthesize.failed", error=traceback.format_exc())
        raise TTSGenerationException()

