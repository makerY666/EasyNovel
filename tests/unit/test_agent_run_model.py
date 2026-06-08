"""Tests for the AgentRun database model."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from packages.database.models import Base, Project, Novel, Chapter, AgentRun


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


class TestAgentRunModel:
    """Tests for the AgentRun database model."""

    def test_create_agent_run(self, db_session, sample_chapter):
        """Arrange: Prepare agent run data.
        Act: Create an AgentRun instance and add to database.
        Assert: AgentRun is created with correct attributes.
        """
        # Arrange
        agent_run_data = {
            "chapter_id": sample_chapter.id,
            "novel_id": sample_chapter.novel_id,
            "agent_name": "chapter_planner_agent",
            "agent_version": "v1.0",
            "prompt_version": "v1.2",
            "model_name": "deepseek-v4-pro",
            "input_data": {
                "chapter_number": 1,
                "context_pack": {"summary": "上一章摘要"},
                "chapter_goal": "介绍主角"
            },
            "output_data": {
                "chapter_card": {
                    "chapter_goal": "介绍主角和世界观",
                    "opening_hook": "深夜，主角独自走在空无一人的街道上"
                }
            },
            "status": "completed",  # pending, running, completed, failed
            "start_time": "2026-06-08T10:00:00",
            "end_time": "2026-06-08T10:05:00",
            "duration_seconds": 300,
            "input_tokens": 1500,
            "output_tokens": 800,
            "total_tokens": 2300,
            "cost_usd": 0.0023,
            "error_message": None,
            "run_metadata": {
                "temperature": 0.7,
                "top_p": 0.9,
                "max_tokens": 2000
            },
        }

        # Act
        agent_run = AgentRun(**agent_run_data)
        db_session.add(agent_run)
        db_session.commit()
        db_session.refresh(agent_run)

        # Assert
        assert agent_run.id is not None
        assert agent_run.chapter_id == sample_chapter.id
        assert agent_run.novel_id == sample_chapter.novel_id
        assert agent_run.agent_name == "chapter_planner_agent"
        assert agent_run.agent_version == "v1.0"
        assert agent_run.prompt_version == "v1.2"
        assert agent_run.model_name == "deepseek-v4-pro"
        assert agent_run.input_data is not None
        assert agent_run.input_data["chapter_number"] == 1
        assert agent_run.output_data is not None
        assert agent_run.output_data["chapter_card"]["chapter_goal"] == "介绍主角和世界观"
        assert agent_run.status == "completed"
        assert agent_run.start_time == "2026-06-08T10:00:00"
        assert agent_run.end_time == "2026-06-08T10:05:00"
        assert agent_run.duration_seconds == 300
        assert agent_run.input_tokens == 1500
        assert agent_run.output_tokens == 800
        assert agent_run.total_tokens == 2300
        assert agent_run.cost_usd == 0.0023
        assert agent_run.error_message is None
        assert agent_run.run_metadata is not None
        assert agent_run.run_metadata["temperature"] == 0.7
        assert agent_run.created_at is not None

    def test_agent_run_belongs_to_chapter(self, db_session, sample_chapter):
        """Arrange: Create agent run with chapter.
        Act: Query agent run.
        Assert: AgentRun has correct chapter relationship.
        """
        # Arrange
        agent_run = AgentRun(
            chapter_id=sample_chapter.id,
            novel_id=sample_chapter.novel_id,
            agent_name="draft_writer_agent",
            status="completed"
        )
        db_session.add(agent_run)
        db_session.commit()
        db_session.refresh(agent_run)

        # Act
        retrieved_agent_run = db_session.query(AgentRun).filter(AgentRun.id == agent_run.id).first()

        # Assert
        assert retrieved_agent_run.chapter_id == sample_chapter.id
        assert retrieved_agent_run.chapter.title == "Test Chapter"

    def test_agent_run_default_values(self, db_session, sample_chapter):
        """Arrange: Create agent run with minimal data.
        Act: Add to database.
        Assert: Default values are set correctly.
        """
        # Arrange
        agent_run = AgentRun(
            chapter_id=sample_chapter.id,
            novel_id=sample_chapter.novel_id,
            agent_name="test_agent"
        )

        # Act
        db_session.add(agent_run)
        db_session.commit()
        db_session.refresh(agent_run)

        # Assert
        assert agent_run.agent_version is None
        assert agent_run.prompt_version is None
        assert agent_run.model_name is None
        assert agent_run.input_data is None
        assert agent_run.output_data is None
        assert agent_run.status == "pending"
        assert agent_run.start_time is None
        assert agent_run.end_time is None
        assert agent_run.duration_seconds is None
        assert agent_run.input_tokens is None
        assert agent_run.output_tokens is None
        assert agent_run.total_tokens is None
        assert agent_run.cost_usd is None
        assert agent_run.error_message is None
        assert agent_run.run_metadata is None
        assert agent_run.created_at is not None

    def test_agent_run_repr(self, db_session, sample_chapter):
        """Arrange: Create an agent run.
        Act: Get string representation.
        Assert: Repr contains agent_name and status.
        """
        # Arrange
        agent_run = AgentRun(
            chapter_id=sample_chapter.id,
            novel_id=sample_chapter.novel_id,
            agent_name="repr_agent",
            status="failed"
        )
        db_session.add(agent_run)
        db_session.commit()
        db_session.refresh(agent_run)

        # Act
        repr_str = repr(agent_run)

        # Assert
        assert "repr_agent" in repr_str
        assert "failed" in repr_str
