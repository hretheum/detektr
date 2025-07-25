"""Database configuration and connection management."""

import os
import sys
from typing import AsyncGenerator

import structlog
from models import Base
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

logger = structlog.get_logger()

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL")

# Enhanced debugging
logger.info(
    "database_config_check",
    database_url_present=bool(DATABASE_URL),
    database_url_length=len(DATABASE_URL) if DATABASE_URL else 0,
    database_url_preview=DATABASE_URL[:50] + "..."
    if DATABASE_URL and len(DATABASE_URL) > 50
    else DATABASE_URL,
    all_env_vars=list(os.environ.keys()),
    postgres_password_present="POSTGRES_PASSWORD" in os.environ,
    postgres_user_present="POSTGRES_USER" in os.environ,
)

if not DATABASE_URL:
    logger.error(
        "database_url_missing",
        env_vars=dict(os.environ),
        cwd=os.getcwd(),
        python_path=sys.path,
    )
    raise ValueError(
        "DATABASE_URL environment variable is required. Available env vars: "
        + ", ".join(os.environ.keys())
    )

# If DATABASE_URL contains localhost, replace with postgres for container networking
if "localhost" in DATABASE_URL:
    original_url = DATABASE_URL
    DATABASE_URL = DATABASE_URL.replace("localhost", "postgres")
    logger.info("database_url_adjusted", original=original_url, adjusted=DATABASE_URL)

# Create async engine with better error handling
try:
    engine = create_async_engine(
        DATABASE_URL,
        echo=os.getenv("SQL_ECHO", "false").lower() == "true",
        pool_pre_ping=True,
        poolclass=NullPool,  # Disable connection pooling for simplicity
    )
    logger.info(
        "database_engine_created",
        url=DATABASE_URL[:50] + "..." if len(DATABASE_URL) > 50 else DATABASE_URL,
    )
except Exception as e:
    logger.error(
        "database_engine_creation_failed",
        error=str(e),
        error_type=type(e).__name__,
        database_url=DATABASE_URL[:50] + "..."
        if DATABASE_URL and len(DATABASE_URL) > 50
        else DATABASE_URL,
    )
    raise

# Create async session factory
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Initialize database - create tables if needed."""
    try:
        logger.info(
            "database_init_starting",
            database_url=DATABASE_URL[:50] + "..."
            if DATABASE_URL and len(DATABASE_URL) > 50
            else DATABASE_URL,
        )
        async with engine.begin() as conn:
            # Note: In production, use Alembic migrations instead
            # This is just for development/demo
            await conn.run_sync(Base.metadata.create_all)
            logger.info("database_initialized")
    except Exception as e:
        logger.error(
            "database_initialization_failed",
            error=str(e),
            error_type=type(e).__name__,
            database_url=DATABASE_URL[:50] + "..."
            if DATABASE_URL and len(DATABASE_URL) > 50
            else DATABASE_URL,
            full_traceback=True,
        )
        raise
