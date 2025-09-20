"""
Dependency injection setup for FastAPI
"""

from functools import lru_cache
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi import Depends
import redis

from app.config import get_settings


# Database setup
@lru_cache()
def get_database_engine():
    """Get database engine"""
    settings = get_settings()
    return create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20
    )


@lru_cache()
def get_session_maker():
    """Get database session maker"""
    engine = get_database_engine()
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    """Dependency to get database session"""
    SessionLocal = get_session_maker()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Redis setup
@lru_cache()
def get_redis_client():
    """Get Redis client"""
    settings = get_settings()
    return redis.from_url(settings.redis_url, decode_responses=True)


def get_redis() -> redis.Redis:
    """Dependency to get Redis client"""
    return get_redis_client()