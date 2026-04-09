import torch

from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification
)

from app.config import settings


class RuBERTModeration:

    def __init__(self):

        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        self.tokenizer = AutoTokenizer.from_pretrained(
            "cointegrated/rubert-tiny-toxicity"
        )

        self.model = AutoModelForSequenceClassification.from_pretrained(
            "cointegrated/rubert-tiny-toxicity"
        )

        self.model.to(self.device)

        self.model.eval()

        self.warmup()

    def warmup(self):

        self.predict("test")

    def predict(self, text: str):

        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            padding=True,
            max_length=512
        )

        inputs = {
            key: value.to(self.device)
            for key, value in inputs.items()
        }

        with torch.no_grad():

            outputs = self.model(**inputs)

        probs = torch.softmax(
            outputs.logits,
            dim=1
        )

        toxicity_score = probs[0][1].item()

        is_toxic = toxicity_score > settings.TOXIC_THRESHOLD

        return {
            "toxicity_score": toxicity_score,
            "is_toxic": is_toxic
        }


rubert = RuBERTModeration()