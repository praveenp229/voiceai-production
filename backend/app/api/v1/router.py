"""
Main API router for VoiceAI 2.0
Includes all endpoint modules and sets up API structure
"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    voice,
    voice_async,
    tenants,
    customers,
    appointments,
    admin,
    analytics
)

# Create main API router
api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(
    voice.router,
    prefix="/voice",
    tags=["voice"],
    responses={404: {"description": "Not found"}}
)

api_router.include_router(
    voice_async.router,
    prefix="/voice",
    tags=["voice-async"],
    responses={404: {"description": "Not found"}}
)

api_router.include_router(
    tenants.router,
    prefix="/tenants",
    tags=["tenants"],
    responses={404: {"description": "Not found"}}
)

api_router.include_router(
    customers.router,
    prefix="/customers",
    tags=["customers"],
    responses={404: {"description": "Not found"}}
)

api_router.include_router(
    appointments.router,
    prefix="/appointments",
    tags=["appointments"],
    responses={404: {"description": "Not found"}}
)

api_router.include_router(
    admin.router,
    prefix="/admin",
    tags=["admin"],
    responses={404: {"description": "Not found"}}
)

api_router.include_router(
    analytics.router,
    prefix="/analytics",
    tags=["analytics"],
    responses={404: {"description": "Not found"}}
)