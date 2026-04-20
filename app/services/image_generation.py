import base64
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
        self._model_id_cache: int | None = None
        self._model_id_lock = asyncio.Lock()
        self._http_client: httpx.AsyncClient | None = None

    async def generate(
        self,
        prompt: str,
        provider: str = "kandinsky",
        style: str | None = None,
        negative_prompt: str | None = None,
        width: int | None = None,
        height: int | None = None,
        nsfw_check: bool | None = None,
    ) -> tuple[bytes, str, int, int, bool | None, float | None]:
        normalized_provider = provider.lower()

        if normalized_provider == "kandinsky":
            return await self._generate_kandinsky(
                prompt=prompt,
                style=style,
                negative_prompt=negative_prompt,
                width=width,
                height=height,
                nsfw_check=nsfw_check,
            )

        raise UnsupportedImageProviderException(provider=provider)

    async def _generate_kandinsky(
        self,
        prompt: str,
        style: str | None = None,
        negative_prompt: str | None = None,
        width: int | None = None,
        height: int | None = None,
        nsfw_check: bool | None = None,
    ) -> tuple[bytes, str, int, int, bool | None, float | None]:
        if not settings.KANDINSKY_API_KEY or not settings.KANDINSKY_SECRET_KEY:
            raise ImageGenerationException(
                details={"reason": "Kandinsky credentials are not configured"}
            )

        actual_width = width or settings.IMAGE_WIDTH
        actual_height = height or settings.IMAGE_HEIGHT
        actual_style = style or settings.IMAGE_DEFAULT_STYLE

        headers = {
            "X-Key": f"Key {settings.KANDINSKY_API_KEY}",
            "X-Secret": f"Secret {settings.KANDINSKY_SECRET_KEY}",
        }

        timeout = httpx.Timeout(settings.IMAGE_TIMEOUT_SEC)

        async with httpx.AsyncClient(
            base_url=settings.KANDINSKY_API_URL,
            headers=headers,
            timeout=timeout,
        ) as client:
            # Get model_id with caching and locking to prevent race conditions
            model_id = settings.KANDINSKY_MODEL_ID or await self._get_cached_model_id(client)

            params: dict[str, Any] = {
                "type": "GENERATE",
                "numImages": settings.IMAGE_NUM_IMAGES,
                "width": actual_width,
                "height": actual_height,
                "generateParams": {
                    "query": prompt,
                },
                "style": actual_style,
            }

            if negative_prompt:
                params["negativePromptDecoder"] = negative_prompt

            response = await client.post(
                "/key/api/v1/text2image/run",
                data={
                    "model_id": str(model_id),
                    "params": self._dump_json(params),
                },
            )
            response.raise_for_status()

            uuid = response.json().get("uuid")
            if not uuid:
                raise ImageGenerationException(
                    details={"reason": "Kandinsky task uuid was not returned"}
                )

            status_payload = await self._poll_generation(client, uuid)
            images = status_payload.get("images") or []
            if not images:
                raise ImageGenerationException(
                    details={"reason": "Kandinsky returned empty images list"}
                )

            image_bytes = base64.b64decode(images[0])
            
            # Determine if NSFW check is enabled
            enable_nsfw_check = nsfw_check if nsfw_check is not None else settings.IMAGE_NSFW_CHECK_ENABLED
            nsfw_detected = None
            nsfw_score = None
            
            # Run NSFW check in background (non-blocking) or parallel
            if enable_nsfw_check:
                nsfw_detected, nsfw_score = await self._check_nsfw(image_bytes)
            
            return image_bytes, actual_style, actual_width, actual_height, nsfw_detected, nsfw_score

    async def _get_cached_model_id(self, client: httpx.AsyncClient) -> int:
        if self._model_id_cache is not None:
            return self._model_id_cache
        
        async with self._model_id_lock:
            if self._model_id_cache is not None:
                return self._model_id_cache
            
            model_id = await self._fetch_model_id(client)
            self._model_id_cache = model_id
            return model_id

    async def _fetch_model_id(self, client: httpx.AsyncClient) -> int:
        response = await client.get("/key/api/v1/models")
        response.raise_for_status()

        models = response.json()
        if not models:
            raise ImageGenerationException(
                details={"reason": "No Kandinsky models available"}
            )

        model_id = models[0].get("id")
        if model_id is None:
            raise ImageGenerationException(
                details={"reason": "Kandinsky model id was not returned"}
            )

        return int(model_id)

    async def _poll_generation(
        self,
        client: httpx.AsyncClient,
        uuid: str,
    ) -> dict[str, Any]:
        attempts = max(1, int(settings.IMAGE_TIMEOUT_SEC // 1.5))
        poll_interval = 1.0
        max_poll_interval = 3.0

        for attempt in range(attempts):
            response = await client.get(f"/key/api/v1/text2image/status/{uuid}")
            response.raise_for_status()
            payload = response.json()

            status = payload.get("status")
            if status == "DONE":
                logger.info(f"Image generation completed after {attempt + 1} polling attempts")
                return payload

            if status == "FAIL":
                raise ImageGenerationException(details={"reason": payload.get("errorDescription")})

            if attempt < 3:
                await asyncio.sleep(poll_interval)
            else:
                await asyncio.sleep(min(poll_interval * 1.2, max_poll_interval))
                poll_interval = min(poll_interval * 1.2, max_poll_interval)

        raise ImageGenerationException(
            details={"reason": "Kandinsky generation timed out"}
        )

    def _dump_json(self, payload: dict[str, Any]) -> str:
        return json.dumps(payload, ensure_ascii=False)

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
