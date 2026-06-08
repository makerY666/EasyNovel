"""Tests for the TimelineEvent database model."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from packages.database.models import Base, Project, Novel, Chapter, TimelineEvent


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


@pytest.fixture
def sample_chapter(db_session, sample_novel):
    """Create a sample chapter for testing."""
    chapter = Chapter(
        novel_id=sample_novel.id,
        chapter_number=1,
        title="Test Chapter"
    )
    db_session.add(chapter)
    db_session.commit()
    db_session.refresh(chapter)
    return chapter


class TestTimelineEventModel:
    """Tests for the TimelineEvent database model."""

    def test_create_timeline_event(self, db_session, sample_chapter):
        """Arrange: Prepare timeline event data.
        Act: Create a TimelineEvent instance and add to database.
        Assert: TimelineEvent is created with correct attributes.
        """
        # Arrange
        event_data = {
            "chapter_id": sample_chapter.id,
            "novel_id": sample_chapter.novel_id,
            "date_in_story": "第一天晚上",
            "location": "城市街道",
            "events": [
                "主角发现异常信号来自旧服务器",
                "女主第一次隐瞒自己认识反派"
            ],
            "state_changes": [
                "主角获得线索A",
                "反派知道主角已经接近真相"
            ],
            "duration": "2小时",
            "weather": "下雨",
            "importance": "high",  # high, medium, low
        }

        # Act
        event = TimelineEvent(**event_data)
        db_session.add(event)
        db_session.commit()
        db_session.refresh(event)

        # Assert
        assert event.id is not None
        assert event.chapter_id == sample_chapter.id
        assert event.novel_id == sample_chapter.novel_id
        assert event.date_in_story == "第一天晚上"
        assert event.location == "城市街道"
        assert event.events == [
            "主角发现异常信号来自旧服务器",
            "女主第一次隐瞒自己认识反派"
        ]
        assert event.state_changes == [
            "主角获得线索A",
            "反派知道主角已经接近真相"
        ]
        assert event.duration == "2小时"
        assert event.weather == "下雨"
        assert event.importance == "high"
        assert event.created_at is not None
        assert event.updated_at is not None

    def test_timeline_event_belongs_to_chapter(self, db_session, sample_chapter):
        """Arrange: Create timeline event with chapter.
        Act: Query timeline event.
        Assert: TimelineEvent has correct chapter relationship.
        """
        # Arrange
        event = TimelineEvent(
            chapter_id=sample_chapter.id,
            novel_id=sample_chapter.novel_id,
            date_in_story="第二天早上",
            location="学校",
            events=["上课"]
        )
        db_session.add(event)
        db_session.commit()
        db_session.refresh(event)

        # Act
        retrieved_event = db_session.query(TimelineEvent).filter(TimelineEvent.id == event.id).first()

        # Assert
        assert retrieved_event.chapter_id == sample_chapter.id
        assert retrieved_event.chapter.title == "Test Chapter"

    def test_timeline_event_default_values(self, db_session, sample_chapter):
        """Arrange: Create timeline event with minimal data.
        Act: Add to database.
        Assert: Default values are set correctly.
        """
        # Arrange
        event = TimelineEvent(
            chapter_id=sample_chapter.id,
            novel_id=sample_chapter.novel_id,
            date_in_story="第三天",
            location="家里"
        )

        # Act
        db_session.add(event)
        db_session.commit()
        db_session.refresh(event)

        # Assert
        assert event.events is None
        assert event.state_changes is None
        assert event.duration is None
        assert event.weather is None
        assert event.importance is None
        assert event.created_at is not None
        assert event.updated_at is not None

    def test_timeline_event_repr(self, db_session, sample_chapter):
        """Arrange: Create a timeline event.
        Act: Get string representation.
        Assert: Repr contains date and location.
        """
        # Arrange
        event = TimelineEvent(
            chapter_id=sample_chapter.id,
            novel_id=sample_chapter.novel_id,
            date_in_story="第四天",
            location="图书馆"
        )
        db_session.add(event)
        db_session.commit()
        db_session.refresh(event)

        # Act
        repr_str = repr(event)

        # Assert
        assert "第四天" in repr_str
        assert "图书馆" in repr_str
