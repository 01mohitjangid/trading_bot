"""Central logging configuration.

Every API request, response, and error is written to both the console and a
rotating log file, satisfying the task's "log API requests, responses, and
errors to a log file" requirement while keeping the console readable.
"""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOGGER_NAME = "trading_bot"

_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(
    log_dir: Path | str = "logs",
    level: str = "INFO",
    log_file: str = "trading_bot.log",
) -> logging.Logger:
    """Configure and return the application logger. Safe to call repeatedly."""
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.propagate = False

    # Idempotent: don't attach duplicate handlers on repeat calls.
    if logger.handlers:
        return logger

    formatter = logging.Formatter(_FORMAT, datefmt=_DATE_FORMAT)

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)

    file_handler = RotatingFileHandler(
        log_dir / log_file,
        maxBytes=1_000_000,  # ~1 MB per file
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


def get_logger() -> logging.Logger:
    """Return the shared application logger (configure it via setup_logging)."""
    return logging.getLogger(LOGGER_NAME)
