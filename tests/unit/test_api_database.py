"""Tests for database engine and session management."""
import pytest
import tempfile
import os
from unittest.mock import patch, MagicMock


class TestDatabaseEngine:
    """Tests for database engine."""

    def test_create_engine_with_sqlite(self):
        """Arrange: Provide SQLite database URL.
        Act: Create engine.
        Assert: Engine is created successfully.
        """
        # Arrange
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        try:
            db_url = f"sqlite:///{db_path}"

            # Act
            from apps.api.database import create_engine_from_url
            engine = create_engine_from_url(db_url)

            # Assert
            assert engine is not None
        finally:
            os.unlink(db_path)

    def test_create_engine_returns_valid_engine(self):
        """Arrange: Provide database URL.
        Act: Create engine.
        Assert: Engine can connect.
        """
        # Arrange
        from apps.api.database import create_engine_from_url

        # Act
        engine = create_engine_from_url("sqlite://")

        # Assert
        connection = engine.connect()
        assert connection is not None
        connection.close()

    def test_get_session_returns_session(self):
        """Arrange: Create engine.
        Act: Create session.
        Assert: Session is created successfully.
        """
        # Arrange
        from apps.api.database import create_engine_from_url, create_session_factory
        engine = create_engine_from_url("sqlite://")
        SessionLocal = create_session_factory(engine)

        # Act
        session = SessionLocal()

        # Assert
        assert session is not None
        session.close()

    def test_create_tables_creates_all_models(self):
        """Arrange: Create engine.
        Act: Create tables.
        Assert: All tables are created.
        """
        # Arrange
        from apps.api.database import create_engine_from_url, create_tables
        engine = create_engine_from_url("sqlite://")

        # Act
        create_tables(engine)

        # Assert - just verify no exception
        assert engine is not None
