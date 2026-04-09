from pydantic import BaseModel
from typing import Optional


class TTSRequest(BaseModel):
    text: str
    donor_name: str
    amount: int
    voice: Optional[str] = None
    donation_id: int


class TTSResponse(BaseModel):
    audio_key: str
    duration_sec: float
    donation_id: int
