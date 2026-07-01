import logging
import sys
from typing import Any

import structlog

from app.config import Settings
from app.utils.helpers import current_trace_ids


def add_service_context(_: Any, __: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    from app.config import get_settings

    settings = get_settings()
    trace_id, span_id = current_trace_ids()
    event_dict["service_name"] = settings.service_name
    event_dict["environment"] = settings.environment
    event_dict["trace_id"] = trace_id
    event_dict["span_id"] = span_id
    return event_dict


def configure_logging(settings: Settings) -> None:
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            add_service_context,
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.log_level.upper(), logging.INFO)
        ),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = "app") -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)

