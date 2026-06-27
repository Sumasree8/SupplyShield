"""Structured request logging + Prometheus metrics middleware."""
import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from src.config.metrics import REQUEST_COUNT, REQUEST_LATENCY

log = structlog.get_logger()


def _route_label(request: Request) -> str:
    """Use the matched route template (e.g. /api/v1/suppliers/{id}) rather than
    the raw path, so per-ID URLs don't explode Prometheus label cardinality."""
    route = request.scope.get("route")
    return getattr(route, "path", request.url.path)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        start = time.perf_counter()
        response = await call_next(request)
        duration_s = time.perf_counter() - start

        path_label = _route_label(request)
        REQUEST_COUNT.labels(
            method=request.method, path=path_label, status=response.status_code
        ).inc()
        REQUEST_LATENCY.labels(method=request.method, path=path_label).observe(duration_s)

        # Skip health check noise in logs
        if request.url.path != "/api/v1/health":
            log.info(
                "http.request",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=round(duration_s * 1000, 2),
                client=request.client.host if request.client else None,
            )

        response.headers["X-Request-ID"] = request_id
        return response
