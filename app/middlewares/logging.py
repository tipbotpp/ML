import time
import uuid
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.services.logger import (
    get_logger,
    http_layer,
    http_method,
    http_path,
    http_request_id,
)


class HTTPLoggingMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = str(uuid.uuid4())[:8]

        http_path.set(str(request.url.path))
        http_method.set(request.method)
        http_layer.set("http")
        http_request_id.set(request_id)

        logger = get_logger().bind(middleware="http")
        start_time = time.time()

        if request.query_params:
            logger.debug("HTTP request started", query_params=str(request.query_params))
        else:
            logger.debug("HTTP request started")

        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            logger.info(
                "HTTP request completed",
                status_code=response.status_code,
                process_time_seconds=round(process_time, 4),
            )
            return response
        except Exception:
            raise
