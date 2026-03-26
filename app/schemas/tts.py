from pydantic import BaseModel


class TTSRequest(BaseModel):
    text: str


class TTSResponse(BaseModel):
    file: str
    latency: float