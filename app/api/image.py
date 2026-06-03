import uuid

from fastapi import APIRouter, Depends

from app.config import settings
from app.dependencies import get_s3, verify_internal_secret
from app.exceptions import ImageGenerationException
from app.schemas.image import ImageGenerationRequest, ImageGenerationResponse
from app.services.image_generation import image_generator
from app.services.logger import get_logger
from app.services.s3 import S3Client
from app.utils.request_formatter import (
    RequestFormatter,
    ResponseFormatter,
    ErrorFormatter,
    ParameterValidator,
)

logger = get_logger().bind(module="image")

router = APIRouter()


def _format_image_request(request: ImageGenerationRequest) -> dict:
    return {
        "donation_id": request.donation_id,
        "provider": request.provider,
        "donor_name": request.donor_name,
        "amount": request.amount,
        "width": request.width,
        "height": request.height,
        "nsfw_check": request.nsfw_check,
    }


def _build_generation_prompt(request: ImageGenerationRequest) -> str:
    return (
        f"Создай изображение для донат-алерта. "
        f"Донатер: {request.donor_name}. "
        f"Сумма: {request.amount}. "
        f"Сообщение: {request.text}"
    )


@router.post("/image/generate", response_model=ImageGenerationResponse)
async def generate_image(
    request: ImageGenerationRequest,
    s3: S3Client = Depends(get_s3),
    _=Depends(verify_internal_secret),
):
    try:
        validation = ParameterValidator.validate_image_params(
            request.text,
            request.negative_prompt or "",
            request.width,
            request.height
        )
        logger.info("image.validation", validation=validation)
    except ValueError as e:
        logger.error("image.validation_error", error=str(e))
        error_response = ErrorFormatter.format_validation_error("image_request", str(e))
        raise ImageGenerationException(details={"reason": str(e)})

    prompt = _build_generation_prompt(request)
    formatted_request = RequestFormatter.format_image_api_request(
        prompt,
        request.negative_prompt or "",
        request.width,
        request.height
    )
    logger.info("image.formatted_request", data=formatted_request)

    image_bytes, provider, width, height, nsfw_detected, nsfw_score = await image_generator.generate(
        prompt=formatted_request["prompt"],
        provider=request.provider,
        negative_prompt=formatted_request["negative_prompt"],
        width=formatted_request["width"],
        height=formatted_request["height"],
        nsfw_check=request.nsfw_check,
    )
    
    response_info = ResponseFormatter.format_image_response(
        image_bytes,
        width,
        height,
        nsfw_detected,
        nsfw_score
    )
    logger.info("image.generation_complete", response_info=response_info)

    key = f"images/{request.donation_id}/{uuid.uuid4()}.png"
    image_key = await s3.upload(
        bucket=settings.S3_BUCKET,
        key=key,
        data=image_bytes,
        content_type="image/png",
    )

    return ImageGenerationResponse(
        image_key=image_key,
        donation_id=request.donation_id,
        provider=provider,
        prompt=formatted_request["prompt"],
        width=width,
        height=height,
        nsfw_detected=nsfw_detected,
        nsfw_score=nsfw_score,
    )

