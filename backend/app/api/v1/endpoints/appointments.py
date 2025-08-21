"""
Appointment management API endpoints
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
import structlog

from app.core.database import get_db

logger = structlog.get_logger(__name__)

router = APIRouter()


class AppointmentResponse(BaseModel):
    id: str
    tenant_id: str
    patient_name: str
    scheduled_datetime: str
    status: str


@router.get("/", response_model=List[AppointmentResponse])
async def list_appointments(db: AsyncSession = Depends(get_db)):
    """List appointments"""
    return []  # Placeholder


@router.get("/{appointment_id}", response_model=AppointmentResponse)
async def get_appointment(
    appointment_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get appointment by ID"""
    raise HTTPException(status_code=404, detail="Appointment not found")