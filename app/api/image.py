import uuid

from fastapi import APIRouter, Depends

from app.config import settings
from app.dependencies import get_s3, verify_internal_secret
from app.schemas.image import ImageGenerationRequest, ImageGenerationResponse
from app.services.image_generation import image_generator
from app.services.logger import get_logger
from app.services.s3 import S3Client

logger = get_logger().bind(module="image")

router = APIRouter()


@router.post("/image/generate", response_model=ImageGenerationResponse)
async def generate_image(
    request: ImageGenerationRequest,
    s3: S3Client = Depends(get_s3),
    _=Depends(verify_internal_secret),
):
    prompt = (
        f"Создай изображение для донат-алерта. "
        f"Донатер: {request.donor_name}. "
        f"Сумма: {request.amount}. "
        f"Сообщение: {request.text}"
    )

    image_bytes, provider_style, width, height, nsfw_detected, nsfw_score = await image_generator.generate(
        prompt=prompt,
        provider=request.provider,
        style=request.style,
        negative_prompt=request.negative_prompt,
        width=request.width,
        height=request.height,
        nsfw_check=request.nsfw_check,
    )

    key = f"images/{request.donation_id}/{uuid.uuid4()}.png"
    image_key = await s3.upload(
        bucket=settings.S3_BUCKET,
        key=key,
        data=image_bytes,
        content_type="image/png",
    )

    logger.info(
        "image.generate.success",
        donation_id=request.donation_id,
        provider=request.provider,
        image_key=image_key,
    )

    return ImageGenerationResponse(
        image_key=image_key,
        donation_id=request.donation_id,
        provider=request.provider,
        prompt=prompt,
        width=width,
        height=height,
        nsfw_detected=nsfw_detected,
        nsfw_score=nsfw_score,
    )
