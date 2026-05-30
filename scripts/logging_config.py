"""
Centralized logging configuration for RoArm test suite.
Ensures consistent logging across all modules.
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOGS_DIR: Path = Path(__file__).parent / "logs"

_configured: dict[str, Path] = {}


def setup_logging(
    log_name: str,
    log_file_name: str = "default.log",
    log_level: int = logging.DEBUG,
) -> tuple[logging.Logger, Path]:
    """
    Setup logging for a module with rotating file + INFO console handlers.

    Args:
        log_name: Name of the logger (usually __name__)
        log_file_name: File name within the logs directory
        log_level: Logger threshold (default DEBUG)

    Returns:
        (logger, log_file_path)
    """
    if log_name in _configured:
        return logging.getLogger(log_name), _configured[log_name]

    LOGS_DIR.mkdir(exist_ok=True)
    log_file_path = LOGS_DIR / log_file_name

    logger = logging.getLogger(log_name)
    logger.setLevel(log_level)
    logger.handlers.clear()

    fmt = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        log_file_path, maxBytes=5 * 1024 * 1024, backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(fmt)
    logger.addHandler(console_handler)

    _configured[log_name] = log_file_path
    return logger, log_file_path


def get_logs_dir() -> Path:
    return LOGS_DIR
