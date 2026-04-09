from pydantic import BaseModel
from typing import List, Optional


class ModerationRequest(BaseModel):
    text: str
    stopwords: List[str] = []
    streamer_id: int


class ModerationResponse(BaseModel):
    is_toxic: bool
    toxicity_score: float
    stopword_found: Optional[str]
    verdict: str  # "allowed" | "blocked"
