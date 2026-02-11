"""
Centralized logging configuration for the content generation pipeline.

This module sets up structured logging with multiple handlers, formats,
and rotation policies to provide comprehensive observability.
"""

import logging
import logging.handlers
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any


class JSONFormatter(logging.Formatter):
    """Custom formatter that outputs logs as JSON."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add request ID if available
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        
        # Add agent name if available
        if hasattr(record, "agent_name"):
            log_data["agent_name"] = record.agent_name
        
        # Add execution phase if available
        if hasattr(record, "phase"):
            log_data["phase"] = record.phase
        
        # Add any extra fields
        if hasattr(record, "extra_data"):
            log_data.update(record.extra_data)
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)


class HumanReadableFormatter(logging.Formatter):
    """Custom formatter for human-readable console output."""
    
    # Color codes for different log levels
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record for human readability with colors."""
        # Add color to level name
        levelname = record.levelname
        if levelname in self.COLORS:
            colored_levelname = f"{self.COLORS[levelname]}{levelname:8}{self.RESET}"
        else:
            colored_levelname = f"{levelname:8}"
        
        # Build the log message
        parts = [
            f"{colored_levelname}",
            f"[{record.name}]",
        ]
        
        # Add request ID if available
        if hasattr(record, "request_id"):
            parts.append(f"({record.request_id[:8]})")
        
        # Add the message
        parts.append(record.getMessage())
        
        log_message = " ".join(parts)
        
        # Add exception info if present
        if record.exc_info:
            log_message += "\n" + self.formatException(record.exc_info)
        
        return log_message


def setup_logging(
    log_dir: str = "logs",
    level: str = "INFO",
    format_type: str = "human",
    enable_console: bool = True,
    enable_file: bool = True
) -> None:
    """
    Configure application-wide logging.
    
    Args:
        log_dir: Directory for log files (default: "logs")
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_type: Log format - "human" or "json" (default: "human")
        enable_console: Whether to log to console (default: True)
        enable_file: Whether to log to files (default: True)
    """
    # Create logs directory if it doesn't exist
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    
    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()
    
    # Console handler (human-readable format)
    if enable_console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, level.upper()))
        
        if format_type == "json":
            console_handler.setFormatter(JSONFormatter())
        else:
            console_handler.setFormatter(HumanReadableFormatter())
        
        root_logger.addHandler(console_handler)
    
    # File handler (JSON format for easy parsing)
    if enable_file:
        file_handler = logging.handlers.RotatingFileHandler(
            filename=log_path / "content_generation.log",
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)  # Always log DEBUG to file
        file_handler.setFormatter(JSONFormatter())
        root_logger.addHandler(file_handler)
        
        # Separate error log file
        error_handler = logging.handlers.RotatingFileHandler(
            filename=log_path / "errors.log",
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding="utf-8"
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(JSONFormatter())
        root_logger.addHandler(error_handler)
    
    # Log the configuration
    root_logger.info(
        f"Logging configured: level={level}, format={format_type}, "
        f"console={enable_console}, file={enable_file}"
    )


def get_log_level_from_env() -> str:
    """Get log level from environment variable."""
    return os.getenv("LOG_LEVEL", "INFO").upper()


def get_log_format_from_env() -> str:
    """Get log format from environment variable."""
    return os.getenv("LOG_FORMAT", "human").lower()


def get_log_dir_from_env() -> str:
    """Get log directory from environment variable."""
    return os.getenv("LOG_DIR", "logs")
