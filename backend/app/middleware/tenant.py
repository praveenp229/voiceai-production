"""
Tenant middleware for multi-tenant architecture
Handles tenant identification and context for all requests
"""

from typing import Callable, Optional
from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

logger = structlog.get_logger(__name__)


class TenantMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle multi-tenant context
    
    Extracts tenant information from:
    1. URL path parameters (/api/v1/voice/{tenant_id})
    2. Headers (X-Tenant-ID) 
    3. API key authentication
    
    Sets request.state.tenant_id for use in endpoints
    """
    
    def __init__(self, app):
        super().__init__(app)
        self.public_paths = {
            "/",
            "/health",
            "/version", 
            "/docs",
            "/redoc",
            "/openapi.json",
            "/metrics"
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip tenant validation for public paths
        if self._is_public_path(request.url.path):
            return await call_next(request)
        
        # Extract tenant ID from various sources
        tenant_id = await self._extract_tenant_id(request)
        
        if tenant_id:
            # Set tenant context for the request
            request.state.tenant_id = tenant_id
            
            # Validate tenant exists and is active (optional - can be done in endpoints)
            if await self._should_validate_tenant(request):
                await self._validate_tenant(tenant_id, request)
            
            logger.debug(
                "Tenant context set",
                tenant_id=tenant_id,
                path=request.url.path,
                method=request.method
            )
        
        return await call_next(request)
    
    def _is_public_path(self, path: str) -> bool:
        """Check if the path is public and doesn't require tenant context"""
        # Exact matches
        if path in self.public_paths:
            return True
        
        # Pattern matches
        if path.startswith("/static/"):
            return True
        
        if path.startswith("/api/v1/admin/login"):
            return True
            
        return False
    
    async def _extract_tenant_id(self, request: Request) -> Optional[str]:
        """Extract tenant ID from request"""
        
        # 1. From URL path parameters
        if "tenant_id" in request.path_params:
            tenant_id = request.path_params["tenant_id"]
            logger.debug("Tenant ID from path params", tenant_id=tenant_id)
            return tenant_id
        
        # 2. From headers
        tenant_header = request.headers.get("X-Tenant-ID")
        if tenant_header:
            logger.debug("Tenant ID from header", tenant_id=tenant_header)
            return tenant_header
        
        # 3. From API key (would require database lookup)
        api_key = request.headers.get("X-API-Key")
        if api_key:
            # This would typically involve a database lookup
            # For now, we'll extract from URL or return None
            pass
        
        # 4. From URL path segments (e.g., /api/v1/voice/tenant123/...)
        path_segments = request.url.path.strip("/").split("/")
        if len(path_segments) >= 4 and path_segments[0] == "api" and path_segments[1] == "v1":
            # Look for tenant ID in common positions
            for i, segment in enumerate(path_segments):
                if segment.startswith("tenant_") or (len(segment) == 36 and "-" in segment):
                    logger.debug("Tenant ID from URL segment", tenant_id=segment)
                    return segment
        
        return None
    
    async def _should_validate_tenant(self, request: Request) -> bool:
        """Determine if we should validate tenant exists in database"""
        # Skip validation for certain endpoints to avoid circular dependencies
        skip_validation_paths = [
            "/api/v1/tenants",  # Tenant management endpoints
            "/api/v1/admin/",   # Admin endpoints
        ]
        
        for skip_path in skip_validation_paths:
            if request.url.path.startswith(skip_path):
                return False
        
        return True
    
    async def _validate_tenant(self, tenant_id: str, request: Request):
        """Validate that tenant exists and is active"""
        # This would typically involve a database lookup
        # For now, we'll do basic validation
        
        if not tenant_id:
            raise HTTPException(
                status_code=400,
                detail="Tenant ID is required"
            )
        
        # Basic format validation
        if len(tenant_id) < 3 or len(tenant_id) > 100:
            raise HTTPException(
                status_code=400,
                detail="Invalid tenant ID format"
            )
        
        # TODO: Add actual database validation here
        # Example:
        # async with get_db() as db:
        #     tenant = await db.get(Tenant, tenant_id)
        #     if not tenant or not tenant.active:
        #         raise HTTPException(status_code=404, detail="Tenant not found or inactive")
        
        logger.debug("Tenant validated", tenant_id=tenant_id)