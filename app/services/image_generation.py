import asyncio
import hashlib
import json
import logging
from typing import Any
from io import BytesIO

import httpx
from PIL import Image

from app.config import settings
from app.exceptions import ImageGenerationException, UnsupportedImageProviderException
from app.services.cache import CacheManager
from app.utils.request_formatter import ResponseFormatter, ErrorFormatter

logger = logging.getLogger(__name__)

image_cache = CacheManager(
    default_ttl_seconds=settings.CACHE_IMAGE_TTL_SECONDS,
    max_entries=settings.CACHE_MAX_ENTRIES,
    max_memory_mb=settings.CACHE_MAX_MEMORY_MB * 0.2,
)


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

    def _generate_cache_key(
        self,
        prompt: str,
        negative_prompt: str | None,
        width: int,
        height: int,
    ) -> str:
        cache_data = f"{prompt}:{negative_prompt}:{width}:{height}"
        return image_cache.generate_key(cache_data)

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

        cache_key = self._generate_cache_key(prompt, negative_prompt, actual_width, actual_height)
        
        if settings.CACHE_ENABLED:
            cached_result = image_cache.get(cache_key)
            if cached_result is not None:
                logger.info(f"Image cache hit: {prompt[:50]}...")
                return cached_result

        request_body = self._format_request_body(
            prompt=prompt,
            negative_prompt=negative_prompt,
            width=actual_width,
            height=actual_height,
        )

        headers = self._format_request_headers()
        timeout = httpx.Timeout(settings.IMAGE_TIMEOUT_SEC)

        try:
            async with httpx.AsyncClient(
                timeout=timeout,
            ) as client:
                response = await client.post(
                    settings.AIRFAIL_API_URL,
                    headers=headers,
                    json=request_body,
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

                result = (image_bytes, "flux", actual_width, actual_height, nsfw_detected, nsfw_score)
                
                if settings.CACHE_ENABLED:
                    image_cache.set(cache_key, result)
                    logger.info(f"Image cached: {prompt[:50]}...")
                
                return result

        except httpx.HTTPError as e:
            raise ImageGenerationException(
                details={"reason": f"air.fail API error: {str(e)}"}
            )

    def _format_request_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {settings.AIRFAIL_API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "TipBot-ML/1.0",
        }

    def _format_request_body(
        self,
        prompt: str,
        negative_prompt: str | None,
        width: int,
        height: int,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "prompt": prompt,
            "width": width,
            "height": height,
            "num_images": settings.IMAGE_NUM_IMAGES,
            "model": settings.AIRFAIL_MODEL_ID,
        }

        if negative_prompt:
            body["negative_prompt"] = negative_prompt

        return body

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
