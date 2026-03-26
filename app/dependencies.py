from fastapi import Header, HTTPException
from app.config import settings


async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != settings.API_KEY:
        raise HTTPException(401, "Invalid API key")