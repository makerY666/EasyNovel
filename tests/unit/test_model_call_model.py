"""Tests for the ModelCall database model."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from packages.database.models import Base, Project, Novel, Chapter, AgentRun, ModelCall


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


@pytest.fixture
def sample_agent_run(db_session, sample_chapter):
    """Create a sample agent run for testing."""
    agent_run = AgentRun(
        chapter_id=sample_chapter.id,
        novel_id=sample_chapter.novel_id,
        agent_name="test_agent",
        status="completed"
    )
    db_session.add(agent_run)
    db_session.commit()
    db_session.refresh(agent_run)
    return agent_run


class TestModelCallModel:
    """Tests for the ModelCall database model."""

    def test_create_model_call(self, db_session, sample_agent_run):
        """Arrange: Prepare model call data.
        Act: Create a ModelCall instance and add to database.
        Assert: ModelCall is created with correct attributes.
        """
        # Arrange
        model_call_data = {
            "agent_run_id": sample_agent_run.id,
            "model_name": "deepseek-v4-pro",
            "model_version": "2026-06-01",
            "prompt": "请为第一章创建章节卡",
            "prompt_tokens": 1500,
            "completion_tokens": 800,
            "total_tokens": 2300,
            "cost_usd": 0.0023,
            "latency_ms": 2500,
            "temperature": 0.7,
            "top_p": 0.9,
            "max_tokens": 2000,
            "status": "success",  # success, error, timeout
            "error_message": None,
            "response": {
                "chapter_card": {
                    "chapter_goal": "介绍主角和世界观",
                    "opening_hook": "深夜，主角独自走在空无一人的街道上"
                }
            },
            "call_metadata": {
                "request_id": "req_12345",
                "endpoint": "https://api.deepseek.com/v1/chat/completions"
            },
        }

        # Act
        model_call = ModelCall(**model_call_data)
        db_session.add(model_call)
        db_session.commit()
        db_session.refresh(model_call)

        # Assert
        assert model_call.id is not None
        assert model_call.agent_run_id == sample_agent_run.id
        assert model_call.model_name == "deepseek-v4-pro"
        assert model_call.model_version == "2026-06-01"
        assert model_call.prompt == "请为第一章创建章节卡"
        assert model_call.prompt_tokens == 1500
        assert model_call.completion_tokens == 800
        assert model_call.total_tokens == 2300
        assert model_call.cost_usd == 0.0023
        assert model_call.latency_ms == 2500
        assert model_call.temperature == 0.7
        assert model_call.top_p == 0.9
        assert model_call.max_tokens == 2000
        assert model_call.status == "success"
        assert model_call.error_message is None
        assert model_call.response is not None
        assert model_call.response["chapter_card"]["chapter_goal"] == "介绍主角和世界观"
        assert model_call.call_metadata is not None
        assert model_call.call_metadata["request_id"] == "req_12345"
        assert model_call.created_at is not None

    def test_model_call_belongs_to_agent_run(self, db_session, sample_agent_run):
        """Arrange: Create model call with agent run.
        Act: Query model call.
        Assert: ModelCall has correct agent_run relationship.
        """
        # Arrange
        model_call = ModelCall(
            agent_run_id=sample_agent_run.id,
            model_name="deepseek-v4-flash",
            status="success"
        )
        db_session.add(model_call)
        db_session.commit()
        db_session.refresh(model_call)

        # Act
        retrieved_model_call = db_session.query(ModelCall).filter(ModelCall.id == model_call.id).first()

        # Assert
        assert retrieved_model_call.agent_run_id == sample_agent_run.id
        assert retrieved_model_call.agent_run.agent_name == "test_agent"

    def test_model_call_default_values(self, db_session, sample_agent_run):
        """Arrange: Create model call with minimal data.
        Act: Add to database.
        Assert: Default values are set correctly.
        """
        # Arrange
        model_call = ModelCall(
            agent_run_id=sample_agent_run.id,
            model_name="test_model"
        )

        # Act
        db_session.add(model_call)
        db_session.commit()
        db_session.refresh(model_call)

        # Assert
        assert model_call.model_version is None
        assert model_call.prompt is None
        assert model_call.prompt_tokens is None
        assert model_call.completion_tokens is None
        assert model_call.total_tokens is None
        assert model_call.cost_usd is None
        assert model_call.latency_ms is None
        assert model_call.temperature is None
        assert model_call.top_p is None
        assert model_call.max_tokens is None
        assert model_call.status == "pending"
        assert model_call.error_message is None
        assert model_call.response is None
        assert model_call.call_metadata is None
        assert model_call.created_at is not None

    def test_model_call_repr(self, db_session, sample_agent_run):
        """Arrange: Create a model call.
        Act: Get string representation.
        Assert: Repr contains model_name and status.
        """
        # Arrange
        model_call = ModelCall(
            agent_run_id=sample_agent_run.id,
            model_name="repr_model",
            status="error"
        )
        db_session.add(model_call)
        db_session.commit()
        db_session.refresh(model_call)

        # Act
        repr_str = repr(model_call)

        # Assert
        assert "repr_model" in repr_str
        assert "error" in repr_str
