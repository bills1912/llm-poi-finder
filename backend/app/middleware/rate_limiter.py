"""
Rate limiting middleware for API protection.
Implements token bucket algorithm for rate limiting.
"""

import time
import logging
from collections import defaultdict
from typing import Callable, Optional
from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings

logger = logging.getLogger(__name__)


class RateLimitExceeded(HTTPException):
    """Exception raised when rate limit is exceeded."""
    def __init__(self, retry_after: int):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "Rate limit exceeded",
                "message": "Too many requests. Please slow down.",
                "retry_after": retry_after
            },
            headers={"Retry-After": str(retry_after)}
        )


class TokenBucket:
    """
    Token bucket implementation for rate limiting.
    Allows burst traffic while maintaining average rate.
    """
    
    def __init__(self, rate: int, capacity: int):
        """
        Initialize token bucket.
        
        Args:
            rate: Tokens added per second
            capacity: Maximum tokens in bucket
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.time()
    
    def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens from bucket.
        
        Returns:
            True if tokens were consumed, False if not enough tokens
        """
        self._refill()
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False
    
    def _refill(self) -> None:
        """Refill tokens based on time elapsed."""
        now = time.time()
        elapsed = now - self.last_update
        
        # Add tokens based on elapsed time
        tokens_to_add = elapsed * self.rate
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_update = now
    
    def time_until_available(self, tokens: int = 1) -> float:
        """Calculate time until tokens are available."""
        self._refill()
        if self.tokens >= tokens:
            return 0
        needed = tokens - self.tokens
        return needed / self.rate


class RateLimiter:
    """
    Rate limiter using token bucket algorithm.
    Tracks limits per client IP address.
    """
    
    def __init__(
        self,
        requests_per_window: int = None,
        window_seconds: int = None,
        burst_multiplier: float = 1.5
    ):
        """
        Initialize rate limiter.
        
        Args:
            requests_per_window: Max requests per time window
            window_seconds: Time window in seconds
            burst_multiplier: Allow burst traffic up to this multiplier
        """
        self.requests_per_window = requests_per_window or settings.rate_limit_requests
        self.window_seconds = window_seconds or settings.rate_limit_window
        
        # Calculate rate (requests per second)
        self.rate = self.requests_per_window / self.window_seconds
        
        # Allow burst capacity
        self.capacity = int(self.requests_per_window * burst_multiplier)
        
        # Per-client buckets
        self._buckets: dict[str, TokenBucket] = defaultdict(
            lambda: TokenBucket(self.rate, self.capacity)
        )
        
        # Track for cleanup
        self._last_cleanup = time.time()
        self._cleanup_interval = 3600  # Clean up every hour
    
    def is_allowed(self, client_id: str) -> tuple[bool, int]:
        """
        Check if request is allowed for client.
        
        Returns:
            Tuple of (allowed, retry_after_seconds)
        """
        self._maybe_cleanup()
        
        bucket = self._buckets[client_id]
        
        if bucket.consume():
            return True, 0
        
        retry_after = int(bucket.time_until_available()) + 1
        return False, retry_after
    
    def _maybe_cleanup(self) -> None:
        """Periodically clean up old buckets to prevent memory leak."""
        now = time.time()
        if now - self._last_cleanup < self._cleanup_interval:
            return
        
        # Remove buckets that haven't been used in a while
        stale_clients = []
        for client_id, bucket in self._buckets.items():
            if now - bucket.last_update > self._cleanup_interval:
                stale_clients.append(client_id)
        
        for client_id in stale_clients:
            del self._buckets[client_id]
        
        self._last_cleanup = now
        logger.debug(f"Cleaned up {len(stale_clients)} stale rate limit buckets")


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for rate limiting.
    """
    
    def __init__(
        self,
        app,
        limiter: RateLimiter = None,
        exclude_paths: list[str] = None
    ):
        super().__init__(app)
        self.limiter = limiter or RateLimiter()
        self.exclude_paths = exclude_paths or ["/health", "/docs", "/openapi.json", "/redoc"]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with rate limiting."""
        
        # Skip rate limiting for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)
        
        # Get client identifier
        client_id = self._get_client_id(request)
        
        # Check rate limit
        allowed, retry_after = self.limiter.is_allowed(client_id)
        
        if not allowed:
            logger.warning(f"Rate limit exceeded for client {client_id}")
            raise RateLimitExceeded(retry_after)
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.limiter.requests_per_window)
        response.headers["X-RateLimit-Window"] = str(self.limiter.window_seconds)
        
        return response
    
    def _get_client_id(self, request: Request) -> str:
        """
        Get unique client identifier from request.
        Uses X-Forwarded-For if behind proxy, otherwise client IP.
        """
        # Check for forwarded header (when behind proxy/load balancer)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # Take the first IP in the chain
            return forwarded.split(",")[0].strip()
        
        # Use direct client IP
        if request.client:
            return request.client.host
        
        return "unknown"


# Create default limiter instance
default_limiter = RateLimiter()
