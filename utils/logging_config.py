"""Logging configuration for CoreSync."""

import logging
import sys
from pathlib import Path
from utils.config import LOGS_DIR, APP_NAME

def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Configure console and file log handlers."""
    logger = logging.getLogger(APP_NAME)
    
    # Avoid duplicate handlers on re-initialization
    if logger.handlers:
        return logger

    logger.setLevel(level)

    log_format = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] [%(name)s.%(funcName)s:%(lineno)d] %(message)s",
        datefmt="%H:%M:%S"
    )

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_format)
    console_handler.setLevel(level)
    logger.addHandler(console_handler)

    # File Handler
    log_file = LOGS_DIR / "coresync.log"
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(log_format)
    file_handler.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)

    return logger

