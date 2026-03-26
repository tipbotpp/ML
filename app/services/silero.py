import torch
import soundfile as sf
import uuid


class Silero:

    def __init__(self):
        self.model, _ = torch.hub.load(
            repo_or_dir="snakers4/silero-models",
            model="silero_tts",
            language="ru",
            speaker="v4_ru",
            trust_repo=True
        )

        self.sample_rate = 48000

    def generate(self, text: str):

        audio = self.model.apply_tts(
            text=text,
            speaker="baya",
            sample_rate=self.sample_rate
        )

        file = f"{uuid.uuid4()}.wav"

        sf.write(file, audio, self.sample_rate)

        return file


silero = Silero()