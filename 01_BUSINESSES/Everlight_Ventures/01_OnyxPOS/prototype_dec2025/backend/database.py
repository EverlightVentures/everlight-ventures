"""
Database initialization and session management
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from contextlib import contextmanager
from models import Base
import config

# Import all models to ensure they're registered with Base.metadata
import models_inventory_advanced  # noqa: F401


# Create engine
engine = create_engine(
    config.Config.SQLALCHEMY_DATABASE_URI,
    **config.Config.SQLALCHEMY_ENGINE_OPTIONS
)

# Create session factory
session_factory = sessionmaker(bind=engine)
Session = scoped_session(session_factory)


def init_db():
    """Initialize database - create all tables"""
    Base.metadata.create_all(bind=engine)
    print("✅ Database initialized successfully!")


def drop_db():
    """Drop all tables - CAREFUL!"""
    Base.metadata.drop_all(bind=engine)
    print("⚠️  All tables dropped!")


@contextmanager
def get_session():
    """Provide a transactional scope for database operations"""
    session = Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_current_tenant_id():
    """
    Get current tenant ID from request context
    This will be set by middleware based on JWT token or subdomain
    """
    from flask import g
    return getattr(g, "tenant_id", None)


if __name__ == "__main__":
    # Initialize database when run directly
    print("Initializing database...")
    init_db()
