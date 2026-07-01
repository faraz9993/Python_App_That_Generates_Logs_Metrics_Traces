from prometheus_client import Counter, Histogram

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests.",
    ["method", "endpoint", "status", "service"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds.",
    ["method", "endpoint", "status", "service"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)

ORDERS_CREATED_TOTAL = Counter("orders_created_total", "Total orders created.", ["service"])
CUSTOMERS_RETRIEVED_TOTAL = Counter(
    "customers_retrieved_total", "Total customer retrieval operations.", ["service"]
)
PRODUCTS_RETRIEVED_TOTAL = Counter(
    "products_retrieved_total", "Total product retrieval operations.", ["service"]
)
DOWNSTREAM_CALLS_TOTAL = Counter(
    "downstream_calls_total",
    "Total downstream service calls.",
    ["service", "target", "status"],
)

