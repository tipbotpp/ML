from fastapi import APIRouter, Depends
from app.exceptions import (
    ToxicityException,
    StopWordException,
    TextTooLongException
)
from app.services.rubert import rubert
from app.schemas.moderation import ModerationRequest
from app.utils.stop_words import DEFAULT_STOP_WORDS
from app.config import settings
from app.dependencies import verify_api_key


router = APIRouter()


@router.post("/moderation/check")
async def moderation_check(
    request: ModerationRequest,
    _ = Depends(verify_api_key)
):

    text = request.text.lower()

    toxicity = rubert.predict(text)

    if toxicity["is_toxic"]:
        raise ToxicityException(
            toxicity["toxicity_score"]
        )

    for word in request.stop_words:

        if word in text:
            raise StopWordException(word)

    if len(text) > settings.MAX_TEXT_LENGTH:
        raise TextTooLongException()

    return {

        "blocked": False,
        "toxicity_score": toxicity["toxicity_score"]
    }