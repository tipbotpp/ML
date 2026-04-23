import asyncio
import json
import logging
from typing import Any
from io import BytesIO

import httpx
from PIL import Image

from app.config import settings
from app.exceptions import ImageGenerationException, UnsupportedImageProviderException

logger = logging.getLogger(__name__)


class ImageGeneratorService:
    def __init__(self):
        self._http_client: httpx.AsyncClient | None = None

    async def generate(
        self,
        prompt: str,
        provider: str = "stable_diffusion",
        style: str | None = None,
        negative_prompt: str | None = None,
        width: int | None = None,
        height: int | None = None,
        nsfw_check: bool | None = None,
    ) -> tuple[bytes, str, int, int, bool | None, float | None]:
        normalized_provider = provider.lower()

        if normalized_provider == "stable_diffusion":
            return await self._generate_stable_diffusion(
                prompt=prompt,
                negative_prompt=negative_prompt,
                width=width,
                height=height,
                nsfw_check=nsfw_check,
            )

        raise UnsupportedImageProviderException(provider=provider)

    async def _generate_stable_diffusion(
        self,
        prompt: str,
        negative_prompt: str | None = None,
        width: int | None = None,
        height: int | None = None,
        nsfw_check: bool | None = None,
    ) -> tuple[bytes, str, int, int, bool | None, float | None]:
        if not settings.AIRFAIL_API_KEY:
            raise ImageGenerationException(
                details={"reason": "air.fail API key is not configured"}
            )

        actual_width = width or settings.IMAGE_WIDTH
        actual_height = height or settings.IMAGE_HEIGHT

        headers = {
            "Authorization": f"Bearer {settings.AIRFAIL_API_KEY}",
        }

        timeout = httpx.Timeout(settings.IMAGE_TIMEOUT_SEC)

        body = {
            "prompt": prompt,
            "width": actual_width,
            "height": actual_height,
        }

        if negative_prompt:
            body["negative_prompt"] = negative_prompt

        try:
            async with httpx.AsyncClient(
                timeout=timeout,
            ) as client:
                response = await client.post(
                    settings.AIRFAIL_API_URL,
                    headers=headers,
                    json=body,
                )
                response.raise_for_status()

                image_bytes = response.content
                if not image_bytes:
                    raise ImageGenerationException(
                        details={"reason": "No image data returned from air.fail API"}
                    )

                enable_nsfw_check = nsfw_check if nsfw_check is not None else settings.IMAGE_NSFW_CHECK_ENABLED
                nsfw_detected = None
                nsfw_score = None

                if enable_nsfw_check:
                    nsfw_detected, nsfw_score = await self._check_nsfw(image_bytes)

                return image_bytes, "flux", actual_width, actual_height, nsfw_detected, nsfw_score

        except httpx.HTTPError as e:
            raise ImageGenerationException(
                details={"reason": f"air.fail API error: {str(e)}"}
            )

    async def _check_nsfw(self, image_bytes: bytes) -> tuple[bool, float]:
        try:
            image = Image.open(BytesIO(image_bytes))
            nsfw_score = await self._calculate_nsfw_score(image)
            nsfw_detected = nsfw_score > settings.IMAGE_NSFW_THRESHOLD
            return nsfw_detected, nsfw_score
        except Exception as e:
            logger.error(f"NSFW check failed: {str(e)}")
            return False, 0.0

    async def _calculate_nsfw_score(self, image: Image.Image) -> float:
        return 0.0


image_generator = ImageGeneratorService()
