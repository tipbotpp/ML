from __future__ import annotations

from contextvars import ContextVar
from typing import Any

import structlog

from app.config import settings

http_path: ContextVar[str] = ContextVar("http_path", default="")
http_method: ContextVar[str] = ContextVar("http_method", default="")
http_layer: ContextVar[str] = ContextVar("http_layer", default="http")
http_request_id: ContextVar[str] = ContextVar("http_request_id", default="")


def http_context_processor(
    logger: Any,
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    path = http_path.get("")
    method = http_method.get("")
    layer = http_layer.get("http")
    request_id = http_request_id.get("")

    if path:
        event_dict["path"] = path
    if method:
        event_dict["method"] = method
    if layer:
        event_dict["layer"] = layer
    if request_id:
        event_dict["request_id"] = request_id

    return event_dict


def reorder_keys_processor(
    logger: Any,
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    ordered: dict[str, Any] = {}
    for key in ("method", "path", "request_id"):
        if key in event_dict:
            ordered[key] = event_dict.pop(key)
    ordered.update(event_dict)
    return ordered


def configure_logger() -> None:
    allowed_levels = {
        "DEBUG": 10,
        "INFO": 20,
        "WARNING": 30,
        "ERROR": 40,
        "CRITICAL": 50,
    }
    log_level = allowed_levels.get(settings.LOG_LEVEL.upper(), 20)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            http_context_processor,
            structlog.processors.add_log_level,
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(),
            reorder_keys_processor,
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False,
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
    )


class StructLogger:
    def __init__(self, context: dict[str, Any] | None = None) -> None:
        self._logger = None
        self._context = context or {}

    def _get_logger(self) -> Any:
        if self._logger is None:
            self._logger = structlog.get_logger()
        return self._logger

    def _caller_info(self) -> dict[str, Any]:
        import inspect
        for frame in inspect.stack()[2:]:
            if "logger.py" not in frame.filename and "structlog" not in frame.filename:
                return {
                    "source_file": frame.filename.split("/")[-1],
                    "func_name": frame.function,
                    "lineno": frame.lineno,
                }
        return {}

    def debug(self, message: str, **kwargs: object) -> None:
        self._get_logger().bind(**self._context, **self._caller_info()).debug(message, **kwargs)

    def info(self, message: str, **kwargs: object) -> None:
        self._get_logger().bind(**self._context, **self._caller_info()).info(message, **kwargs)

    def warning(self, message: str, **kwargs: object) -> None:
        self._get_logger().bind(**self._context, **self._caller_info()).warning(message, **kwargs)

    def error(self, message: str, **kwargs: object) -> None:
        self._get_logger().bind(**self._context, **self._caller_info()).error(message, **kwargs)

    def bind(self, **kwargs: object) -> StructLogger:
        return StructLogger({**self._context, **kwargs})


_logger_instance: StructLogger | None = None


def get_logger() -> StructLogger:
    global _logger_instance
    if _logger_instance is None:
        configure_logger()
        _logger_instance = StructLogger()
    return _logger_instance
