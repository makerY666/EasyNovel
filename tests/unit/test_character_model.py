"""Tests for the Character database model."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from packages.database.models import Base, Project, Novel, Character


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


class TestCharacterModel:
    """Tests for the Character database model."""

    def test_create_character(self, db_session, sample_novel):
        """Arrange: Prepare character data.
        Act: Create a Character instance and add to database.
        Assert: Character is created with correct attributes.
        """
        # Arrange
        character_data = {
            "novel_id": sample_novel.id,
            "name": "李明",
            "role": "protagonist",  # protagonist, antagonist, supporting, minor
            "public_goal": "寻找失踪的妹妹",
            "hidden_desire": "证明自己不是废物",
            "fear": "再次失去重要的人",
            "relationship_to_protagonist": "自己",
            "current_knowledge": ["知道妹妹失踪与公司有关"],
            "secrets": ["其实是富二代"],
            "voice_style": {
                "sentence_length": "short",
                "tone": "冷静、压抑、偶尔讽刺",
                "taboo_words": ["他妈的", "草"]
            },
            "physical_description": "身高180cm，短发，眼神锐利",
            "personality_traits": ["聪明", "固执", "重感情"],
            "background_story": "普通家庭出身，妹妹失踪后开始调查",
            "skills": ["黑客技术", "格斗术"],
            "weaknesses": ["过于冲动", "不信任他人"],
        }

        # Act
        character = Character(**character_data)
        db_session.add(character)
        db_session.commit()
        db_session.refresh(character)

        # Assert
        assert character.id is not None
        assert character.novel_id == sample_novel.id
        assert character.name == "李明"
        assert character.role == "protagonist"
        assert character.public_goal == "寻找失踪的妹妹"
        assert character.hidden_desire == "证明自己不是废物"
        assert character.fear == "再次失去重要的人"
        assert character.relationship_to_protagonist == "自己"
        assert character.current_knowledge == ["知道妹妹失踪与公司有关"]
        assert character.secrets == ["其实是富二代"]
        assert character.voice_style is not None
        assert character.voice_style["tone"] == "冷静、压抑、偶尔讽刺"
        assert character.physical_description == "身高180cm，短发，眼神锐利"
        assert character.personality_traits == ["聪明", "固执", "重感情"]
        assert character.background_story == "普通家庭出身，妹妹失踪后开始调查"
        assert character.skills == ["黑客技术", "格斗术"]
        assert character.weaknesses == ["过于冲动", "不信任他人"]
        assert character.created_at is not None
        assert character.updated_at is not None

    def test_character_belongs_to_novel(self, db_session, sample_novel):
        """Arrange: Create character with novel.
        Act: Query character.
        Assert: Character has correct novel relationship.
        """
        # Arrange
        character = Character(
            novel_id=sample_novel.id,
            name="Test Character",
            role="supporting"
        )
        db_session.add(character)
        db_session.commit()
        db_session.refresh(character)

        # Act
        retrieved_character = db_session.query(Character).filter(Character.id == character.id).first()

        # Assert
        assert retrieved_character.novel_id == sample_novel.id
        assert retrieved_character.novel.title == "Test Novel"

    def test_character_default_values(self, db_session, sample_novel):
        """Arrange: Create character with minimal data.
        Act: Add to database.
        Assert: Default values are set correctly.
        """
        # Arrange
        character = Character(novel_id=sample_novel.id, name="Minimal Character")

        # Act
        db_session.add(character)
        db_session.commit()
        db_session.refresh(character)

        # Assert
        assert character.role is None
        assert character.public_goal is None
        assert character.hidden_desire is None
        assert character.fear is None
        assert character.relationship_to_protagonist is None
        assert character.current_knowledge is None
        assert character.secrets is None
        assert character.voice_style is None
        assert character.physical_description is None
        assert character.personality_traits is None
        assert character.background_story is None
        assert character.skills is None
        assert character.weaknesses is None
        assert character.created_at is not None
        assert character.updated_at is not None

    def test_character_repr(self, db_session, sample_novel):
        """Arrange: Create a character.
        Act: Get string representation.
        Assert: Repr contains character name and role.
        """
        # Arrange
        character = Character(
            novel_id=sample_novel.id,
            name="Repr Character",
            role="antagonist"
        )
        db_session.add(character)
        db_session.commit()
        db_session.refresh(character)

        # Act
        repr_str = repr(character)

        # Assert
        assert "Repr Character" in repr_str
        assert "antagonist" in repr_str
