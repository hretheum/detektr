"""Database configuration and connection management."""

import os
from typing import AsyncGenerator

import structlog
from models import Base
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

logger = structlog.get_logger()

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL")

# If DATABASE_URL not provided, construct it from individual components
if not DATABASE_URL:
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
    POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB = os.getenv("POSTGRES_DB", "detektor")
    POSTGRES_USER = os.getenv("POSTGRES_USER", "detektor")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
    DETEKTOR_DB_PASSWORD = os.getenv("DETEKTOR_DB_PASSWORD")

    logger.info(
        "password_debug",
        postgres_password=POSTGRES_PASSWORD[:3] + "..." if POSTGRES_PASSWORD else None,
        detektor_db_password=DETEKTOR_DB_PASSWORD[:3] + "..."
        if DETEKTOR_DB_PASSWORD
        else None,
        postgres_password_len=len(POSTGRES_PASSWORD) if POSTGRES_PASSWORD else 0,
        detektor_db_password_len=len(DETEKTOR_DB_PASSWORD)
        if DETEKTOR_DB_PASSWORD
        else 0,
    )

    # Use DETEKTOR_DB_PASSWORD if POSTGRES_PASSWORD is the default
    if POSTGRES_PASSWORD == "detektor_pass" and DETEKTOR_DB_PASSWORD:
        logger.warning(
            "Using DETEKTOR_DB_PASSWORD instead of default POSTGRES_PASSWORD"
        )
        POSTGRES_PASSWORD = DETEKTOR_DB_PASSWORD

    if not POSTGRES_PASSWORD:
        logger.error(
            "postgres_password_missing",
            available_env_vars=list(os.environ.keys()),
            postgres_host=POSTGRES_HOST,
            postgres_port=POSTGRES_PORT,
            postgres_db=POSTGRES_DB,
            postgres_user=POSTGRES_USER,
        )
        raise ValueError(
            "POSTGRES_PASSWORD environment variable is required. "
            "Available env vars: " + ", ".join(os.environ.keys())
        )

    # Construct DATABASE_URL from components
    DATABASE_URL = (
        f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@"
        f"{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    )
    logger.info(
        "database_url_constructed",
        postgres_host=POSTGRES_HOST,
        postgres_port=POSTGRES_PORT,
        postgres_db=POSTGRES_DB,
        postgres_user=POSTGRES_USER,
        postgres_password_length=len(POSTGRES_PASSWORD),
    )

# Enhanced debugging
logger.info(
    "database_config_check",
    database_url_source="env" if os.getenv("DATABASE_URL") else "constructed",
    database_url_length=len(DATABASE_URL) if DATABASE_URL else 0,
    database_url_preview=DATABASE_URL[:50] + "..."
    if DATABASE_URL and len(DATABASE_URL) > 50
    else DATABASE_URL,
    all_env_vars=list(os.environ.keys()),
    postgres_password_present="POSTGRES_PASSWORD" in os.environ,
    postgres_user_present="POSTGRES_USER" in os.environ,
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
