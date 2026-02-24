"""Global middleware — error handling for rate limits, scraping blocks."""

from __future__ import annotations

import logging

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Catches unhandled exceptions at the middleware level and returns
    structured error responses instead of crashing.
    """

    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            logger.exception(f"Unhandled exception on {request.method} {request.url.path}")

            status_code = 500
            detail = "Internal server error"

            # Rate limit detection
            if "429" in str(exc) or "rate" in str(exc).lower():
                status_code = 429
                detail = "Rate limited by upstream API. Please retry in a few seconds."

            # Scraping block
            elif "403" in str(exc) or "blocked" in str(exc).lower():
                status_code = 502
                detail = "Upstream resource blocked the request."

            return JSONResponse(
                status_code=status_code,
                content={"error": detail, "detail": str(exc)},
            )
