import io

import torch
import soundfile as sf

from app.config import settings


VALID_VOICES = {"aidar", "baya", "kseniya", "xenia", "eugene"}


class Silero:

    def __init__(self):
        self.model, _ = torch.hub.load(
            repo_or_dir="snakers4/silero-models",
            model="silero_tts",
            language="ru",
            speaker="v4_ru",
            trust_repo=True
        )
        self.sample_rate = settings.TTS_SAMPLE_RATE

    def generate(self, text: str, voice: str | None = None) -> tuple[bytes, float]:
        speaker = voice if voice in VALID_VOICES else settings.TTS_SPEAKER

        audio = self.model.apply_tts(
            text=text,
            speaker=speaker,
            sample_rate=self.sample_rate,
        )

        duration_sec = len(audio) / self.sample_rate

        buf = io.BytesIO()
        sf.write(buf, audio, self.sample_rate, format="WAV")
        buf.seek(0)

        return buf.read(), duration_sec


silero = Silero()
