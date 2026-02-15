"""Shared SQLAlchemy base and database initialization."""

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


async def init_db(url: str | None = None) -> None:
    """Initialize the async database engine and session factory.

    Creates all tables defined via Base.metadata.
    """
    global _engine, _session_factory

    if _engine is not None:
        return

    settings = get_settings()
    db_url = url or settings.database_url

    _engine = create_async_engine(db_url, echo=settings.debug, pool_pre_ping=True)
    _session_factory = async_sessionmaker(
        _engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Import all models so metadata is populated before create_all
    import app.db.models  # noqa: F401

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Dispose of the engine and release all connections."""
    global _engine, _session_factory

    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the configured session factory.

    Raises RuntimeError if init_db() has not been called.
    """
    if _session_factory is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _session_factory
