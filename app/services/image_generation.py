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
        if not prompt or not isinstance(prompt, str):
            raise ImageGenerationException(
                details={"reason": "Prompt must be non-empty string"}
            )
        
        normalized_provider = provider.lower() if provider else "stable_diffusion"

        if normalized_provider in ["stable_diffusion", "sd"]:
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
        
        if not settings.AIRFAIL_API_URL:
            raise ImageGenerationException(
                details={"reason": "air.fail API URL is not configured"}
            )

        actual_width = width or settings.IMAGE_WIDTH
        actual_height = height or settings.IMAGE_HEIGHT
        
        if not isinstance(actual_width, int) or not isinstance(actual_height, int):
            raise ImageGenerationException(
                details={"reason": "Invalid width or height type"}
            )

        cache_key = self._generate_cache_key(prompt, negative_prompt, actual_width, actual_height)
        
        if settings.CACHE_ENABLED:
            try:
                cached_result = image_cache.get(cache_key)
                if cached_result is not None:
                    logger.info(f"Image cache hit: {prompt[:50]}...")
                    return cached_result
            except Exception as e:
                logger.warning(f"Cache retrieval failed: {str(e)}")

        request_body = self._format_request_body(
            prompt=prompt,
            negative_prompt=negative_prompt,
            width=actual_width,
            height=actual_height,
        )
        
        if not request_body:
            raise ImageGenerationException(
                details={"reason": "Failed to format request body"}
            )

        headers = self._format_request_headers()
        if not headers or "Authorization" not in headers:
            raise ImageGenerationException(
                details={"reason": "Invalid request headers"}
            )
        
        timeout = httpx.Timeout(settings.IMAGE_TIMEOUT_SEC)

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    settings.AIRFAIL_API_URL,
                    headers=headers,
                    json=request_body,
                )
                
                try:
                    response.raise_for_status()
                except httpx.HTTPStatusError as e:
                    error_text = ""
                    try:
                        error_text = e.response.text[:300]
                    except:
                        error_text = str(e)
                    
                    logger.error(
                        f"air.fail API HTTP error",
                        status_code=e.response.status_code,
                        error=error_text
                    )
                    raise ImageGenerationException(
                        details={"reason": f"HTTP {e.response.status_code}: {error_text}"}
                    )

                image_bytes = response.content
                if not image_bytes or len(image_bytes) == 0:
                    logger.error("air.fail API returned empty image")
                    raise ImageGenerationException(
                        details={"reason": "No image data returned from air.fail API"}
                    )

                enable_nsfw_check = nsfw_check if nsfw_check is not None else settings.IMAGE_NSFW_CHECK_ENABLED
                nsfw_detected = None
                nsfw_score = None

                if enable_nsfw_check:
                    try:
                        nsfw_detected, nsfw_score = await self._check_nsfw(image_bytes)
                    except Exception as e:
                        logger.error(f"NSFW check error: {str(e)}")
                        nsfw_detected = False
                        nsfw_score = 0.0

                result = (image_bytes, "flux", actual_width, actual_height, nsfw_detected, nsfw_score)
                
                if settings.CACHE_ENABLED:
                    try:
                        image_cache.set(cache_key, result)
                        logger.info(f"Image cached: {prompt[:50]}...")
                    except Exception as e:
                        logger.warning(f"Cache set failed: {str(e)}")
                
                return result

        except ImageGenerationException:
            raise
        except httpx.RequestError as e:
            logger.error(f"air.fail API request error: {str(e)}")
            raise ImageGenerationException(
                details={"reason": f"Request failed: {str(e)}"}
            )
        except asyncio.TimeoutError:
            logger.error("air.fail API request timeout")
            raise ImageGenerationException(
                details={"reason": "Request timeout"}
            )
        except Exception as e:
            logger.error(f"Unexpected error in image generation: {str(e)}", exc_info=True)
            raise ImageGenerationException(
                details={"reason": f"Unexpected error: {str(e)}"}
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
        if not prompt or not isinstance(prompt, str):
            raise ImageGenerationException(
                details={"reason": "Invalid prompt for request body"}
            )
        
        if not isinstance(width, int) or not isinstance(height, int):
            raise ImageGenerationException(
                details={"reason": "Invalid width or height type"}
            )
        
        body: dict[str, Any] = {
            "prompt": prompt.strip(),
            "width": width,
            "height": height,
            "num_images": settings.IMAGE_NUM_IMAGES or 1,
            "model": settings.AIRFAIL_MODEL_ID or "flux",
        }

        if negative_prompt and isinstance(negative_prompt, str) and negative_prompt.strip():
            body["negative_prompt"] = negative_prompt.strip()

        return body

    async def _check_nsfw(self, image_bytes: bytes) -> tuple[bool, float]:
        if not image_bytes or len(image_bytes) == 0:
            logger.warning("Empty image bytes provided to NSFW check")
            return False, 0.0
        
        try:
            image = Image.open(BytesIO(image_bytes))
            if not image:
                logger.warning("Failed to open image in NSFW check")
                return False, 0.0
            
            nsfw_score = await self._calculate_nsfw_score(image)
            
            if not isinstance(nsfw_score, (int, float)):
                logger.warning(f"Invalid NSFW score type: {type(nsfw_score)}")
                nsfw_score = 0.0
            
            nsfw_detected = nsfw_score > settings.IMAGE_NSFW_THRESHOLD
            return nsfw_detected, nsfw_score
        except Exception as e:
            logger.error(f"NSFW check failed with exception: {str(e)}", exc_info=True)
            raise ImageGenerationException(
                details={"reason": f"NSFW check failed: {str(e)}"}
            )

    async def _calculate_nsfw_score(self, image: Image.Image) -> float:
        if not image:
            logger.warning("None image provided to _calculate_nsfw_score")
            return 0.0
        
        try:
            # Placeholder implementation - returns 0.0 by default
            # In production, implement actual NSFW detection logic here
            return 0.0
        except Exception as e:
            logger.error(f"NSFW score calculation error: {str(e)}")
            return 0.0


image_generator = ImageGeneratorService()
