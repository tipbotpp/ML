import base64
from typing import Any

import httpx

from app.config import settings
from app.exceptions import ImageGenerationException, UnsupportedImageProviderException


class ImageGeneratorService:
    async def generate(
        self,
        prompt: str,
        provider: str = "kandinsky",
        style: str | None = None,
        negative_prompt: str | None = None,
        width: int | None = None,
        height: int | None = None,
    ) -> tuple[bytes, str, int, int]:
        normalized_provider = provider.lower()

        if normalized_provider == "kandinsky":
            return await self._generate_kandinsky(
                prompt=prompt,
                style=style,
                negative_prompt=negative_prompt,
                width=width,
                height=height,
            )

        raise UnsupportedImageProviderException(provider=provider)

    async def _generate_kandinsky(
        self,
        prompt: str,
        style: str | None = None,
        negative_prompt: str | None = None,
        width: int | None = None,
        height: int | None = None,
    ) -> tuple[bytes, str, int, int]:
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
            model_id = settings.KANDINSKY_MODEL_ID or await self._fetch_model_id(client)

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
            return image_bytes, actual_style, actual_width, actual_height

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
        attempts = max(1, int(settings.IMAGE_TIMEOUT_SEC // 2))

        for _ in range(attempts):
            response = await client.get(f"/key/api/v1/text2image/status/{uuid}")
            response.raise_for_status()
            payload = response.json()

            status = payload.get("status")
            if status == "DONE":
                return payload

            if status == "FAIL":
                raise ImageGenerationException(details={"reason": payload.get("errorDescription")})

            await self._sleep_poll_interval()

        raise ImageGenerationException(
            details={"reason": "Kandinsky generation timed out"}
        )

    async def _sleep_poll_interval(self) -> None:
        import asyncio

        await asyncio.sleep(2)

    def _dump_json(self, payload: dict[str, Any]) -> str:
        import json

        return json.dumps(payload, ensure_ascii=False)


image_generator = ImageGeneratorService()
