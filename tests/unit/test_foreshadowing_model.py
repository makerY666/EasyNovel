"""Tests for the Foreshadowing database model."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from packages.database.models import Base, Project, Novel, Foreshadowing


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


@pytest.fixture
def sample_novel(db_session, sample_project):
    """Create a sample novel for testing."""
    novel = Novel(
        project_id=sample_project.id,
        title="Test Novel",
        genre="Fantasy"
    )
    db_session.add(novel)
    db_session.commit()
    db_session.refresh(novel)
    return novel


class TestForeshadowingModel:
    """Tests for the Foreshadowing database model."""

    def test_create_foreshadowing(self, db_session, sample_novel):
        """Arrange: Prepare foreshadowing data.
        Act: Create a Foreshadowing instance and add to database.
        Assert: Foreshadowing is created with correct attributes.
        """
        # Arrange
        foreshadowing_data = {
            "novel_id": sample_novel.id,
            "foreshadowing_id": "f023",
            "introduced_at_chapter": 7,
            "content": "旧收音机只在凌晨2:17自动响起",
            "intended_payoff_chapter": 42,
            "intended_payoff_content": "揭示它是信号接收器",
            "status": "open",  # open, resolved, abandoned
            "related_characters": ["主角", "管理员"],
            "importance": "high",  # high, medium, low
            "notes": "关键伏笔，需要持续跟踪",
        }

        # Act
        foreshadowing = Foreshadowing(**foreshadowing_data)
        db_session.add(foreshadowing)
        db_session.commit()
        db_session.refresh(foreshadowing)

        # Assert
        assert foreshadowing.id is not None
        assert foreshadowing.novel_id == sample_novel.id
        assert foreshadowing.foreshadowing_id == "f023"
        assert foreshadowing.introduced_at_chapter == 7
        assert foreshadowing.content == "旧收音机只在凌晨2:17自动响起"
        assert foreshadowing.intended_payoff_chapter == 42
        assert foreshadowing.intended_payoff_content == "揭示它是信号接收器"
        assert foreshadowing.status == "open"
        assert foreshadowing.related_characters == ["主角", "管理员"]
        assert foreshadowing.importance == "high"
        assert foreshadowing.notes == "关键伏笔，需要持续跟踪"
        assert foreshadowing.created_at is not None
        assert foreshadowing.updated_at is not None

    def test_foreshadowing_belongs_to_novel(self, db_session, sample_novel):
        """Arrange: Create foreshadowing with novel.
        Act: Query foreshadowing.
        Assert: Foreshadowing has correct novel relationship.
        """
        # Arrange
        foreshadowing = Foreshadowing(
            novel_id=sample_novel.id,
            foreshadowing_id="f024",
            introduced_at_chapter=1,
            content="测试伏笔",
            status="open"
        )
        db_session.add(foreshadowing)
        db_session.commit()
        db_session.refresh(foreshadowing)

        # Act
        retrieved_foreshadowing = db_session.query(Foreshadowing).filter(Foreshadowing.id == foreshadowing.id).first()

        # Assert
        assert retrieved_foreshadowing.novel_id == sample_novel.id
        assert retrieved_foreshadowing.novel.title == "Test Novel"

    def test_foreshadowing_default_values(self, db_session, sample_novel):
        """Arrange: Create foreshadowing with minimal data.
        Act: Add to database.
        Assert: Default values are set correctly.
        """
        # Arrange
        foreshadowing = Foreshadowing(
            novel_id=sample_novel.id,
            foreshadowing_id="f025",
            introduced_at_chapter=2,
            content="测试伏笔"
        )

        # Act
        db_session.add(foreshadowing)
        db_session.commit()
        db_session.refresh(foreshadowing)

        # Assert
        assert foreshadowing.intended_payoff_chapter is None
        assert foreshadowing.intended_payoff_content is None
        assert foreshadowing.status == "open"
        assert foreshadowing.related_characters is None
        assert foreshadowing.importance is None
        assert foreshadowing.notes is None
        assert foreshadowing.created_at is not None
        assert foreshadowing.updated_at is not None

    def test_foreshadowing_repr(self, db_session, sample_novel):
        """Arrange: Create a foreshadowing.
        Act: Get string representation.
        Assert: Repr contains foreshadowing_id and status.
        """
        # Arrange
        foreshadowing = Foreshadowing(
            novel_id=sample_novel.id,
            foreshadowing_id="f026",
            introduced_at_chapter=3,
            content="测试伏笔",
            status="resolved"
        )
        db_session.add(foreshadowing)
        db_session.commit()
        db_session.refresh(foreshadowing)

        # Act
        repr_str = repr(foreshadowing)

        # Assert
        assert "f026" in repr_str
        assert "resolved" in repr_str
