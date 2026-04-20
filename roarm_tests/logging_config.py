"""
Centralized logging configuration for RoArm test suite.
Ensures consistent logging across all modules.
"""

import logging
import os
from logging.handlers import RotatingFileHandler

# Logger cache to prevent duplicate handlers
_configured_loggers = set()


def setup_logging(log_name, log_file_name='default.log', log_level=logging.DEBUG):
    """
    Setup logging for a module with file and console handlers.
    
    Args:
        log_name: Name of the logger (usually __name__)
        log_file_name: Name of the log file (e.g., 'roarm_sequence.log')
        log_level: Logging level (default: DEBUG)
    
    Returns:
        Configured logger instance
    """
    # Prevent duplicate handler configuration
    if log_name in _configured_loggers:
        return logging.getLogger(log_name)
    
    # Create logs directory if it doesn't exist
    logs_dir = os.path.join(os.path.dirname(__file__), 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    
    # Get logger
    logger = logging.getLogger(log_name)
    logger.setLevel(log_level)
    
    # Remove any existing handlers (in case of reconfiguration)
    logger.handlers.clear()
    
    # Define log format
    log_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # File handler with rotation (max 5MB per file, keep 5 old files)
    log_file_path = os.path.join(logs_dir, log_file_name)
    file_handler = RotatingFileHandler(
        log_file_path, 
        maxBytes=5*1024*1024,  # 5MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(log_format)
    logger.addHandler(file_handler)
    
    # Console handler - only INFO and above to reduce console noise
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(log_format)
    logger.addHandler(console_handler)
    
    # Mark as configured
    _configured_loggers.add(log_name)
    
    return logger, os.path.join(logs_dir, log_file_name)


def get_logs_dir():
    """Get the logs directory path."""
    return os.path.join(os.path.dirname(__file__), 'logs')
