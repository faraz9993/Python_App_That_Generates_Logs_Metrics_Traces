from opentelemetry import trace


def current_trace_ids() -> tuple[str, str]:
    span_context = trace.get_current_span().get_span_context()
    if not span_context.is_valid:
        return "", ""
    return format(span_context.trace_id, "032x"), format(span_context.span_id, "016x")


def route_template(scope: dict) -> str:
    route = scope.get("route")
    if route and getattr(route, "path", None):
        return route.path
    return scope.get("path", "unknown")

