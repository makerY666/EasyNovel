"""Tests for the Novel database model."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from packages.database.models import Base, Project, Novel


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


@pytest.fixture
def sample_project(db_session):
    """Create a sample project for testing."""
    project = Project(name="Test Project", description="A test project")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    return project


class TestNovelModel:
    """Tests for the Novel database model."""

    def test_create_novel(self, db_session, sample_project):
        """Arrange: Prepare novel data.
        Act: Create a Novel instance and add to database.
        Assert: Novel is created with correct attributes.
        """
        # Arrange
        novel_data = {
            "project_id": sample_project.id,
            "title": "测试小说标题",
            "subtitle": "第一章：开始",
            "synopsis": "这是一个测试小说的简介",
            "genre": "玄幻",
            "sub_genre": "东方玄幻",
            "target_word_count": 100000,
            "current_word_count": 0,
            "status": "planning",  # planning, writing, editing, completed
            "style_guide": "简洁明快，节奏紧凑",
            "taboo_words": ["他妈的", "草"],
        }

        # Act
        novel = Novel(**novel_data)
        db_session.add(novel)
        db_session.commit()
        db_session.refresh(novel)

        # Assert
        assert novel.id is not None
        assert novel.project_id == sample_project.id
        assert novel.title == "测试小说标题"
        assert novel.subtitle == "第一章：开始"
        assert novel.synopsis == "这是一个测试小说的简介"
        assert novel.genre == "玄幻"
        assert novel.sub_genre == "东方玄幻"
        assert novel.target_word_count == 100000
        assert novel.current_word_count == 0
        assert novel.status == "planning"
        assert novel.style_guide == "简洁明快，节奏紧凑"
        assert novel.taboo_words == ["他妈的", "草"]
        assert novel.created_at is not None
        assert novel.updated_at is not None

    def test_novel_belongs_to_project(self, db_session, sample_project):
        """Arrange: Create novel with project.
        Act: Query novel.
        Assert: Novel has correct project relationship.
        """
        # Arrange
        novel = Novel(
            project_id=sample_project.id,
            title="Project Novel",
            genre="Fantasy"
        )
        db_session.add(novel)
        db_session.commit()
        db_session.refresh(novel)

        # Act
        retrieved_novel = db_session.query(Novel).filter(Novel.id == novel.id).first()

        # Assert
        assert retrieved_novel.project_id == sample_project.id
        assert retrieved_novel.project.name == "Test Project"

    def test_novel_default_values(self, db_session, sample_project):
        """Arrange: Create novel with minimal data.
        Act: Add to database.
        Assert: Default values are set correctly.
        """
        # Arrange
        novel = Novel(project_id=sample_project.id, title="Minimal Novel")

        # Act
        db_session.add(novel)
        db_session.commit()
        db_session.refresh(novel)

        # Assert
        assert novel.subtitle is None
        assert novel.synopsis is None
        assert novel.genre is None
        assert novel.sub_genre is None
        assert novel.target_word_count is None
        assert novel.current_word_count == 0
        assert novel.status == "planning"
        assert novel.style_guide is None
        assert novel.taboo_words is None
        assert novel.created_at is not None
        assert novel.updated_at is not None

    def test_novel_repr(self, db_session, sample_project):
        """Arrange: Create a novel.
        Act: Get string representation.
        Assert: Repr contains novel title and id.
        """
        # Arrange
        novel = Novel(project_id=sample_project.id, title="Repr Test Novel")
        db_session.add(novel)
        db_session.commit()
        db_session.refresh(novel)

        # Act
        repr_str = repr(novel)

        # Assert
        assert "Repr Test Novel" in repr_str
        assert str(novel.id) in repr_str
