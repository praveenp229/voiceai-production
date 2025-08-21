"""
Async database configuration using SQLAlchemy 2.0
Supports both SQLite (development) and PostgreSQL (production)
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import StaticPool
import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)

# Create async engine
if settings.DATABASE_URL.startswith("sqlite"):
    # SQLite configuration for development
    engine = create_async_engine(
        settings.DATABASE_URL.replace("sqlite://", "sqlite+aiosqlite://"),
        echo=settings.DEBUG,
        poolclass=StaticPool,
        connect_args={
            "check_same_thread": False,
        }
    )
else:
    # PostgreSQL configuration for production
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
        pool_pre_ping=True,  # Verify connections before use
        pool_recycle=3600,   # Recycle connections after 1 hour
    )

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=True,
    autocommit=False,
)

# Base class for all models
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get database session
    
    Usage:
        @app.get("/")
        async def read_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database tables"""
    try:
        logger.info("Initializing database...")
        
        # Import all models to register them with Base
        from app.models import tenant, customer, call_log, system_config, voice_config, appointment
        
        # Create all tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("✅ Database tables created successfully")
        
    except Exception as e:
        logger.error("❌ Failed to initialize database", error=str(e))
        raise


async def close_db() -> None:
    """Close database connections"""
    await engine.dispose()
    logger.info("Database connections closed")