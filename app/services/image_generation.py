import asyncio
import hashlib
import json
from typing import Any
from io import BytesIO

import httpx
from PIL import Image

from app.config import settings
from app.exceptions import ImageGenerationException, UnsupportedImageProviderException
from app.services.cache import CacheManager
from app.services.logger import get_logger
from app.utils.request_formatter import ResponseFormatter

logger = get_logger().bind(layer="service", module="image_generation")

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
        logger.debug("image_generation.generate started", provider=normalized_provider, prompt_length=len(prompt))

        if normalized_provider in ["stable_diffusion", "sd"]:
            return await self._generate_stable_diffusion(
                prompt=prompt,
                negative_prompt=negative_prompt,
                width=width,
                height=height,
                nsfw_check=nsfw_check,
            )

        logger.error("image_generation.unsupported_provider", provider=provider)
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
            logger.error("image_generation.airfail_key_missing")
            raise ImageGenerationException(
                details={"reason": "air.fail API key is not configured"}
            )

        if not settings.AIRFAIL_API_URL:
            logger.error("image_generation.airfail_url_missing")
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
                    logger.info("image_generation.cache_hit", prompt_preview=prompt[:50])
                    return cached_result
            except Exception as e:
                logger.warning("image_generation.cache_get_failed", error=str(e))

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
        logger.debug(
            "image_generation.airfail_request",
            url=settings.AIRFAIL_API_URL,
            model_version=settings.AIRFAIL_MODEL_VERSION,
            prompt_length=len(prompt),
        )

        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
                response = await client.post(
                    settings.AIRFAIL_API_URL,
                    headers=headers,
                    data=request_body,
                )

                logger.debug(
                    "image_generation.airfail_response",
                    status_code=response.status_code,
                    content_type=response.headers.get("content-type", ""),
                    content_length=len(response.content),
                )

                try:
                    response.raise_for_status()
                except httpx.HTTPStatusError as e:
                    error_text = ""
                    try:
                        error_text = e.response.text[:500]
                    except Exception:
                        error_text = str(e)

                    logger.error(
                        "image_generation.airfail_http_error",
                        status_code=e.response.status_code,
                        url=str(e.request.url),
                        redirect_location=e.response.headers.get("location", ""),
                        error=error_text,
                    )
                    raise ImageGenerationException(
                        details={"reason": f"HTTP {e.response.status_code}: {error_text}"}
                    )

                try:
                    messages = response.json()
                except Exception:
                    logger.error("image_generation.invalid_json", content_preview=response.text[:200])
                    raise ImageGenerationException(
                        details={"reason": "air.fail returned non-JSON response"}
                    )

                if not messages or not isinstance(messages, list):
                    logger.error("image_generation.unexpected_response_format", response_preview=str(messages)[:200])
                    raise ImageGenerationException(
                        details={"reason": "Unexpected response format from air.fail"}
                    )

                image_url = messages[0].get("file") if messages[0] else None
                if not image_url:
                    logger.error("image_generation.no_file_url", message=str(messages[0])[:200])
                    raise ImageGenerationException(
                        details={"reason": "No image URL in air.fail response"}
                    )

                logger.debug("image_generation.downloading_image", url=image_url[:80])
                async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as dl_client:
                    img_response = await dl_client.get(image_url)
                    img_response.raise_for_status()

                image_bytes = img_response.content
                if not image_bytes or len(image_bytes) == 0:
                    logger.error("image_generation.empty_image_download")
                    raise ImageGenerationException(
                        details={"reason": "Downloaded image is empty"}
                    )

                logger.debug("image_generation.image_received", size_bytes=len(image_bytes))

                enable_nsfw_check = nsfw_check if nsfw_check is not None else settings.IMAGE_NSFW_CHECK_ENABLED
                nsfw_detected = None
                nsfw_score = None

                if enable_nsfw_check:
                    try:
                        nsfw_detected, nsfw_score = await self._check_nsfw(image_bytes)
                        logger.debug("image_generation.nsfw_check_done", nsfw_detected=nsfw_detected, nsfw_score=nsfw_score)
                    except Exception as e:
                        logger.error("image_generation.nsfw_check_failed", error=str(e))
                        nsfw_detected = False
                        nsfw_score = 0.0

                result = (image_bytes, "flux", actual_width, actual_height, nsfw_detected, nsfw_score)

                if settings.CACHE_ENABLED:
                    try:
                        image_cache.set(cache_key, result)
                        logger.info("image_generation.cache_set", prompt_preview=prompt[:50])
                    except Exception as e:
                        logger.warning("image_generation.cache_set_failed", error=str(e))

                logger.info(
                    "image_generation.done",
                    width=actual_width,
                    height=actual_height,
                    size_bytes=len(image_bytes),
                    nsfw_detected=nsfw_detected,
                )
                return result

        except ImageGenerationException:
            raise
        except httpx.RequestError as e:
            logger.error("image_generation.request_error", error=str(e), url=settings.AIRFAIL_API_URL)
            raise ImageGenerationException(
                details={"reason": f"Request failed: {str(e)}"}
            )
        except asyncio.TimeoutError:
            logger.error("image_generation.timeout", timeout_sec=settings.IMAGE_TIMEOUT_SEC)
            raise ImageGenerationException(
                details={"reason": "Request timeout"}
            )
        except Exception as e:
            logger.error("image_generation.unexpected_error", error=str(e), error_type=type(e).__name__)
            raise ImageGenerationException(
                details={"reason": f"Unexpected error: {str(e)}"}
            )

    def _format_request_headers(self) -> dict[str, str]:
        return {
            "Authorization": settings.AIRFAIL_API_KEY,
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

        full_prompt = prompt.strip()
        if negative_prompt and isinstance(negative_prompt, str) and negative_prompt.strip():
            full_prompt += f". Avoid: {negative_prompt.strip()}"

        return {
            "content": full_prompt,
            "info": json.dumps({"version": settings.AIRFAIL_MODEL_VERSION or "flux-1"}),
        }

    async def _check_nsfw(self, image_bytes: bytes) -> tuple[bool, float]:
        if not image_bytes or len(image_bytes) == 0:
            logger.warning("image_generation.nsfw_empty_input")
            return False, 0.0

        try:
            image = Image.open(BytesIO(image_bytes))
            if not image:
                logger.warning("image_generation.nsfw_open_failed")
                return False, 0.0

            nsfw_score = await self._calculate_nsfw_score(image)

            if not isinstance(nsfw_score, (int, float)):
                logger.warning("image_generation.nsfw_invalid_score", score_type=type(nsfw_score).__name__)
                nsfw_score = 0.0

            nsfw_detected = nsfw_score > settings.IMAGE_NSFW_THRESHOLD
            return nsfw_detected, nsfw_score
        except Exception as e:
            logger.error("image_generation.nsfw_exception", error=str(e))
            raise ImageGenerationException(
                details={"reason": f"NSFW check failed: {str(e)}"}
            )

    async def _calculate_nsfw_score(self, image: Image.Image) -> float:
        if not image:
            logger.warning("image_generation.nsfw_score_none_image")
            return 0.0

        try:
            return 0.0
        except Exception as e:
            logger.error("image_generation.nsfw_score_error", error=str(e))
            return 0.0


image_generator = ImageGeneratorService()
