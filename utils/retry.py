"""
Retry utilities with exponential backoff for resilient API calls.

This module provides decorators and utilities for retrying operations
that may fail due to transient errors like network issues or rate limits.
"""

import time
import random
import logging
from functools import wraps
from typing import Callable, Type, Tuple, TypeVar, Any

logger = logging.getLogger(__name__)

T = TypeVar('T')


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
) -> Callable:
    """
    Decorator for retrying functions with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts (default: 3)
        base_delay: Initial delay in seconds (default: 1.0)
        max_delay: Maximum delay in seconds (default: 60.0)
        exponential_base: Base for exponential backoff (default: 2.0)
        jitter: Whether to add random jitter to delays (default: True)
        exceptions: Tuple of exception types to retry on (default: all exceptions)
    
    Returns:
        Decorated function with retry logic
    
    Example:
        @retry_with_backoff(max_retries=3, exceptions=(APIError, TimeoutError))
        def call_api():
            # API call that might fail
            pass
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            retries = 0
            
            while retries <= max_retries:
                try:
                    return func(*args, **kwargs)
                    
                except exceptions as e:
                    retries += 1
                    
                    if retries > max_retries:
                        logger.error(
                            f"{func.__name__} failed after {max_retries} retries",
                            extra={"error": str(e), "retries": retries}
                        )
                        raise
                    
                    # Calculate delay with exponential backoff
                    delay = min(base_delay * (exponential_base ** (retries - 1)), max_delay)
                    
                    # Add jitter to avoid thundering herd
                    if jitter:
                        delay = delay * (0.5 + random.random())
                    
                    logger.warning(
                        f"{func.__name__} failed, retrying in {delay:.2f}s (attempt {retries}/{max_retries})",
                        extra={"error": str(e), "delay": delay, "attempt": retries}
                    )
                    
                    time.sleep(delay)
                
                except Exception as e:
                    # Don't retry on unexpected exceptions
                    logger.error(
                        f"{func.__name__} failed with unexpected error",
                        extra={"error": str(e), "error_type": type(e).__name__}
                    )
                    raise
            
            # This should never be reached, but just in case
            raise RuntimeError(f"{func.__name__} exceeded retry budget")
        
        return wrapper
    return decorator


class RetryBudget:
    """
    Tracks retry attempts across multiple operations to prevent infinite retries.
    
    Example:
        budget = RetryBudget(max_total_retries=10)
        
        @budget.with_retry(max_retries=3)
        def operation():
            pass
    """
    
    def __init__(self, max_total_retries: int = 10):
        """
        Initialize retry budget.
        
        Args:
            max_total_retries: Maximum total retries across all operations
        """
        self.max_total_retries = max_total_retries
        self.total_retries = 0
        self.logger = logging.getLogger(f"{__name__}.RetryBudget")
    
    def with_retry(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        exceptions: Tuple[Type[Exception], ...] = (Exception,)
    ) -> Callable:
        """
        Create a retry decorator that respects the retry budget.
        
        Args:
            max_retries: Maximum retries for this operation
            base_delay: Initial delay in seconds
            exceptions: Tuple of exception types to retry on
        
        Returns:
            Decorator function
        """
        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            @wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> T:
                retries = 0
                
                while retries <= max_retries:
                    # Check if we've exceeded the total retry budget
                    if self.total_retries >= self.max_total_retries:
                        self.logger.error(
                            f"Retry budget exhausted ({self.total_retries}/{self.max_total_retries})"
                        )
                        raise RuntimeError("Retry budget exhausted")
                    
                    try:
                        return func(*args, **kwargs)
                    
                    except exceptions as e:
                        retries += 1
                        self.total_retries += 1
                        
                        if retries > max_retries:
                            self.logger.error(
                                f"{func.__name__} failed after {max_retries} retries"
                            )
                            raise
                        
                        delay = base_delay * (2 ** (retries - 1))
                        
                        self.logger.warning(
                            f"{func.__name__} failed, retrying in {delay:.2f}s "
                            f"(attempt {retries}/{max_retries}, "
                            f"total budget: {self.total_retries}/{self.max_total_retries})"
                        )
                        
                        time.sleep(delay)
                
                raise RuntimeError(f"{func.__name__} exceeded retry limit")
            
            return wrapper
        return decorator
    
    def reset(self):
        """Reset the retry budget counter."""
        self.total_retries = 0
        self.logger.info("Retry budget reset")
