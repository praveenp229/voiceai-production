"""
Admin API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
import structlog

from app.core.database import get_db

logger = structlog.get_logger(__name__)

router = APIRouter()


class AdminResponse(BaseModel):
    message: str


@router.get("/health", response_model=AdminResponse)
async def admin_health(db: AsyncSession = Depends(get_db)):
    """Admin health check"""
    return AdminResponse(message="Admin API healthy")