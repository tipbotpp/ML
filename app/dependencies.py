from fastapi import Header, HTTPException, Request

from app.config import settings
from app.services.s3 import S3Client


async def verify_internal_secret(x_internal_secret: str = Header(...)):
    if x_internal_secret != settings.INTERNAL_SECRET:
        raise HTTPException(401, "Invalid secret")


async def get_s3(request: Request) -> S3Client:
    return request.app.state.s3
