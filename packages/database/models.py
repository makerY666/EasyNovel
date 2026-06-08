"""Database models for AI Novel Studio."""
from datetime import datetime
from typing import List, Optional

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, JSON, func
from sqlalchemy.orm import DeclarativeBase, relationship, relationship


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


class Project(Base):
    """Project model representing a novel project."""
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    target_platform = Column(String(100), nullable=True)  # e.g., 番茄小说, 起点中文网
    target_audience = Column(String(255), nullable=True)  # e.g., 18-35岁男性
    expected_word_count = Column(Integer, nullable=True)  # 预期总字数
    protagonist_type = Column(String(255), nullable=True)  # 主角类型
    pleasure_points = Column(JSON, nullable=True)  # 爽点类型列表
    forbidden_tropes = Column(JSON, nullable=True)  # 禁用套路列表
    reference_style = Column(String(255), nullable=True)  # 参考风格
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    novels = relationship("Novel", back_populates="project")

    def __repr__(self) -> str:
        return f"<Project(id={self.id}, name='{self.name}')>"


class Novel(Base):
    """Novel model representing a single novel within a project."""
    __tablename__ = "novels"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False, index=True)
    subtitle = Column(String(255), nullable=True)
    synopsis = Column(Text, nullable=True)
    genre = Column(String(100), nullable=True)  # e.g., 玄幻, 科幻, 都市
    sub_genre = Column(String(100), nullable=True)  # e.g., 东方玄幻, 未来科幻
    target_word_count = Column(Integer, nullable=True)  # 目标字数
    current_word_count = Column(Integer, default=0, nullable=False)  # 当前字数
    status = Column(String(50), default="planning", nullable=False)  # planning, writing, editing, completed
    style_guide = Column(Text, nullable=True)  # 文风指南
    taboo_words = Column(JSON, nullable=True)  # 禁用词列表
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    project = relationship("Project", back_populates="novels")
    chapters = relationship("Chapter", back_populates="novel")
    characters = relationship("Character", back_populates="novel")
    world_rules = relationship("WorldRule", back_populates="novel")
    timeline_events = relationship("TimelineEvent", back_populates="novel")
    foreshadowings = relationship("Foreshadowing", back_populates="novel")
    style_guides = relationship("StyleGuide", back_populates="novel")
    agent_runs = relationship("AgentRun", back_populates="novel")
    quality_reports = relationship("QualityReport", back_populates="novel")

    def __repr__(self) -> str:
        return f"<Novel(id={self.id}, title='{self.title}')>"


class Chapter(Base):
    """Chapter model representing a single chapter within a novel."""
    __tablename__ = "chapters"

    id = Column(Integer, primary_key=True, index=True)
    novel_id = Column(Integer, ForeignKey("novels.id"), nullable=False, index=True)
    chapter_number = Column(Integer, nullable=False, index=True)
    title = Column(String(255), nullable=True)
    summary = Column(Text, nullable=True)  # 章节摘要
    target_word_count = Column(Integer, nullable=True)  # 目标字数
    current_word_count = Column(Integer, default=0, nullable=False)  # 当前字数
    status = Column(String(50), default="planned", nullable=False)  # planned, drafting, editing, polished, final
    chapter_card = Column(JSON, nullable=True)  # 章节卡（结构化）
    current_version_id = Column(Integer, nullable=True, index=True)
    pov = Column(String(100), nullable=True)  # 视角人物
    time_in_story = Column(String(255), nullable=True)  # 故事内时间
    location = Column(String(255), nullable=True)  # 地点
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    novel = relationship("Novel", back_populates="chapters")
    versions = relationship("ChapterVersion", back_populates="chapter")
    timeline_events = relationship("TimelineEvent", back_populates="chapter")
    agent_runs = relationship("AgentRun", back_populates="chapter")
    quality_reports = relationship("QualityReport", back_populates="chapter")
    character_states = relationship("CharacterState", back_populates="chapter")

    def __repr__(self) -> str:
        return f"<Chapter(id={self.id}, number={self.chapter_number}, title='{self.title}')>"


