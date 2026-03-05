"""Error handling middleware and utilities for API resilience."""

from typing import Callable, Optional
import logging
from functools import wraps
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from app.config import get_settings

logger = logging.getLogger(__name__)


class APIError(Exception):
    """Base API error class."""
    def __init__(self, message: str, status_code: int = 500, error_code: str = "INTERNAL_ERROR"):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(message)


class ValidationError(APIError):
    """Invalid request data."""
    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(message, 400, "VALIDATION_ERROR")
        self.field = field


class NotFoundError(APIError):
    """Resource not found."""
    def __init__(self, resource: str, resource_id: str):
        message = f"{resource} '{resource_id}' not found"
        super().__init__(message, 404, "NOT_FOUND")


class RateLimitError(APIError):
    """Rate limit exceeded."""
    def __init__(self, retry_after: int = 60):
        super().__init__(
            f"Rate limit exceeded. Retry after {retry_after} seconds",
            429,
            "RATE_LIMIT_EXCEEDED"
        )
        self.retry_after = retry_after


class LLMError(APIError):
    """LLM provider error."""
    def __init__(self, message: str, provider: str):
        super().__init__(f"LLM Error ({provider}): {message}", 503, "LLM_ERROR")
        self.provider = provider


async def error_handler(request: Request, exc: Exception) -> Response:
    """Global error handler for API exceptions."""
    
    if isinstance(exc, APIError):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "message": exc.message,
                    "code": exc.error_code,
                    "field": getattr(exc, "field", None),
                }
            }
        )
    
    # Log unexpected errors
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "message": "Internal server error",
                "code": "INTERNAL_ERROR"
            }
        }
    )


def handle_errors(func: Callable) -> Callable:
    """Decorator to wrap async endpoints with error handling."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except APIError as e:
            raise HTTPException(status_code=e.status_code, detail=e.message)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Internal server error")
    return wrapper


class CircuitBreaker:
    """Circuit breaker for external API calls."""
    
    def __init__(self, failure_threshold: int = 5, timeout_seconds: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.failures = 0
        self.last_failure_time = 0
        self.is_open = False
    
    def record_success(self):
        """Record successful call."""
        self.failures = 0
        self.is_open = False
    
    def record_failure(self):
        """Record failed call."""
        self.failures += 1
        import time
        self.last_failure_time = time.time()
        if self.failures >= self.failure_threshold:
            self.is_open = True
    
    def is_available(self) -> bool:
        """Check if circuit is available."""
        if not self.is_open:
            return True
        
        import time
        if time.time() - self.last_failure_time > self.timeout_seconds:
            self.is_open = False
            self.failures = 0
            return True
        
        return False


# Global circuit breakers for LLM providers
_llm_circuit_breakers: dict[str, CircuitBreaker] = {}


def get_circuit_breaker(provider: str) -> CircuitBreaker:
    """Get or create circuit breaker for provider."""
    if provider not in _llm_circuit_breakers:
        _llm_circuit_breakers[provider] = CircuitBreaker()
    return _llm_circuit_breakers[provider]
