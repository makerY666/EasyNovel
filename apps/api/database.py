"""Database engine and session management for AI Novel Studio."""
from sqlalchemy import Engine, create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker


def create_engine_from_url(database_url: str) -> Engine:
    """Create a SQLAlchemy engine from a database URL.

    Args:
        database_url: Database connection URL.

    Returns:
        SQLAlchemy Engine instance.
    """
    connect_args = {}
    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    return create_engine(database_url, connect_args=connect_args, echo=False)


def create_session_factory(engine: Engine) -> sessionmaker:
    """Create a session factory for database operations.

    Args:
        engine: SQLAlchemy Engine instance.

    Returns:
        Session factory.
    """
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_tables(engine: Engine) -> None:
    """Create all database tables.

    Args:
        engine: SQLAlchemy Engine instance.
    """
    from packages.database.models import Base
    Base.metadata.create_all(bind=engine)
    _apply_lightweight_sqlite_migrations(engine)


def _apply_lightweight_sqlite_migrations(engine: Engine) -> None:
    """Apply tiny local-only SQLite migrations for existing developer DBs."""
    if engine.dialect.name != "sqlite":
        return

    inspector = inspect(engine)
    if "chapters" not in inspector.get_table_names():
        return
    chapter_columns = {column["name"] for column in inspector.get_columns("chapters")}
    if "current_version_id" not in chapter_columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE chapters ADD COLUMN current_version_id INTEGER"))
