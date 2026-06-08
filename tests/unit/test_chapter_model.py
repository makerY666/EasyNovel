"""Tests for the Chapter database model."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from packages.database.models import Base, Project, Novel, Chapter


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


class TestChapterModel:
    """Tests for the Chapter database model."""

    def test_create_chapter(self, db_session, sample_novel):
        """Arrange: Prepare chapter data.
        Act: Create a Chapter instance and add to database.
        Assert: Chapter is created with correct attributes.
        """
        # Arrange
        chapter_data = {
            "novel_id": sample_novel.id,
            "chapter_number": 1,
            "title": "第一章：开始",
            "summary": "主角出场，介绍世界观",
            "target_word_count": 3000,
            "current_word_count": 0,
            "status": "planned",  # planned, drafting, editing, polished, final
            "chapter_card": {
                "chapter_goal": "介绍主角和世界观",
                "opening_hook": "深夜，主角独自走在空无一人的街道上",
                "main_conflict": "主角发现异常现象",
                "turning_point": "决定调查真相",
                "emotional_shift": "从平静到紧张",
                "new_information": ["世界并非表面那样"],
                "foreshadowing": ["旧收音机自动响起"],
                "ending_hook": "收音机传来神秘声音",
                "must_not_violate": ["主角不能突然获得超能力"]
            },
            "pov": "主角",  # point of view
            "time_in_story": "第一天晚上",
            "location": "城市街道",
        }

        # Act
        chapter = Chapter(**chapter_data)
        db_session.add(chapter)
        db_session.commit()
        db_session.refresh(chapter)

        # Assert
        assert chapter.id is not None
        assert chapter.novel_id == sample_novel.id
        assert chapter.chapter_number == 1
        assert chapter.title == "第一章：开始"
        assert chapter.summary == "主角出场，介绍世界观"
        assert chapter.target_word_count == 3000
        assert chapter.current_word_count == 0
        assert chapter.status == "planned"
        assert chapter.chapter_card is not None
        assert chapter.chapter_card["chapter_goal"] == "介绍主角和世界观"
        assert chapter.pov == "主角"
        assert chapter.time_in_story == "第一天晚上"
        assert chapter.location == "城市街道"
        assert chapter.created_at is not None
        assert chapter.updated_at is not None

    def test_chapter_belongs_to_novel(self, db_session, sample_novel):
        """Arrange: Create chapter with novel.
        Act: Query chapter.
        Assert: Chapter has correct novel relationship.
        """
        # Arrange
        chapter = Chapter(
            novel_id=sample_novel.id,
            chapter_number=1,
            title="Test Chapter"
        )
        db_session.add(chapter)
        db_session.commit()
        db_session.refresh(chapter)

        # Act
        retrieved_chapter = db_session.query(Chapter).filter(Chapter.id == chapter.id).first()

        # Assert
        assert retrieved_chapter.novel_id == sample_novel.id
        assert retrieved_chapter.novel.title == "Test Novel"

    def test_chapter_default_values(self, db_session, sample_novel):
        """Arrange: Create chapter with minimal data.
        Act: Add to database.
        Assert: Default values are set correctly.
        """
        # Arrange
        chapter = Chapter(novel_id=sample_novel.id, chapter_number=1)

        # Act
        db_session.add(chapter)
        db_session.commit()
        db_session.refresh(chapter)

        # Assert
        assert chapter.title is None
        assert chapter.summary is None
        assert chapter.target_word_count is None
        assert chapter.current_word_count == 0
        assert chapter.status == "planned"
        assert chapter.chapter_card is None
        assert chapter.pov is None
        assert chapter.time_in_story is None
        assert chapter.location is None
        assert chapter.created_at is not None
        assert chapter.updated_at is not None

    def test_chapter_repr(self, db_session, sample_novel):
        """Arrange: Create a chapter.
        Act: Get string representation.
        Assert: Repr contains chapter number and title.
        """
        # Arrange
        chapter = Chapter(
            novel_id=sample_novel.id,
            chapter_number=5,
            title="Repr Test Chapter"
        )
        db_session.add(chapter)
        db_session.commit()
        db_session.refresh(chapter)

        # Act
        repr_str = repr(chapter)

        # Assert
        assert "5" in repr_str
        assert "Repr Test Chapter" in repr_str
