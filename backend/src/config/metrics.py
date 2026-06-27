"""
Prometheus metric definitions.

Kept in a dedicated module (rather than main.py) so both the app factory and
the request middleware can import them without a circular dependency.
"""
from prometheus_client import Counter, Histogram

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "path"],
)
