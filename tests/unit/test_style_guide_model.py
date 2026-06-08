"""Tests for the StyleGuide database model."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from packages.database.models import Base, Project, Novel, StyleGuide


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


class TestStyleGuideModel:
    """Tests for the StyleGuide database model."""

    def test_create_style_guide(self, db_session, sample_novel):
        """Arrange: Prepare style guide data.
        Act: Create a StyleGuide instance and add to database.
        Assert: StyleGuide is created with correct attributes.
        """
        # Arrange
        style_guide_data = {
            "novel_id": sample_novel.id,
            "name": "网文风格指南",
            "description": "适用于番茄小说平台的文风指南",
            "narrative_pov": "第三人称有限视角",  # 第一人称, 第三人称有限, 第三人称全知
            "sentence_length_preference": "medium",  # short, medium, long
            "dialogue_density": "high",  # low, medium, high
            "description_intensity": "medium",  # sparse, medium, detailed
            "rhythm_preference": "fast",  # slow, medium, fast
            "forbidden_words": ["他妈的", "草", "卧槽"],
            "forbidden_phrases": [
                "他不知道的是……",
                "命运的齿轮开始转动。",
                "空气仿佛凝固了。",
                "这一刻，他终于明白……",
                "眼神中闪过一丝复杂。",
                "心中涌起一股难以言喻的情绪。",
                "大脑飞速运转。",
                "事情远没有这么简单。",
                "真正的考验才刚刚开始。"
            ],
            "preferred_sentence_patterns": [
                "短句为主，长句为辅",
                "动作描写具体化",
                "对话简洁有力"
            ],
            "character_voice_guidelines": {
                "主角": "简洁、直接、偶尔幽默",
                "反派": "冷静、优雅、暗藏锋芒",
                "配角": "各有特色，避免同质化"
            },
            "platform_specific_rules": {
                "番茄小说": "每章2000-3000字，章末必须有钩子",
                "起点中文网": "每章3000-4000字，注重世界观构建"
            },
            "is_active": True,
        }

        # Act
        style_guide = StyleGuide(**style_guide_data)
        db_session.add(style_guide)
        db_session.commit()
        db_session.refresh(style_guide)

        # Assert
        assert style_guide.id is not None
        assert style_guide.novel_id == sample_novel.id
        assert style_guide.name == "网文风格指南"
        assert style_guide.description == "适用于番茄小说平台的文风指南"
        assert style_guide.narrative_pov == "第三人称有限视角"
        assert style_guide.sentence_length_preference == "medium"
        assert style_guide.dialogue_density == "high"
        assert style_guide.description_intensity == "medium"
        assert style_guide.rhythm_preference == "fast"
        assert style_guide.forbidden_words == ["他妈的", "草", "卧槽"]
        assert len(style_guide.forbidden_phrases) == 9
        assert "他不知道的是……" in style_guide.forbidden_phrases
        assert style_guide.preferred_sentence_patterns == [
            "短句为主，长句为辅",
            "动作描写具体化",
            "对话简洁有力"
        ]
        assert style_guide.character_voice_guidelines is not None
        assert style_guide.character_voice_guidelines["主角"] == "简洁、直接、偶尔幽默"
        assert style_guide.platform_specific_rules is not None
        assert style_guide.platform_specific_rules["番茄小说"] == "每章2000-3000字，章末必须有钩子"
        assert style_guide.is_active == True
        assert style_guide.created_at is not None
        assert style_guide.updated_at is not None

    def test_style_guide_belongs_to_novel(self, db_session, sample_novel):
        """Arrange: Create style guide with novel.
        Act: Query style guide.
        Assert: StyleGuide has correct novel relationship.
        """
        # Arrange
        style_guide = StyleGuide(
            novel_id=sample_novel.id,
            name="测试风格指南",
            description="测试用"
        )
        db_session.add(style_guide)
        db_session.commit()
        db_session.refresh(style_guide)

        # Act
        retrieved_style_guide = db_session.query(StyleGuide).filter(StyleGuide.id == style_guide.id).first()

        # Assert
        assert retrieved_style_guide.novel_id == sample_novel.id
        assert retrieved_style_guide.novel.title == "Test Novel"

    def test_style_guide_default_values(self, db_session, sample_novel):
        """Arrange: Create style guide with minimal data.
        Act: Add to database.
        Assert: Default values are set correctly.
        """
        # Arrange
        style_guide = StyleGuide(
            novel_id=sample_novel.id,
            name="最小风格指南"
        )

        # Act
        db_session.add(style_guide)
        db_session.commit()
        db_session.refresh(style_guide)

        # Assert
        assert style_guide.description is None
        assert style_guide.narrative_pov is None
        assert style_guide.sentence_length_preference is None
        assert style_guide.dialogue_density is None
        assert style_guide.description_intensity is None
        assert style_guide.rhythm_preference is None
        assert style_guide.forbidden_words is None
        assert style_guide.forbidden_phrases is None
        assert style_guide.preferred_sentence_patterns is None
        assert style_guide.character_voice_guidelines is None
        assert style_guide.platform_specific_rules is None
        assert style_guide.is_active == True
        assert style_guide.created_at is not None
        assert style_guide.updated_at is not None

    def test_style_guide_repr(self, db_session, sample_novel):
        """Arrange: Create a style guide.
        Act: Get string representation.
        Assert: Repr contains name and is_active.
        """
        # Arrange
        style_guide = StyleGuide(
            novel_id=sample_novel.id,
            name="Repr风格指南",
            is_active=False
        )
        db_session.add(style_guide)
        db_session.commit()
        db_session.refresh(style_guide)

        # Act
        repr_str = repr(style_guide)

        # Assert
        assert "Repr风格指南" in repr_str
        assert "False" in repr_str
