# backend/app/core/logging_config.py
import logging

from pythonjsonlogger import jsonlogger
from app.core.config import settings


def configure_logging() -> None:
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    formatter = jsonlogger.JsonFormatter(fmt="%(asctime)s %(levelname)s %(name)s %(message)s")
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(log_level)

    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uvicorn_logger = logging.getLogger(logger_name)
        uvicorn_logger.handlers = [handler]
        uvicorn_logger.setLevel(log_level)
        uvicorn_logger.propagate = False

    noisy_loggers = (
        "asyncio",
        "cachecontrol",
        "cachecontrol.controller",
        "sqlalchemy.engine",
        "sqlalchemy.pool",
        "urllib3",
        "urllib3.connectionpool",
        "urllib3.util.retry",
        "uvicorn.protocols.websockets",
        "websockets",
        "websockets.client",
        "websockets.server",
    )
    for logger_name in noisy_loggers:
        logging.getLogger(logger_name).setLevel(logging.WARNING)

    logging.captureWarnings(True)
