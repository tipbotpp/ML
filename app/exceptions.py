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


class TTSGenerationException(MLException):

    def __init__(self):

        super().__init__(
            code="TTS_ERROR",
            message="TTS generation failed",
            status_code=500
        )
