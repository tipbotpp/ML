import re
from typing import Any
from enum import Enum


class TextSanitizer:
    MAX_LENGTH = 2000
    CYRILLIC_PATTERN = re.compile(r'^[\u0400-\u04FF\s\d\p{P}]*$')
    EMOJI_PATTERN = re.compile(r'[\U0001F300-\U0001F9FF]|[\u2600-\u27BF]')
    
    @classmethod
    def sanitize_for_moderation(cls, text: str, max_length: int = 300) -> str:
        if not text or not isinstance(text, str):
            return ""
        
        text = text.strip()
        text = cls._remove_urls(text)
        text = cls._normalize_whitespace(text)
        text = cls._remove_excessive_punctuation(text)
        
        if len(text) > max_length:
            text = text[:max_length].rsplit(' ', 1)[0]
        
        return text
    
    @classmethod
    def sanitize_for_tts(cls, text: str, max_length: int = 500) -> str:
        if not text or not isinstance(text, str):
            return ""
        
        text = text.strip()
        text = cls._normalize_whitespace(text)
        text = cls._convert_numbers_to_text(text)
        text = cls._remove_special_tts_chars(text)
        
        if len(text) > max_length:
            text = text[:max_length].rsplit(' ', 1)[0]
        
        text = cls._ensure_proper_ending(text)
        return text
    
    @classmethod
    def sanitize_for_image_prompt(cls, text: str, max_length: int = 1000) -> str:
        if not text or not isinstance(text, str):
            return ""
        
        text = text.strip()
        text = cls._normalize_whitespace(text)
        text = cls._remove_urls(text)
        text = cls._remove_emoji(text)
        
        if len(text) > max_length:
            text = text[:max_length].rsplit(' ', 1)[0]
        
        return text
    
    @staticmethod
    def _remove_urls(text: str) -> str:
        url_pattern = r'https?://(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&/=]*)'
        return re.sub(url_pattern, '', text)
    
    @staticmethod
    def _normalize_whitespace(text: str) -> str:
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    @staticmethod
    def _remove_excessive_punctuation(text: str) -> str:
        text = re.sub(r'([!?.]){2,}', r'\1', text)
        text = re.sub(r'[^\w\s\u0400-\u04FF\-.,!?]', '', text)
        return text
    
    @staticmethod
    def _convert_numbers_to_text(text: str) -> str:
        ones = ['', 'один', 'два', 'три', 'четыре', 'пять', 'шесть', 'семь', 'восемь', 'девять']
        tens = ['', '', 'двадцать', 'тридцать', 'сорок', 'пятьдесят', 'шестьдесят', 'семьдесят', 'восемьдесят', 'девяносто']
        
        def convert_number(match):
            num = int(match.group())
            if num < 10:
                return ones[num]
            elif num < 100:
                return tens[num // 10] + (' ' + ones[num % 10] if num % 10 != 0 else '')
            elif num < 1000:
                return ones[num // 100] + ' сто' + (' ' + convert_number(re.match(r'\d+', str(num % 100))) if num % 100 != 0 else '')
            return str(num)
        
        return re.sub(r'\d+', convert_number, text)
    
    @staticmethod
    def _remove_special_tts_chars(text: str) -> str:
        text = re.sub(r'[^\w\s\u0400-\u04FF\-.,!?;:]', '', text)
        return text
    
    @staticmethod
    def _remove_emoji(text: str) -> str:
        return re.sub(r'[\U0001F300-\U0001F9FF]|[\u2600-\u27BF]|[\U0001F900-\U0001F9FF]', '', text)
    
    @staticmethod
    def _ensure_proper_ending(text: str) -> str:
        if not text:
            return text
        if not text[-1] in '.!?,;:':
            text += '.'
        return text


class ParameterValidator:
    @staticmethod
    def validate_moderation_params(text: str, stopwords: list) -> dict:
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Text must be non-empty string")
        
        if len(text) > 300:
            raise ValueError(f"Text too long: {len(text)} > 300")
        
        if not isinstance(stopwords, (list, tuple)):
            raise ValueError("Stopwords must be list or tuple")
        
        if len(stopwords) > 50:
            raise ValueError(f"Too many stopwords: {len(stopwords)} > 50")
        
        for word in stopwords:
            if not isinstance(word, str) or not word.strip():
                raise ValueError("All stopwords must be non-empty strings")
            if len(word) > 50:
                raise ValueError(f"Stopword too long: {word}")
        
        return {
            "text_length": len(text),
            "stopwords_count": len(stopwords),
            "is_valid": True
        }
    
    @staticmethod
    def validate_tts_params(text: str, voice: str, sample_rate: int) -> dict:
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Text must be non-empty string")
        
        if len(text) > 500:
            raise ValueError(f"Text too long for TTS: {len(text)} > 500")
        
        valid_voices = ['aidar', 'baya', 'kseniya', 'xenia', 'eugene', 'random']
        if voice not in valid_voices:
            raise ValueError(f"Invalid voice: {voice}. Must be one of {valid_voices}")
        
        valid_sample_rates = [8000, 16000, 24000, 48000]
        if sample_rate not in valid_sample_rates:
            raise ValueError(f"Invalid sample rate: {sample_rate}. Must be one of {valid_sample_rates}")
        
        return {
            "text_length": len(text),
            "voice": voice,
            "sample_rate": sample_rate,
            "is_valid": True
        }
    
    @staticmethod
    def validate_image_params(prompt: str, negative_prompt: str, width: int, height: int) -> dict:
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("Prompt must be non-empty string")
        
        if len(prompt) > 1000:
            raise ValueError(f"Prompt too long: {len(prompt)} > 1000")
        
        valid_widths = [512, 768, 1024, 1280]
        valid_heights = [512, 768, 1024, 1280]
        
        if width not in valid_widths:
            raise ValueError(f"Invalid width: {width}. Must be one of {valid_widths}")
        
        if height not in valid_heights:
            raise ValueError(f"Invalid height: {height}. Must be one of {valid_heights}")
        
        if negative_prompt and len(negative_prompt) > 500:
            raise ValueError(f"Negative prompt too long: {len(negative_prompt)} > 500")
        
        return {
            "prompt_length": len(prompt),
            "negative_prompt_length": len(negative_prompt) if negative_prompt else 0,
            "dimensions": f"{width}x{height}",
            "is_valid": True
        }


class RequestFormatter:
    @staticmethod
    def format_moderation_api_request(text: str, stopwords: list) -> dict:
        validation = ParameterValidator.validate_moderation_params(text, stopwords)
        sanitized_text = TextSanitizer.sanitize_for_moderation(text)
        
        return {
            "text": sanitized_text,
            "language": "ru",
            "stopwords": [w.lower().strip() for w in stopwords if w.strip()],
            "validation": validation,
        }
    
    @staticmethod
    def format_tts_api_request(text: str, voice: str, sample_rate: int) -> dict:
        validation = ParameterValidator.validate_tts_params(text, voice, sample_rate)
        sanitized_text = TextSanitizer.sanitize_for_tts(text)
        
        return {
            "text": sanitized_text,
            "voice": voice,
            "sample_rate": sample_rate,
            "language": "ru",
            "validation": validation,
        }
    
    @staticmethod
    def format_image_api_request(
        prompt: str,
        negative_prompt: str,
        width: int,
        height: int,
        model: str = "flux"
    ) -> dict:
        validation = ParameterValidator.validate_image_params(
            prompt, negative_prompt, width, height
        )
        sanitized_prompt = TextSanitizer.sanitize_for_image_prompt(prompt)
        sanitized_negative = (
            TextSanitizer.sanitize_for_image_prompt(negative_prompt)
            if negative_prompt else ""
        )
        
        return {
            "prompt": sanitized_prompt,
            "negative_prompt": sanitized_negative or None,
            "width": width,
            "height": height,
            "model": model,
            "language": "ru",
            "validation": validation,
        }


class ResponseFormatter:
    @staticmethod
    def format_moderation_response(raw_response: dict) -> dict:
        return {
            "is_toxic": bool(raw_response.get("is_toxic", False)),
            "toxicity_score": float(raw_response.get("toxicity_score", 0.0)),
            "confidence": float(raw_response.get("confidence", 0.0)),
            "timestamp": raw_response.get("timestamp"),
        }
    
    @staticmethod
    def format_tts_response(audio_bytes: bytes, duration: float) -> dict:
        return {
            "audio_size_bytes": len(audio_bytes),
            "duration_seconds": float(duration),
            "format": "wav",
            "sample_rate": 48000,
        }
    
    @staticmethod
    def format_image_response(
        image_bytes: bytes,
        width: int,
        height: int,
        nsfw_detected: bool = False,
        nsfw_score: float = 0.0
    ) -> dict:
        return {
            "image_size_bytes": len(image_bytes),
            "dimensions": f"{width}x{height}",
            "format": "png",
            "nsfw_detected": bool(nsfw_detected),
            "nsfw_score": float(nsfw_score),
        }


class ErrorFormatter:
    @staticmethod
    def format_error(error_code: str, error_message: str, details: dict = None) -> dict:
        return {
            "error": True,
            "code": error_code,
            "message": error_message,
            "details": details or {},
        }
    
    @staticmethod
    def format_validation_error(field: str, reason: str) -> dict:
        return ErrorFormatter.format_error(
            "VALIDATION_ERROR",
            f"Validation failed for field: {field}",
            {"field": field, "reason": reason}
        )
    
    @staticmethod
    def format_api_error(service: str, status_code: int, error_details: str) -> dict:
        return ErrorFormatter.format_error(
            f"{service.upper()}_API_ERROR",
            f"External API call failed",
            {
                "service": service,
                "status_code": status_code,
                "details": error_details[:200]
            }
        )
