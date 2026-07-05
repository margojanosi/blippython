"""Logging configuration for the BrightHR Time Review MVP."""

import logging
import sys
from pathlib import Path


def configure_logging(log_level: str = "INFO", log_file: Path | None = None) -> None:
    """Configure root logger with console (and optional file) handlers.

    Args:
        log_level: Logging level string, e.g. "INFO", "DEBUG".
        log_file:  Optional path to a log file.
    """
    fmt = "%(asctime)s  %(levelname)-8s  %(name)s  %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(fmt=fmt, datefmt=datefmt)

    root = logging.getLogger()
    root.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root.addHandler(console_handler)

    # Optional file handler
    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)
