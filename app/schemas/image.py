from typing import Literal, Optional

from pydantic import BaseModel, Field


class ImageGenerationRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=300)
    donation_id: int
    donor_name: str
    amount: int
    style: Optional[str] = None
    negative_prompt: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    provider: Literal["kandinsky", "sd"] = "kandinsky"


class ImageGenerationResponse(BaseModel):
    image_key: str
    donation_id: int
    provider: str
    prompt: str
    width: int
    height: int
