"""
Tenant management API endpoints
CRUD operations for tenant management and configuration
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
import structlog

from app.core.database import get_db
from app.services.tenant_service import TenantService

logger = structlog.get_logger(__name__)

router = APIRouter()


class TenantCreate(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    timezone: str = "America/Chicago"


class TenantResponse(BaseModel):
    id: str
    name: str
    email: str
    phone: Optional[str]
    api_key: str
    timezone: str
    active: bool


@router.post("/", response_model=TenantResponse)
async def create_tenant(
    tenant_data: TenantCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new tenant"""
    try:
        tenant = await TenantService.create_tenant(
            db=db,
            name=tenant_data.name,
            email=tenant_data.email,
            phone=tenant_data.phone,
            timezone=tenant_data.timezone
        )
        
        return TenantResponse(
            id=tenant.id,
            name=tenant.name,
            email=tenant.email,
            phone=tenant.phone,
            api_key=tenant.api_key,
            timezone=tenant.timezone,
            active=tenant.active
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Failed to create tenant", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create tenant")


@router.get("/", response_model=List[TenantResponse])
async def list_tenants(
    active_only: bool = Query(True),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """List all tenants"""
    tenants = await TenantService.list_tenants(
        db=db,
        active_only=active_only,
        limit=limit,
        offset=offset
    )
    
    return [
        TenantResponse(
            id=tenant.id,
            name=tenant.name,
            email=tenant.email,
            phone=tenant.phone,
            api_key=tenant.api_key,
            timezone=tenant.timezone,
            active=tenant.active
        )
        for tenant in tenants
    ]


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get tenant by ID"""
    tenant = await TenantService.get_tenant_by_id(db, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    return TenantResponse(
        id=tenant.id,
        name=tenant.name,
        email=tenant.email,
        phone=tenant.phone,
        api_key=tenant.api_key,
        timezone=tenant.timezone,
        active=tenant.active
    )