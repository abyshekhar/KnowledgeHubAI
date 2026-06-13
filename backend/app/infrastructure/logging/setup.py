from __future__ import annotations

import logging

import structlog


def configure_logging(environment: str) -> None:
    logging.basicConfig(level=logging.INFO)
    processors = [
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ]
    if environment == "development":
        processors[-1] = structlog.dev.ConsoleRenderer()
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        cache_logger_on_first_use=True,
    )

