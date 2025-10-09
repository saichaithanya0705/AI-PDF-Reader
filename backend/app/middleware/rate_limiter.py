"""
Rate limiting middleware to prevent API abuse
"""
from fastapi import Request, HTTPException, status
from collections import defaultdict
from typing import Dict, List
import time
from datetime import datetime, timedelta
import asyncio


class RateLimiter:
    """
    Simple in-memory rate limiter
    
    For production, consider using Redis for distributed rate limiting
    """
    
    def __init__(
        self,
        max_requests: int = 100,
        window_seconds: int = 60,
        block_duration_seconds: int = 300
    ):
        """
        Initialize rate limiter
        
        Args:
            max_requests: Maximum requests allowed in time window
            window_seconds: Time window in seconds
            block_duration_seconds: How long to block after exceeding limit
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.block_duration_seconds = block_duration_seconds
        
        # Track requests: {user_id: [timestamp1, timestamp2, ...]}
        self.requests: Dict[str, List[float]] = defaultdict(list)
        
        # Track blocked users: {user_id: block_until_timestamp}
        self.blocked_until: Dict[str, float] = {}
        
        # Cleanup task
        self._cleanup_task = None
    
    async def start_cleanup_task(self):
        """Start background task to cleanup old entries"""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    async def _cleanup_loop(self):
        """Periodically clean up old request timestamps"""
        while True:
            await asyncio.sleep(self.window_seconds)
            now = time.time()
            
            # Clean old requests
            for user_id in list(self.requests.keys()):
                self.requests[user_id] = [
                    req_time for req_time in self.requests[user_id]
                    if now - req_time < self.window_seconds
                ]
                
                # Remove empty entries
                if not self.requests[user_id]:
                    del self.requests[user_id]
            
            # Clean expired blocks
            for user_id in list(self.blocked_until.keys()):
                if now >= self.blocked_until[user_id]:
                    del self.blocked_until[user_id]
    
    def check_rate_limit(self, user_id: str, endpoint: str = "default") -> None:
        """
        Check if user has exceeded rate limit
        
        Args:
            user_id: User identifier (can be IP for anonymous)
            endpoint: Optional endpoint-specific limiting
            
        Raises:
            HTTPException: If rate limit exceeded
        """
        now = time.time()
        
        # Check if user is blocked
        if user_id in self.blocked_until:
            block_until = self.blocked_until[user_id]
            if now < block_until:
                remaining = int(block_until - now)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Too many requests. Blocked for {remaining} more seconds.",
                    headers={
                        "Retry-After": str(remaining),
                        "X-RateLimit-Reset": str(int(block_until))
                    }
                )
            else:
                # Block expired
                del self.blocked_until[user_id]
        
        # Get request history for this user
        key = f"{user_id}:{endpoint}"
        request_times = self.requests[key]
        
        # Clean old requests (outside time window)
        request_times[:] = [
            req_time for req_time in request_times
            if now - req_time < self.window_seconds
        ]
        
        # Check if limit exceeded
        if len(request_times) >= self.max_requests:
            # Block user
            self.blocked_until[user_id] = now + self.block_duration_seconds
            
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    f"Rate limit exceeded. Maximum {self.max_requests} requests "
                    f"per {self.window_seconds} seconds. Blocked for {self.block_duration_seconds} seconds."
                ),
                headers={
                    "Retry-After": str(self.block_duration_seconds),
                    "X-RateLimit-Limit": str(self.max_requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(now + self.block_duration_seconds))
                }
            )
        
        # Add current request
        request_times.append(now)
        
        # Calculate remaining requests
        remaining = self.max_requests - len(request_times)
        
        return remaining
    
    def get_rate_limit_headers(self, user_id: str, endpoint: str = "default") -> dict:
        """Get rate limit headers for response"""
        key = f"{user_id}:{endpoint}"
        request_times = self.requests[key]
        remaining = max(0, self.max_requests - len(request_times))
        
        reset_time = int(time.time() + self.window_seconds)
        
        return {
            "X-RateLimit-Limit": str(self.max_requests),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Reset": str(reset_time)
        }


# Global rate limiters for different endpoints
default_limiter = RateLimiter(max_requests=100, window_seconds=60)
upload_limiter = RateLimiter(max_requests=10, window_seconds=3600)  # 10 uploads per hour
auth_limiter = RateLimiter(max_requests=5, window_seconds=300)  # 5 login attempts per 5 min


async def rate_limit_default(request: Request):
    """Default rate limiting for general API endpoints"""
    user_id = getattr(request.state, "user_id", request.client.host)
    endpoint = "default"
    default_limiter.check_rate_limit(user_id, endpoint)


async def rate_limit_upload(request: Request):
    """Strict rate limiting for upload endpoints"""
    user_id = getattr(request.state, "user_id", request.client.host)
    endpoint = "upload"
    upload_limiter.check_rate_limit(user_id, endpoint)


async def rate_limit_auth(request: Request):
    """Strict rate limiting for authentication endpoints"""
    # For auth, use IP address since user might not be authenticated yet
    user_id = request.client.host
    endpoint = "auth"
    auth_limiter.check_rate_limit(user_id, endpoint)


class IPRateLimiter:
    """Rate limiter based on IP address (for anonymous requests)"""
    
    def __init__(self, max_requests: int = 50, window_seconds: int = 60):
        self.limiter = RateLimiter(max_requests, window_seconds)
    
    async def __call__(self, request: Request):
        """Rate limit by IP address"""
        ip_address = request.client.host
        self.limiter.check_rate_limit(ip_address, "ip")


# Example usage in routes:
"""
from fastapi import Depends
from .middleware.rate_limiter import rate_limit_default, rate_limit_upload, rate_limit_auth

# Apply to specific endpoints
@app.post("/api/upload", dependencies=[Depends(rate_limit_upload)])
async def upload_document(file: UploadFile):
    pass

@app.post("/api/login", dependencies=[Depends(rate_limit_auth)])
async def login(credentials: dict):
    pass

# Apply globally to all routes
@app.middleware("http")
async def add_rate_limiting(request: Request, call_next):
    user_id = getattr(request.state, "user_id", request.client.host)
    
    try:
        default_limiter.check_rate_limit(user_id, request.url.path)
        response = await call_next(request)
        
        # Add rate limit headers
        headers = default_limiter.get_rate_limit_headers(user_id, request.url.path)
        for key, value in headers.items():
            response.headers[key] = value
        
        return response
    except HTTPException as e:
        raise e
"""
