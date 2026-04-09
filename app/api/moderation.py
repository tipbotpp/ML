from fastapi import APIRouter, Depends

from app.services.rubert import rubert
from app.services.logger import get_logger
from app.schemas.moderation import ModerationRequest, ModerationResponse
from app.dependencies import verify_internal_secret

router = APIRouter()
logger = get_logger()


@router.post("/moderation/check", response_model=ModerationResponse)
async def moderation_check(
    request: ModerationRequest,
    _ = Depends(verify_internal_secret)
):
    logger.info("moderation_check", streamer_id=request.streamer_id)

    text = request.text.lower()
    toxicity = rubert.predict(text)

    if toxicity["is_toxic"]:
        return ModerationResponse(
            is_toxic=True,
            toxicity_score=toxicity["toxicity_score"],
            stopword_found=None,
            verdict="blocked",
        )

    for word in request.stopwords:
        if word.lower() in text:
            return ModerationResponse(
                is_toxic=False,
                toxicity_score=toxicity["toxicity_score"],
                stopword_found=word,
                verdict="blocked",
            )

    return ModerationResponse(
        is_toxic=False,
        toxicity_score=toxicity["toxicity_score"],
        stopword_found=None,
        verdict="allowed",
    )
