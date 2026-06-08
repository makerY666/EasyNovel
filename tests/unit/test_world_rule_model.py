"""Tests for the WorldRule database model."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from packages.database.models import Base, Project, Novel, WorldRule


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


class TestWorldRuleModel:
    """Tests for the WorldRule database model."""

    def test_create_world_rule(self, db_session, sample_novel):
        """Arrange: Prepare world rule data.
        Act: Create a WorldRule instance and add to database.
        Assert: WorldRule is created with correct attributes.
        """
        # Arrange
        rule_data = {
            "novel_id": sample_novel.id,
            "rule_id": "rule_001",
            "content": "能力不能凭空升级，必须通过代价触发。",
            "priority": "high",  # high, medium, low
            "category": "power_system",  # power_system, world_setting, character_rule, etc.
            "is_active": True,
            "created_by": "story_bible_agent",
            "notes": "这是核心设定，不可随意修改",
        }

        # Act
        rule = WorldRule(**rule_data)
        db_session.add(rule)
        db_session.commit()
        db_session.refresh(rule)

        # Assert
        assert rule.id is not None
        assert rule.novel_id == sample_novel.id
        assert rule.rule_id == "rule_001"
        assert rule.content == "能力不能凭空升级，必须通过代价触发。"
        assert rule.priority == "high"
        assert rule.category == "power_system"
        assert rule.is_active == True
        assert rule.created_by == "story_bible_agent"
        assert rule.notes == "这是核心设定，不可随意修改"
        assert rule.created_at is not None
        assert rule.updated_at is not None

    def test_world_rule_belongs_to_novel(self, db_session, sample_novel):
        """Arrange: Create world rule with novel.
        Act: Query world rule.
        Assert: WorldRule has correct novel relationship.
        """
        # Arrange
        rule = WorldRule(
            novel_id=sample_novel.id,
            rule_id="rule_002",
            content="魔法需要消耗精神力",
            priority="medium"
        )
        db_session.add(rule)
        db_session.commit()
        db_session.refresh(rule)

        # Act
        retrieved_rule = db_session.query(WorldRule).filter(WorldRule.id == rule.id).first()

        # Assert
        assert retrieved_rule.novel_id == sample_novel.id
        assert retrieved_rule.novel.title == "Test Novel"

    def test_world_rule_default_values(self, db_session, sample_novel):
        """Arrange: Create world rule with minimal data.
        Act: Add to database.
        Assert: Default values are set correctly.
        """
        # Arrange
        rule = WorldRule(
            novel_id=sample_novel.id,
            rule_id="rule_003",
            content="测试规则"
        )

        # Act
        db_session.add(rule)
        db_session.commit()
        db_session.refresh(rule)

        # Assert
        assert rule.priority is None
        assert rule.category is None
        assert rule.is_active == True
        assert rule.created_by is None
        assert rule.notes is None
        assert rule.created_at is not None
        assert rule.updated_at is not None

    def test_world_rule_repr(self, db_session, sample_novel):
        """Arrange: Create a world rule.
        Act: Get string representation.
        Assert: Repr contains rule_id and priority.
        """
        # Arrange
        rule = WorldRule(
            novel_id=sample_novel.id,
            rule_id="rule_004",
            content="测试规则",
            priority="low"
        )
        db_session.add(rule)
        db_session.commit()
        db_session.refresh(rule)

        # Act
        repr_str = repr(rule)

        # Assert
        assert "rule_004" in repr_str
        assert "low" in repr_str
