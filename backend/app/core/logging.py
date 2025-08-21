"""
Structured logging configuration using structlog
Provides JSON logging for production and readable logging for development
"""

import sys
import logging
from typing import Any, Dict
import structlog
from structlog.types import EventDict, Processor

from app.core.config import settings


def add_app_context(logger, method_name: str, event_dict: EventDict) -> EventDict:
    """Add application context to log events"""
    event_dict["app"] = "voiceai"
    event_dict["version"] = "2.0.0"
    event_dict["environment"] = settings.ENVIRONMENT
    return event_dict


def censor_sensitive_data(logger, method_name: str, event_dict: EventDict) -> EventDict:
    """Remove sensitive information from logs"""
    sensitive_keys = {
        "password", "token", "api_key", "secret", "auth",
        "credit_card", "ssn", "phone", "email"
    }
    
    def _censor_dict(data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively censor sensitive data in dictionaries"""
        if not isinstance(data, dict):
            return data
            
        censored = {}
        for key, value in data.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                censored[key] = "[REDACTED]"
            elif isinstance(value, dict):
                censored[key] = _censor_dict(value)
            elif isinstance(value, list):
                censored[key] = [_censor_dict(item) if isinstance(item, dict) else item for item in value]
            else:
                censored[key] = value
        return censored
    
    return _censor_dict(event_dict)


def setup_logging() -> None:
    """Configure structured logging for the application"""
    
    # Configure processors
    processors: list[Processor] = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="ISO"),
        structlog.processors.StackInfoRenderer(),
        add_app_context,
        censor_sensitive_data,
    ]
    
    if settings.is_development:
        # Pretty console output for development
        processors.extend([
            structlog.processors.CallsiteParameterAdder(
                parameters=[structlog.processors.CallsiteParameter.FUNC_NAME]
            ),
            structlog.dev.ConsoleRenderer(colors=True)
        ])
    else:
        # JSON output for production
        processors.extend([
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer()
        ])
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        context_class=dict,
        cache_logger_on_first_use=True,
    )
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.DEBUG if settings.DEBUG else logging.INFO,
    )
    
    # Set log levels for noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


def get_logger(name: str = None) -> structlog.BoundLogger:
    """Get a configured logger instance"""
    return structlog.get_logger(name) if name else structlog.get_logger()