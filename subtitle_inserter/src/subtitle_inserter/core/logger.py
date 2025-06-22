"""Logging utilities following the project logging rules."""
from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


LOG_MAX_BYTES = 256 * 1024  # 256 KB
LOG_BACKUP_COUNT = 5


def setup_logger(log_dir: Path) -> None:
    """Initialize root logger with rotating file + console handlers.

    Parameters
    ----------
    log_dir : Path
        Directory where `application.log` will be stored.
    """
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "application.log"

    formatter = logging.Formatter(
        fmt="%(asctime)s|%(levelname)s|%(filename)s:%(lineno)d|%(funcName)s|%(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        log_file, maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUP_COUNT, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.DEBUG)

    # Configure root logger. Remove existing handlers to avoid duplication.
    root_logger = logging.getLogger()
    for h in list(root_logger.handlers):
        root_logger.removeHandler(h)

    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)


def get_logger(name: str | None = None) -> logging.Logger:
    """Get a named logger after root logger is configured."""
    return logging.getLogger(name) 