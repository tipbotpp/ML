from fastapi import HTTPException


class MLException(HTTPException):

    def __init__(
        self,
        code: str,
        message: str,
        details: dict = None,
        status_code: int = 400
    ):

        super().__init__(
            status_code=status_code,
            detail={
                "error": True,
                "code": code,
                "message": message,
                "details": details
            }
        )

class ToxicityException(MLException):

    def __init__(self, score: float):

        super().__init__(

            code="TOXIC_MESSAGE",

            message="Сообщение содержит токсичность",

            details={
                "toxicity_score": score
            },

            status_code=400
        )


class StopWordException(MLException):

    def __init__(self, word: str):

        super().__init__(

            code="STOP_WORD",

            message="Сообщение содержит запрещеное слово",

            details={
                "word": word
            },

            status_code=400
        )


class TextTooLongException(MLException):

    def __init__(self):

        super().__init__(

            code="TEXT_TOO_LONG",

            message="Сообщение слишком длинное",

            status_code=400
        )


class TTSGenerationException(MLException):

    def __init__(self):

        super().__init__(

            code="TTS_ERROR",

            message="TTS generation failed",

            status_code=500
        )