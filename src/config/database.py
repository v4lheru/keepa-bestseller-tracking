"""
Database connection and session management for Supabase PostgreSQL.
Handles async database operations with proper connection pooling.
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import MetaData

from .settings import settings
from .logging import get_logger

logger = get_logger(__name__)


class Base(DeclarativeBase):
    """Base class for all database models."""
    metadata = MetaData()


# Create async engine with connection pooling
engine = create_async_engine(
    settings.database_url,
    echo=not settings.is_production,  # Log SQL queries in development
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # Validate connections before use
    pool_recycle=3600,   # Recycle connections every hour
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=True,
    autocommit=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency function to get database session.
    Used with FastAPI dependency injection.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error("Database session error", error=str(e))
            raise
        finally:
            await session.close()


async def init_database() -> None:
    """Initialize database connection and verify connectivity."""
    try:
        async with engine.begin() as conn:
            # Test connection
            await conn.execute("SELECT 1")
            logger.info("Database connection established successfully")
            
    except Exception as e:
        logger.error("Failed to connect to database", error=str(e))
        raise


async def close_database() -> None:
    """Close database connections gracefully."""
    try:
        await engine.dispose()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error("Error closing database connections", error=str(e))


class DatabaseManager:
    """Database manager for handling connections and sessions."""
    
    def __init__(self):
        self.engine = engine
        self.session_factory = AsyncSessionLocal
        self.logger = get_logger(self.__class__.__name__)
    
    async def get_session(self) -> AsyncSession:
        """Get a new database session."""
        return self.session_factory()
    
    async def execute_query(self, query: str, params: dict = None) -> list:
        """Execute a raw SQL query and return results."""
        async with self.session_factory() as session:
            try:
                result = await session.execute(query, params or {})
                await session.commit()
                return result.fetchall()
            except Exception as e:
                await session.rollback()
                self.logger.error("Query execution failed", query=query, error=str(e))
                raise
    
    async def health_check(self) -> bool:
        """Check database connectivity."""
        try:
            async with self.session_factory() as session:
                await session.execute("SELECT 1")
                return True
        except Exception as e:
            self.logger.error("Database health check failed", error=str(e))
            return False


# Global database manager instance
db_manager = DatabaseManager()
