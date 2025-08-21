"""
Customer management API endpoints
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
import structlog

from app.core.database import get_db

logger = structlog.get_logger(__name__)

router = APIRouter()


class CustomerResponse(BaseModel):
    id: str
    tenant_id: str
    name: str
    phone: str
    total_calls: str
    

@router.get("/", response_model=List[CustomerResponse])
async def list_customers(
    tenant_id: str = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """List customers"""
    return []  # Placeholder


@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get customer by ID"""
    raise HTTPException(status_code=404, detail="Customer not found")