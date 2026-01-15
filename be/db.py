"""SQLAlchemy 2.x database setup using psycopg3 and pgvector.

This module defines the async engine and session factory but does not
hard-code any connection credentials.
"""

from __future__ import annotations

from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from .config import settings


engine: AsyncEngine = create_async_engine(settings.db.url, echo=False, future=True)

AsyncSessionMaker = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI-friendly async session dependency.

    Usage:
        async def endpoint(session: AsyncSession = Depends(get_session)):
            ...
    """

    async with AsyncSessionMaker() as session:
        yield session
