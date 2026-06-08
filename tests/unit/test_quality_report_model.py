"""Tests for the QualityReport database model."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from packages.database.models import Base, Project, Novel, Chapter, QualityReport


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


class TestQualityReportModel:
    """Tests for the QualityReport database model."""

    def test_create_quality_report(self, db_session, sample_chapter):
        """Arrange: Prepare quality report data.
        Act: Create a QualityReport instance and add to database.
        Assert: QualityReport is created with correct attributes.
        """
        # Arrange
        quality_report_data = {
            "chapter_id": sample_chapter.id,
            "novel_id": sample_chapter.novel_id,
            "report_type": "auto",  # auto, manual
            "overall_score": 7.5,
            "plot_progression": 8.0,
            "conflict_strength": 7.0,
            "character_consistency": 8.5,
            "style_naturalness": 7.5,
            "dialogue_quality": 8.0,
            "hook_strength": 6.5,
            "continuity_safety": 9.0,
            "cliche_density": 3.0,  # 低分表示套话少
            "main_problems": [
                "中段冲突偏弱",
                "主角主动性不足",
                "章末钩子不够具体"
            ],
            "revision_plan": [
                "增加主角主动试探反派的动作",
                "将信息揭示改成对话冲突",
                "章末留下具体物证"
            ],
            "strengths": [
                "开头引入自然",
                "人物对话符合性格",
                "环境描写具体"
            ],
            "weaknesses": [
                "中间部分节奏拖沓",
                "反派动机不够清晰"
            ],
            "recommendations": [
                "加强中段冲突",
                "补充反派背景"
            ],
            "is_passing": True,  # 是否通过质量检查
            "blocking_issues": [],  # 阻断性问题
            "evaluator_agent": "quality_judge_agent",
            "evaluator_version": "v1.0",
        }

        # Act
        quality_report = QualityReport(**quality_report_data)
        db_session.add(quality_report)
        db_session.commit()
        db_session.refresh(quality_report)

        # Assert
        assert quality_report.id is not None
        assert quality_report.chapter_id == sample_chapter.id
        assert quality_report.novel_id == sample_chapter.novel_id
        assert quality_report.report_type == "auto"
        assert quality_report.overall_score == 7.5
        assert quality_report.plot_progression == 8.0
        assert quality_report.conflict_strength == 7.0
        assert quality_report.character_consistency == 8.5
        assert quality_report.style_naturalness == 7.5
        assert quality_report.dialogue_quality == 8.0
        assert quality_report.hook_strength == 6.5
        assert quality_report.continuity_safety == 9.0
        assert quality_report.cliche_density == 3.0
        assert quality_report.main_problems == [
            "中段冲突偏弱",
            "主角主动性不足",
            "章末钩子不够具体"
        ]
        assert quality_report.revision_plan == [
            "增加主角主动试探反派的动作",
            "将信息揭示改成对话冲突",
            "章末留下具体物证"
        ]
        assert quality_report.strengths == [
            "开头引入自然",
            "人物对话符合性格",
            "环境描写具体"
        ]
        assert quality_report.weaknesses == [
            "中间部分节奏拖沓",
            "反派动机不够清晰"
        ]
        assert quality_report.recommendations == [
            "加强中段冲突",
            "补充反派背景"
        ]
        assert quality_report.is_passing == True
        assert quality_report.blocking_issues == []
        assert quality_report.evaluator_agent == "quality_judge_agent"
        assert quality_report.evaluator_version == "v1.0"
        assert quality_report.created_at is not None

    def test_quality_report_belongs_to_chapter(self, db_session, sample_chapter):
        """Arrange: Create quality report with chapter.
        Act: Query quality report.
        Assert: QualityReport has correct chapter relationship.
        """
        # Arrange
        quality_report = QualityReport(
            chapter_id=sample_chapter.id,
            novel_id=sample_chapter.novel_id,
            report_type="manual",
            overall_score=6.0,
            is_passing=False
        )
        db_session.add(quality_report)
        db_session.commit()
        db_session.refresh(quality_report)

        # Act
        retrieved_quality_report = db_session.query(QualityReport).filter(QualityReport.id == quality_report.id).first()

        # Assert
        assert retrieved_quality_report.chapter_id == sample_chapter.id
        assert retrieved_quality_report.chapter.title == "Test Chapter"

    def test_quality_report_default_values(self, db_session, sample_chapter):
        """Arrange: Create quality report with minimal data.
        Act: Add to database.
        Assert: Default values are set correctly.
        """
        # Arrange
        quality_report = QualityReport(
            chapter_id=sample_chapter.id,
            novel_id=sample_chapter.novel_id,
            report_type="auto"
        )

        # Act
        db_session.add(quality_report)
        db_session.commit()
        db_session.refresh(quality_report)

        # Assert
        assert quality_report.overall_score is None
        assert quality_report.plot_progression is None
        assert quality_report.conflict_strength is None
        assert quality_report.character_consistency is None
        assert quality_report.style_naturalness is None
        assert quality_report.dialogue_quality is None
        assert quality_report.hook_strength is None
        assert quality_report.continuity_safety is None
        assert quality_report.cliche_density is None
        assert quality_report.main_problems is None
        assert quality_report.revision_plan is None
        assert quality_report.strengths is None
        assert quality_report.weaknesses is None
        assert quality_report.recommendations is None
        assert quality_report.is_passing == False
        assert quality_report.blocking_issues is None
        assert quality_report.evaluator_agent is None
        assert quality_report.evaluator_version is None
        assert quality_report.created_at is not None

    def test_quality_report_repr(self, db_session, sample_chapter):
        """Arrange: Create a quality report.
        Act: Get string representation.
        Assert: Repr contains overall_score and is_passing.
        """
        # Arrange
        quality_report = QualityReport(
            chapter_id=sample_chapter.id,
            novel_id=sample_chapter.novel_id,
            report_type="auto",
            overall_score=8.5,
            is_passing=True
        )
        db_session.add(quality_report)
        db_session.commit()
        db_session.refresh(quality_report)

        # Act
        repr_str = repr(quality_report)

        # Assert
        assert "8.5" in repr_str
        assert "True" in repr_str
