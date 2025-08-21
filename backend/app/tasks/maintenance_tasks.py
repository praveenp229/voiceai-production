"""
Maintenance tasks for Celery
Periodic cleanup and maintenance operations
"""

import asyncio
from typing import Dict
from datetime import datetime, timezone, timedelta
import structlog

from app.tasks.celery_app import celery_app
from app.core.database import AsyncSessionLocal

logger = structlog.get_logger(__name__)


@celery_app.task(
    bind=True,
    name="cleanup_old_call_logs",
    queue="maintenance"
)
def cleanup_old_call_logs(self, days_to_keep: int = 90):
    """
    Cleanup old call logs (periodic task)
    
    Args:
        self: Celery task instance
        days_to_keep: Number of days to keep call logs
        
    Returns:
        Dict with cleanup results
    """
    try:
        logger.info("Starting call logs cleanup", task_id=self.request.id, days_to_keep=days_to_keep)
        
        # Run async cleanup
        result = asyncio.run(_cleanup_old_call_logs_internal(days_to_keep, self.request.id))
        
        logger.info(
            "Call logs cleanup completed",
            task_id=self.request.id,
            deleted_logs=result.get("deleted_logs", 0)
        )
        
        return result
        
    except Exception as e:
        logger.error("Call logs cleanup failed", error=str(e), task_id=self.request.id)
        return {
            "success": False,
            "error": str(e),
            "deleted_logs": 0
        }


@celery_app.task(
    bind=True,
    name="cleanup_expired_sessions",
    queue="maintenance"
)
def cleanup_expired_sessions(self):
    """
    Cleanup expired sessions and temporary data
    """
    try:
        logger.info("Starting expired sessions cleanup", task_id=self.request.id)
        
        # Run async cleanup
        result = asyncio.run(_cleanup_expired_sessions_internal(self.request.id))
        
        return result
        
    except Exception as e:
        logger.error("Expired sessions cleanup failed", error=str(e))
        return {
            "success": False,
            "error": str(e),
            "cleaned_sessions": 0
        }


@celery_app.task(
    bind=True,
    name="generate_usage_reports",
    queue="maintenance"
)
def generate_usage_reports(self):
    """
    Generate usage reports for tenants
    """
    try:
        logger.info("Starting usage reports generation", task_id=self.request.id)
        
        # Run async report generation
        result = asyncio.run(_generate_usage_reports_internal(self.request.id))
        
        return result
        
    except Exception as e:
        logger.error("Usage reports generation failed", error=str(e))
        return {
            "success": False,
            "error": str(e),
            "reports_generated": 0
        }


@celery_app.task(
    bind=True,
    name="health_check_services",
    queue="maintenance"
)
def health_check_services(self):
    """
    Health check for external services (OpenAI, Twilio, etc.)
    """
    try:
        logger.info("Starting services health check", task_id=self.request.id)
        
        # Run async health checks
        result = asyncio.run(_health_check_services_internal(self.request.id))
        
        return result
        
    except Exception as e:
        logger.error("Services health check failed", error=str(e))
        return {
            "success": False,
            "error": str(e),
            "healthy_services": 0,
            "unhealthy_services": 1
        }


# Internal async functions

async def _cleanup_old_call_logs_internal(days_to_keep: int, task_id: str) -> Dict:
    """Internal call logs cleanup function"""
    
    async with AsyncSessionLocal() as db:
        try:
            from sqlalchemy import select, delete
            from app.models.call_log import CallLog
            
            # Calculate cutoff date
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
            
            # Count logs to delete
            count_query = select(CallLog).where(CallLog.created_at < cutoff_date)
            count_result = await db.execute(count_query)
            logs_to_delete = len(list(count_result.scalars()))
            
            if logs_to_delete > 0:
                # Delete old logs
                delete_stmt = delete(CallLog).where(CallLog.created_at < cutoff_date)
                await db.execute(delete_stmt)
                await db.commit()
                
                logger.info(
                    "Old call logs deleted",
                    deleted_count=logs_to_delete,
                    cutoff_date=cutoff_date.isoformat(),
                    task_id=task_id
                )
            else:
                logger.info("No old call logs to delete", task_id=task_id)
            
            return {
                "success": True,
                "deleted_logs": logs_to_delete,
                "cutoff_date": cutoff_date.isoformat(),
                "task_id": task_id
            }
            
        except Exception as e:
            await db.rollback()
            logger.error("Failed to cleanup call logs", error=str(e))
            raise


