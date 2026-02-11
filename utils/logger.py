"""
Logging utilities and helpers for the content generation pipeline.

This module provides utilities for creating contextual loggers,
tracking request IDs, and measuring execution time.
"""

import logging
import uuid
import time
from functools import wraps
from typing import Any, Callable, TypeVar, Optional

T = TypeVar('T')


class RequestIDFilter(logging.Filter):
    """Add request ID to all log records."""
    
    def __init__(self, request_id: str):
        """
        Initialize filter with request ID.
        
        Args:
            request_id: Unique identifier for this request/pipeline run
        """
        super().__init__()
        self.request_id = request_id
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Add request ID to log record."""
        record.request_id = self.request_id
        return True


class AgentNameFilter(logging.Filter):
    """Add agent name to all log records."""
    
    def __init__(self, agent_name: str):
        """
        Initialize filter with agent name.
        
        Args:
            agent_name: Name of the agent (e.g., "Planner", "Writer")
        """
        super().__init__()
        self.agent_name = agent_name
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Add agent name to log record."""
        record.agent_name = self.agent_name
        return True


def generate_request_id() -> str:
    """
    Generate a unique request ID for tracking pipeline execution.
    
    Returns:
        UUID string
    """
    return str(uuid.uuid4())


def get_logger(
    name: str,
    request_id: Optional[str] = None,
    agent_name: Optional[str] = None
) -> logging.Logger:
    """
    Get a logger with optional request ID and agent name context.
    
    Args:
        name: Logger name (typically __name__)
        request_id: Optional request ID to add to all logs
        agent_name: Optional agent name to add to all logs
    
    Returns:
        Configured logger instance
    
    Example:
        logger = get_logger(__name__, request_id="abc-123", agent_name="Planner")
        logger.info("Planning started")
    """
    logger = logging.getLogger(name)
    
    # Add request ID filter if provided
    if request_id:
        logger.addFilter(RequestIDFilter(request_id))
    
    # Add agent name filter if provided
    if agent_name:
        logger.addFilter(AgentNameFilter(agent_name))
    
    return logger


def log_execution_time(logger: Optional[logging.Logger] = None):
    """
    Decorator to log function execution time.
    
    Args:
        logger: Logger instance to use (if None, creates one from function module)
    
    Returns:
        Decorator function
    
    Example:
        @log_execution_time()
        def process_data():
            # ... processing
            pass
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            # Get logger
            nonlocal logger
            if logger is None:
                logger = logging.getLogger(func.__module__)
            
            func_name = func.__name__
            logger.debug(f"{func_name} started")
            
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                logger.info(
                    f"{func_name} completed in {duration:.2f}s",
                    extra={"duration_seconds": duration, "function": func_name}
                )
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                
                logger.error(
                    f"{func_name} failed after {duration:.2f}s: {str(e)}",
                    extra={
                        "duration_seconds": duration,
                        "function": func_name,
                        "error": str(e),
                        "error_type": type(e).__name__
                    },
                    exc_info=True
                )
                
                raise
        
        return wrapper
    return decorator


class ExecutionTimer:
    """
    Context manager for timing code blocks.
    
    Example:
        with ExecutionTimer(logger, "data processing"):
            # ... code to time
            pass
    """
    
    def __init__(self, logger: logging.Logger, operation_name: str):
        """
        Initialize timer.
        
        Args:
            logger: Logger instance
            operation_name: Name of the operation being timed
        """
        self.logger = logger
        self.operation_name = operation_name
        self.start_time: Optional[float] = None
    
    def __enter__(self):
        """Start timing."""
        self.start_time = time.time()
        self.logger.debug(f"{self.operation_name} started")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop timing and log duration."""
        if self.start_time is not None:
            duration = time.time() - self.start_time
            
            if exc_type is None:
                self.logger.info(
                    f"{self.operation_name} completed in {duration:.2f}s",
                    extra={"duration_seconds": duration, "operation": self.operation_name}
                )
            else:
                self.logger.error(
                    f"{self.operation_name} failed after {duration:.2f}s",
                    extra={
                        "duration_seconds": duration,
                        "operation": self.operation_name,
                        "error_type": exc_type.__name__ if exc_type else None
                    }
                )


def log_with_context(logger: logging.Logger, level: str, message: str, **context):
    """
    Log a message with additional context data.
    
    Args:
        logger: Logger instance
        level: Log level (debug, info, warning, error, critical)
        message: Log message
        **context: Additional context key-value pairs
    
    Example:
        log_with_context(
            logger, "info", "Agent completed",
            agent="Planner", tokens=150, duration=2.5
        )
    """
    log_func = getattr(logger, level.lower())
    log_func(message, extra={"extra_data": context})
