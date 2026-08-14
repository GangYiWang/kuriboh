import logging

from app.core.logging import JsonFormatter, configure_logging


def test_uvicorn_loggers_use_plain_json_formatter() -> None:
    configure_logging("INFO")

    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(name)
        assert logger.propagate is False
        assert len(logger.handlers) == 1
        assert isinstance(logger.handlers[0].formatter, JsonFormatter)
