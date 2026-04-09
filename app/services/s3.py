from types import TracebackType

import aiobotocore.session

from app.config import settings


class S3Client:

    def __init__(self) -> None:
        self._session = aiobotocore.session.get_session()
        self._client = None

    async def __aenter__(self) -> "S3Client":
        self._client = await self._session.create_client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            region_name="us-east-1",
        ).__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self._client:
            await self._client.__aexit__(exc_type, exc_val, exc_tb)

    async def upload(self, bucket: str, key: str, data: bytes, content_type: str) -> str:
        await self._client.put_object(
            Bucket=bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        return key