async def _cleanup_expired_sessions_internal(task_id: str) -> Dict:
    """Internal session cleanup function"""
    
    try:
        # Mock session cleanup - in production this would clean Redis sessions, temp files, etc.
        logger.info("Cleaning expired sessions", task_id=task_id)
        
        # Simulate cleanup
        await asyncio.sleep(1)
        cleaned_sessions = 5  # Mock number
        
        return {
            "success": True,
            "cleaned_sessions": cleaned_sessions,
            "task_id": task_id
        }
        
    except Exception as e:
        logger.error("Failed to cleanup expired sessions", error=str(e))
        raise


async def _generate_usage_reports_internal(task_id: str) -> Dict:
    """Internal usage reports generation function"""
    
    async with AsyncSessionLocal() as db:
        try:
            from sqlalchemy import select, func
            from app.models.tenant import Tenant
            from app.models.call_log import CallLog
            
            # Get all active tenants
            tenants_result = await db.execute(select(Tenant).where(Tenant.active == True))
            tenants = tenants_result.scalars().all()
            
            reports_generated = 0
            
            for tenant in tenants:
                # Generate basic usage stats
                calls_query = select(func.count(CallLog.id)).where(
                    CallLog.tenant_id == tenant.id,
                    CallLog.created_at >= datetime.now(timezone.utc) - timedelta(days=30)
                )
                calls_result = await db.execute(calls_query)
                monthly_calls = calls_result.scalar() or 0
                
                # Mock report generation - in production this would create actual reports
                logger.info(
                    "Generated usage report",
                    tenant_id=tenant.id,
                    monthly_calls=monthly_calls,
                    task_id=task_id
                )
                
                reports_generated += 1
            
            return {
                "success": True,
                "reports_generated": reports_generated,
                "task_id": task_id
            }
            
        except Exception as e:
            logger.error("Failed to generate usage reports", error=str(e))
            raise


async def _health_check_services_internal(task_id: str) -> Dict:
    """Internal services health check function"""
    
    try:
        from app.core.config import settings
        import httpx
        
        healthy_services = 0
        unhealthy_services = 0
        service_status = {}
        
        # Check OpenAI API
        if settings.OPENAI_API_KEY:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(
                        "https://api.openai.com/v1/models",
                        headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"}
                    )
                    if response.status_code == 200:
                        service_status["openai"] = "healthy"
                        healthy_services += 1
                    else:
                        service_status["openai"] = "unhealthy"
                        unhealthy_services += 1
            except Exception:
                service_status["openai"] = "unhealthy"
                unhealthy_services += 1
        
        # Check Twilio API (mock)
        if settings.TWILIO_ACCOUNT_SID:
            # Mock Twilio health check
            service_status["twilio"] = "healthy"
            healthy_services += 1
        
        # Check database connectivity
        async with AsyncSessionLocal() as db:
            try:
                await db.execute("SELECT 1")
                service_status["database"] = "healthy"
                healthy_services += 1
            except Exception:
                service_status["database"] = "unhealthy"
                unhealthy_services += 1
        
        logger.info(
            "Services health check completed",
            healthy=healthy_services,
            unhealthy=unhealthy_services,
            task_id=task_id
        )
        
        return {
            "success": unhealthy_services == 0,
            "healthy_services": healthy_services,
            "unhealthy_services": unhealthy_services,
            "service_status": service_status,
            "task_id": task_id
        }
        
    except Exception as e:
        logger.error("Failed to check services health", error=str(e))
        raise