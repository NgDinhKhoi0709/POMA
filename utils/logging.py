"""Logging helpers for POMA."""

from __future__ import annotations

import logging
import sys
from typing import Optional

_loggers: dict = {}


def setup_logger(
    level: str = "INFO",
    output_dir: Optional[str] = None,
    log_format: str = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
) -> logging.Logger:
    """Configure the package root logger (console only)."""
    logger = logging.getLogger("poma")
    logger.handlers.clear()
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
    }
    logger.setLevel(level_map.get(level.upper(), logging.INFO))
    formatter = logging.Formatter(log_format, datefmt="%Y-%m-%d %H:%M:%S")
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    return logger


def get_logger(name: str) -> logging.Logger:
    """Return a child logger under `poma`."""
    if name in _loggers:
        return _loggers[name]
    if not name.lower().startswith("poma"):
        name = f"poma.{name}"
    logger = logging.getLogger(name)
    _loggers[name] = logger
    return logger
