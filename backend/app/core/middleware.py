from time import perf_counter
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import get_logger


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid4())
        request.state.request_id = request_id
        started_at = perf_counter()
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        get_logger("lizibei.request").info(
            "%s %s %s %.2fms",
            request.method,
            request.url.path,
            response.status_code,
            (perf_counter() - started_at) * 1000,
            extra={"request_id": request_id},
        )
        return response

