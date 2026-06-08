"""Tests for database models."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from packages.database.models import Base, Project


@pytest.fixture
def db_session():
    """Create an in-memory SQLite database session for testing."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


class TestProjectModel:
    """Tests for the Project database model."""

    def test_create_project(self, db_session):
        """Arrange: Prepare project data.
        Act: Create a Project instance and add to database.
        Assert: Project is created with correct attributes.
        """
        # Arrange
        project_data = {
            "name": "Test Novel Project",
            "description": "A test novel project",
            "target_platform": "番茄小说",
            "target_audience": "18-35岁男性",
            "expected_word_count": 200000,
            "protagonist_type": "普通人逆袭",
            "pleasure_points": ["升级打怪", "装逼打脸"],
            "forbidden_tropes": ["后宫", "无脑爽"],
            "reference_style": "辰东",
        }

        # Act
        project = Project(**project_data)
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        # Assert
        assert project.id is not None
        assert project.name == "Test Novel Project"
        assert project.description == "A test novel project"
        assert project.target_platform == "番茄小说"
        assert project.target_audience == "18-35岁男性"
        assert project.expected_word_count == 200000
        assert project.protagonist_type == "普通人逆袭"
        assert project.pleasure_points == ["升级打怪", "装逼打脸"]
        assert project.forbidden_tropes == ["后宫", "无脑爽"]
        assert project.reference_style == "辰东"
        assert project.created_at is not None
        assert project.updated_at is not None

    def test_project_name_uniqueness(self, db_session):
        """Arrange: Create first project.
        Act: Try to create second project with same name.
        Assert: Should raise integrity error.
        """
        # Arrange
        project1 = Project(name="Unique Name", description="First project")
        db_session.add(project1)
        db_session.commit()

        # Act & Assert
        project2 = Project(name="Unique Name", description="Second project")
        db_session.add(project2)
        with pytest.raises(Exception):  # SQLAlchemy integrity error
            db_session.commit()

    def test_project_default_values(self, db_session):
        """Arrange: Create project with minimal data.
        Act: Add to database.
        Assert: Default values are set correctly.
        """
        # Arrange
        project = Project(name="Minimal Project")

        # Act
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        # Assert
        assert project.description is None
        assert project.target_platform is None
        assert project.target_audience is None
        assert project.expected_word_count is None
        assert project.protagonist_type is None
        assert project.pleasure_points is None
        assert project.forbidden_tropes is None
        assert project.reference_style is None
        assert project.created_at is not None
        assert project.updated_at is not None

    def test_project_repr(self, db_session):
        """Arrange: Create a project.
        Act: Get string representation.
        Assert: Repr contains project name and id.
        """
        # Arrange
        project = Project(name="Repr Test Project")
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        # Act
        repr_str = repr(project)

        # Assert
        assert "Repr Test Project" in repr_str
        assert str(project.id) in repr_str
