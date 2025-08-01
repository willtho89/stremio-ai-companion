"""
Logging configuration for the Stremio AI Companion application.
"""

import logging
import os
import sys


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """
    Setup logging configuration with specified level.

    Args:
        log_level: The logging level to use (default: "INFO")

    Returns:
        A configured logger instance
    """
    level = getattr(logging, log_level.upper(), logging.INFO)

    # Create formatter
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Set specific logger levels
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    return logging.getLogger("stremio_ai_companion")


# Initialize logger with environment variable or default to INFO
logger = setup_logging(os.getenv("LOG_LEVEL", "INFO"))
