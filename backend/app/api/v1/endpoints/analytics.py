"""
Analytics API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
import structlog

from app.core.database import get_db

logger = structlog.get_logger(__name__)

router = APIRouter()


class AnalyticsResponse(BaseModel):
    total_calls: int
    total_tenants: int


@router.get("/overview", response_model=AnalyticsResponse)
async def get_analytics_overview(db: AsyncSession = Depends(get_db)):
    """Get analytics overview"""
    return AnalyticsResponse(total_calls=0, total_tenants=0)