class ChapterVersion(Base):
    """Versioned chapter content produced by AI or manual editing."""
    __tablename__ = "chapter_versions"

    id = Column(Integer, primary_key=True, index=True)
    chapter_id = Column(Integer, ForeignKey("chapters.id"), nullable=False, index=True)
    novel_id = Column(Integer, ForeignKey("novels.id"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    stage = Column(String(50), nullable=False, index=True)  # draft, polished, manual, final
    content = Column(Text, nullable=False)
    word_count = Column(Integer, default=0, nullable=False)
    source = Column(String(50), default="manual", nullable=False)  # ai, manual, import
    workflow_id = Column(String(100), nullable=True, index=True)
    version_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    chapter = relationship("Chapter", back_populates="versions")
    novel = relationship("Novel")

    def __repr__(self) -> str:
        return (
            f"<ChapterVersion(id={self.id}, chapter_id={self.chapter_id}, "
            f"version={self.version_number}, stage='{self.stage}')>"
        )


class Character(Base):
    """Character model representing a character within a novel."""
    __tablename__ = "characters"

    id = Column(Integer, primary_key=True, index=True)
    novel_id = Column(Integer, ForeignKey("novels.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    role = Column(String(50), nullable=True)  # protagonist, antagonist, supporting, minor
    public_goal = Column(Text, nullable=True)  # 公开目标
    hidden_desire = Column(Text, nullable=True)  # 隐藏欲望
    fear = Column(Text, nullable=True)  # 恐惧
    relationship_to_protagonist = Column(String(255), nullable=True)  # 与主角关系
    current_knowledge = Column(JSON, nullable=True)  # 当前知道什么
    secrets = Column(JSON, nullable=True)  # 秘密
    voice_style = Column(JSON, nullable=True)  # 说话风格
    physical_description = Column(Text, nullable=True)  # 外貌描述
    personality_traits = Column(JSON, nullable=True)  # 性格特征
    background_story = Column(Text, nullable=True)  # 背景故事
    skills = Column(JSON, nullable=True)  # 技能
    weaknesses = Column(JSON, nullable=True)  # 弱点
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    novel = relationship("Novel", back_populates="characters")
    states = relationship("CharacterState", back_populates="character")

    def __repr__(self) -> str:
        return f"<Character(id={self.id}, name='{self.name}', role='{self.role}')>"


class WorldRule(Base):
    """WorldRule model representing a world rule within a novel."""
    __tablename__ = "world_rules"

    id = Column(Integer, primary_key=True, index=True)
    novel_id = Column(Integer, ForeignKey("novels.id"), nullable=False, index=True)
    rule_id = Column(String(100), nullable=False, index=True)  # e.g., rule_001
    content = Column(Text, nullable=False)  # 规则内容
    priority = Column(String(20), nullable=True)  # high, medium, low
    category = Column(String(100), nullable=True)  # power_system, world_setting, character_rule, etc.
    is_active = Column(Boolean, default=True, nullable=False)  # 是否激活
    created_by = Column(String(100), nullable=True)  # 创建者
    notes = Column(Text, nullable=True)  # 备注
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    novel = relationship("Novel", back_populates="world_rules")

    def __repr__(self) -> str:
        return f"<WorldRule(id={self.id}, rule_id='{self.rule_id}', priority='{self.priority}')>"


class TimelineEvent(Base):
    """TimelineEvent model representing a timeline event within a novel."""
    __tablename__ = "timeline_events"

    id = Column(Integer, primary_key=True, index=True)
    chapter_id = Column(Integer, ForeignKey("chapters.id"), nullable=False, index=True)
    novel_id = Column(Integer, ForeignKey("novels.id"), nullable=False, index=True)
    date_in_story = Column(String(255), nullable=False)  # 故事内时间
    location = Column(String(255), nullable=False)  # 地点
    events = Column(JSON, nullable=True)  # 事件列表
    state_changes = Column(JSON, nullable=True)  # 状态变化
    duration = Column(String(100), nullable=True)  # 持续时间
    weather = Column(String(100), nullable=True)  # 天气
    importance = Column(String(20), nullable=True)  # high, medium, low
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    chapter = relationship("Chapter", back_populates="timeline_events")
    novel = relationship("Novel", back_populates="timeline_events")

    def __repr__(self) -> str:
        return f"<TimelineEvent(id={self.id}, date='{self.date_in_story}', location='{self.location}')>"


class Foreshadowing(Base):
    """Foreshadowing model representing a foreshadowing within a novel."""
    __tablename__ = "foreshadowings"

    id = Column(Integer, primary_key=True, index=True)
    novel_id = Column(Integer, ForeignKey("novels.id"), nullable=False, index=True)
    foreshadowing_id = Column(String(100), nullable=False, index=True)  # e.g., f023
    introduced_at_chapter = Column(Integer, nullable=False)  # 引入章节
    content = Column(Text, nullable=False)  # 伏笔内容
    intended_payoff_chapter = Column(Integer, nullable=True)  # 计划回收章节
    intended_payoff_content = Column(Text, nullable=True)  # 计划回收内容
    status = Column(String(20), default="open", nullable=False)  # open, resolved, abandoned
    related_characters = Column(JSON, nullable=True)  # 相关人物
    importance = Column(String(20), nullable=True)  # high, medium, low
    notes = Column(Text, nullable=True)  # 备注
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    novel = relationship("Novel", back_populates="foreshadowings")

    def __repr__(self) -> str:
        return f"<Foreshadowing(id={self.id}, foreshadowing_id='{self.foreshadowing_id}', status='{self.status}')>"


class StyleGuide(Base):
    """StyleGuide model representing a style guide within a novel."""
    __tablename__ = "style_guides"

    id = Column(Integer, primary_key=True, index=True)
    novel_id = Column(Integer, ForeignKey("novels.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)  # 风格指南名称
    description = Column(Text, nullable=True)  # 描述
    narrative_pov = Column(String(100), nullable=True)  # 叙述视角
    sentence_length_preference = Column(String(20), nullable=True)  # short, medium, long
    dialogue_density = Column(String(20), nullable=True)  # low, medium, high
    description_intensity = Column(String(20), nullable=True)  # sparse, medium, detailed
    rhythm_preference = Column(String(20), nullable=True)  # slow, medium, fast
    forbidden_words = Column(JSON, nullable=True)  # 禁用词
    forbidden_phrases = Column(JSON, nullable=True)  # 禁用短语
    preferred_sentence_patterns = Column(JSON, nullable=True)  # 偏好句式
    character_voice_guidelines = Column(JSON, nullable=True)  # 人物口吻指南
    platform_specific_rules = Column(JSON, nullable=True)  # 平台特定规则
    is_active = Column(Boolean, default=True, nullable=False)  # 是否激活
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    novel = relationship("Novel", back_populates="style_guides")

    def __repr__(self) -> str:
        return f"<StyleGuide(id={self.id}, name='{self.name}', is_active={self.is_active})>"


class AgentRun(Base):
    """AgentRun model representing an agent run within a novel."""
    __tablename__ = "agent_runs"

    id = Column(Integer, primary_key=True, index=True)
    chapter_id = Column(Integer, ForeignKey("chapters.id"), nullable=False, index=True)
    novel_id = Column(Integer, ForeignKey("novels.id"), nullable=False, index=True)
    agent_name = Column(String(100), nullable=False, index=True)  # e.g., chapter_planner_agent
    agent_version = Column(String(50), nullable=True)  # e.g., v1.0
    prompt_version = Column(String(50), nullable=True)  # e.g., v1.2
    model_name = Column(String(100), nullable=True)  # e.g., deepseek-v4-pro
    input_data = Column(JSON, nullable=True)  # 输入数据
    output_data = Column(JSON, nullable=True)  # 输出数据
    status = Column(String(20), default="pending", nullable=False)  # pending, running, completed, failed
    start_time = Column(String(50), nullable=True)  # 开始时间
    end_time = Column(String(50), nullable=True)  # 结束时间
    duration_seconds = Column(Integer, nullable=True)  # 持续时间（秒）
    input_tokens = Column(Integer, nullable=True)  # 输入token数
    output_tokens = Column(Integer, nullable=True)  # 输出token数
    total_tokens = Column(Integer, nullable=True)  # 总token数
    cost_usd = Column(Float, nullable=True)  # 成本（美元）
    error_message = Column(Text, nullable=True)  # 错误信息
    run_metadata = Column(JSON, nullable=True)  # 元数据
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # Relationships
    chapter = relationship("Chapter", back_populates="agent_runs")
    novel = relationship("Novel", back_populates="agent_runs")
    model_calls = relationship("ModelCall", back_populates="agent_run")

    def __repr__(self) -> str:
        return f"<AgentRun(id={self.id}, agent_name='{self.agent_name}', status='{self.status}')>"


class ModelCall(Base):
    """ModelCall model representing a model call within an agent run."""
    __tablename__ = "model_calls"

    id = Column(Integer, primary_key=True, index=True)
    agent_run_id = Column(Integer, ForeignKey("agent_runs.id"), nullable=False, index=True)
    model_name = Column(String(100), nullable=False, index=True)  # e.g., deepseek-v4-pro
    model_version = Column(String(100), nullable=True)  # e.g., 2026-06-01
    prompt = Column(Text, nullable=True)  # 提示词
    prompt_tokens = Column(Integer, nullable=True)  # 提示词token数
    completion_tokens = Column(Integer, nullable=True)  # 完成token数
    total_tokens = Column(Integer, nullable=True)  # 总token数
    cost_usd = Column(Float, nullable=True)  # 成本（美元）
    latency_ms = Column(Integer, nullable=True)  # 延迟（毫秒）
    temperature = Column(Float, nullable=True)  # 温度参数
    top_p = Column(Float, nullable=True)  # top_p参数
    max_tokens = Column(Integer, nullable=True)  # 最大token数
    status = Column(String(20), default="pending", nullable=False)  # pending, success, error, timeout
    error_message = Column(Text, nullable=True)  # 错误信息
    response = Column(JSON, nullable=True)  # 响应内容
    call_metadata = Column(JSON, nullable=True)  # 元数据
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # Relationships
    agent_run = relationship("AgentRun", back_populates="model_calls")

    def __repr__(self) -> str:
        return f"<ModelCall(id={self.id}, model_name='{self.model_name}', status='{self.status}')>"


class QualityReport(Base):
    """QualityReport model representing a quality report within a novel."""
    __tablename__ = "quality_reports"

    id = Column(Integer, primary_key=True, index=True)
    chapter_id = Column(Integer, ForeignKey("chapters.id"), nullable=False, index=True)
    novel_id = Column(Integer, ForeignKey("novels.id"), nullable=False, index=True)
    report_type = Column(String(20), nullable=False)  # auto, manual
    overall_score = Column(Float, nullable=True)  # 总体评分
    plot_progression = Column(Float, nullable=True)  # 剧情推进
    conflict_strength = Column(Float, nullable=True)  # 冲突强度
    character_consistency = Column(Float, nullable=True)  # 人物一致性
    style_naturalness = Column(Float, nullable=True)  # 语言自然度
    dialogue_quality = Column(Float, nullable=True)  # 对话质量
    hook_strength = Column(Float, nullable=True)  # 章末钩子
    continuity_safety = Column(Float, nullable=True)  # 连续性安全
    cliche_density = Column(Float, nullable=True)  # 套话密度
    main_problems = Column(JSON, nullable=True)  # 主要问题
    revision_plan = Column(JSON, nullable=True)  # 修改计划
    strengths = Column(JSON, nullable=True)  # 优点
    weaknesses = Column(JSON, nullable=True)  # 弱点
    recommendations = Column(JSON, nullable=True)  # 建议
    is_passing = Column(Boolean, default=False, nullable=False)  # 是否通过质量检查
    blocking_issues = Column(JSON, nullable=True)  # 阻断性问题
    evaluator_agent = Column(String(100), nullable=True)  # 评估者
    evaluator_version = Column(String(50), nullable=True)  # 评估者版本
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # Relationships
    chapter = relationship("Chapter", back_populates="quality_reports")
    novel = relationship("Novel", back_populates="quality_reports")

    def __repr__(self) -> str:
        return f"<QualityReport(id={self.id}, overall_score={self.overall_score}, is_passing={self.is_passing})>"


class CharacterState(Base):
    """CharacterState model representing a character's state at a specific chapter."""
    __tablename__ = "character_states"

    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(Integer, ForeignKey("characters.id"), nullable=False, index=True)
    chapter_id = Column(Integer, ForeignKey("chapters.id"), nullable=False, index=True)
    current_knowledge = Column(JSON, nullable=True)  # 当前知道什么
    emotion = Column(String(100), nullable=True)  # 情绪状态
    injury = Column(Text, nullable=True)  # 受伤情况
    trust_level = Column(String(50), nullable=True)  # 信任等级
    relationship_changes = Column(JSON, nullable=True)  # 关系变化
    inventory_changes = Column(JSON, nullable=True)  # 物品变化
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # Relationships
    character = relationship("Character", back_populates="states")
    chapter = relationship("Chapter", back_populates="character_states")

    def __repr__(self) -> str:
        return f"<CharacterState(id={self.id}, character_id={self.character_id}, chapter_id={self.chapter_id})>"
