from pydantic import BaseModel
from typing import List


class ModerationRequest(BaseModel):

    text: str

    stop_words: List[str] = []


class ModerationResponse(BaseModel):

    is_toxic: bool

    toxicity_score: float

    stop_word_detected: bool

    length_violation: bool

    blocked: bool