"""
Timing middleware to track request/response performance
Useful for monitoring API latency and identifying bottlenecks
"""

import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

logger = structlog.get_logger(__name__)


class TimingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to measure and log request processing time
    
    Adds headers:
    - X-Process-Time: Time taken to process the request
    - X-Request-ID: Unique identifier for the request
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate unique request ID
        import uuid
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id
        
        # Start timing
        start_time = time.time()
        
        # Log incoming request
        logger.info(
            "Request started",
            request_id=request_id,
            method=request.method,
            url=str(request.url),
            user_agent=request.headers.get("user-agent", "Unknown"),
            client_ip=request.client.host if request.client else "Unknown"
        )
        
        try:
            # Process the request
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Add timing headers
            response.headers["X-Process-Time"] = str(round(process_time, 4))
            response.headers["X-Request-ID"] = request_id
            
            # Log response
            logger.info(
                "Request completed",
                request_id=request_id,
                method=request.method,
                url=str(request.url),
                status_code=response.status_code,
                process_time=round(process_time, 4),
                slow_request=process_time > 2.0  # Flag slow requests
            )
            
            return response
            
        except Exception as e:
            # Calculate processing time even for errors
            process_time = time.time() - start_time
            
            # Log error
            logger.error(
                "Request failed",
                request_id=request_id,
                method=request.method,
                url=str(request.url),
                error=str(e),
                process_time=round(process_time, 4)
            )
            
            raise