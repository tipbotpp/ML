from fastapi import APIRouter, Depends

from app.services.rubert import rubert
from app.services.logger import get_logger
from app.services.cache import CacheManager
from app.schemas.moderation import ModerationRequest, ModerationResponse
from app.dependencies import verify_internal_secret
from app.utils.stop_words import DEFAULT_STOP_WORDS
from app.utils.request_formatter import (
    RequestFormatter,
    ResponseFormatter,
    ErrorFormatter,
    ParameterValidator,
)
from app.config import settings

router = APIRouter()
logger = get_logger()

moderation_cache = CacheManager(
    default_ttl_seconds=settings.CACHE_MODERATION_TTL_SECONDS,
    max_entries=settings.CACHE_MAX_ENTRIES,
    max_memory_mb=settings.CACHE_MAX_MEMORY_MB * 0.3,
)


def _format_moderation_request(request: ModerationRequest) -> dict:
    return {
        "streamer_id": request.streamer_id,
        "text": request.text,
        "stopwords_count": len(request.stopwords),
    }


def _generate_moderation_cache_key(text: str, stopwords: frozenset[str]) -> str:
    stopwords_str = "|".join(sorted(stopwords))
    return moderation_cache.generate_key(text, stopwords_str)


@router.post("/moderation/check", response_model=ModerationResponse)
async def moderation_check(
    request: ModerationRequest,
    _ = Depends(verify_internal_secret)
):
    try:
        validation = ParameterValidator.validate_moderation_params(
            request.text,
            request.stopwords
        )
        logger.info("moderation.validation", validation=validation)
    except ValueError as e:
        logger.error("moderation.validation_error", error=str(e))
        error_response = ErrorFormatter.format_validation_error("moderation_request", str(e))
        return ModerationResponse(
            is_toxic=False,
            toxicity_score=0.0,
            stopword_found=None,
            verdict="error",
        )
    
    formatted_request = RequestFormatter.format_moderation_api_request(
        request.text,
        request.stopwords
    )
    logger.info("moderation.formatted_request", data=formatted_request)

    text = formatted_request["text"].lower()
    stopwords = formatted_request["stopwords"]
    
    if settings.CACHE_ENABLED:
        cache_key = moderation_cache.generate_key(text, "|".join(sorted(stopwords)))
        cached_result = moderation_cache.get(cache_key)
        if cached_result is not None:
            logger.info("moderation.cache_hit", streamer_id=request.streamer_id)
            return cached_result

    toxicity = rubert.predict(text)
    all_stopwords = list(set(stopwords) | set(DEFAULT_STOP_WORDS))

    if toxicity["is_toxic"]:
        result = ModerationResponse(
            is_toxic=True,
            toxicity_score=toxicity["toxicity_score"],
            stopword_found=None,
            verdict="rejected_toxicity",
        )
        if settings.CACHE_ENABLED:
            moderation_cache.set(cache_key, result)
        return result

    for word in stopwords:
        if word.lower() in text:
            result = ModerationResponse(
                is_toxic=False,
                toxicity_score=toxicity["toxicity_score"],
                stopword_found=word,
                verdict="rejected_stopword",
            )
            if settings.CACHE_ENABLED:
                moderation_cache.set(cache_key, result)
            return result

    result = ModerationResponse(
        is_toxic=False,
        toxicity_score=toxicity["toxicity_score"],
        stopword_found=None,
        verdict="ok",
    )
    
    if settings.CACHE_ENABLED:
        moderation_cache.set(cache_key, result)
    
    return result
    
    return result

