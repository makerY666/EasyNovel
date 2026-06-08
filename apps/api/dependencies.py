"""Dependency injection and service wiring for AI Novel Studio API."""
from functools import lru_cache
from typing import Generator

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from apps.api.config import Settings
from apps.api.database import (
    create_engine_from_url,
    create_session_factory,
    create_tables,
)
from packages.models.deepseek_client import DeepSeekClient
from packages.models.model_gateway import ModelGateway
from packages.memory.memory_manager import MemoryManager
from packages.agents.chapter_planner_agent import ChapterPlannerAgent
from packages.agents.draft_writer_agent import DraftWriterAgent
from packages.agents.human_style_polisher_agent import HumanStylePolisherAgent
from packages.workflow.chapter_workflow import ChapterWorkflow


# ---------- Singleton helpers ----------

@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()


_settings = None
_engine = None
_SessionLocal = None
_deepseek_client = None
_model_gateway = None


# ---------- Database ----------

def _get_engine() -> Engine:
    """Create or return the database engine."""
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_engine_from_url(settings.database_url)
        create_tables(_engine)
    return _engine


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: provide a database session.

    Yields:
        SQLAlchemy Session instance.

    Usage in routes:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            ...
    """
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = create_session_factory(_get_engine())

    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------- DeepSeek Client ----------

def get_deepseek_client() -> DeepSeekClient:
    """Create or return the DeepSeek API client."""
    global _deepseek_client
    if _deepseek_client is None:
        settings = get_settings()
        _deepseek_client = DeepSeekClient(
            api_key=settings.model_api_key,
            base_url=settings.model_base_url,
            provider=settings.model_provider,
            model_flash=settings.model_flash,
            model_pro=settings.model_pro,
            timeout_seconds=settings.model_timeout_seconds,
        )
    return _deepseek_client


# ---------- Model Gateway ----------

def get_model_gateway() -> ModelGateway:
    """Create or return the ModelGateway."""
    global _model_gateway
    if _model_gateway is None:
        _model_gateway = ModelGateway(client=get_deepseek_client())
    return _model_gateway


# ---------- Memory Manager ----------

def get_memory_manager(db: Session) -> MemoryManager:
    """Create a MemoryManager for the current database session.

    Args:
        db: Database session (injected by FastAPI).

    Returns:
        MemoryManager instance.
    """
    return MemoryManager(db=db)


# ---------- Agents ----------

def get_chapter_planner_agent() -> ChapterPlannerAgent:
    """Create or return the ChapterPlannerAgent."""
    return ChapterPlannerAgent(gateway=get_model_gateway())


def get_draft_writer_agent() -> DraftWriterAgent:
    """Create or return the DraftWriterAgent."""
    return DraftWriterAgent(gateway=get_model_gateway())


def get_style_polisher_agent() -> HumanStylePolisherAgent:
    """Create or return the HumanStylePolisherAgent."""
    return HumanStylePolisherAgent(gateway=get_model_gateway())


# ---------- Workflow ----------

def get_chapter_workflow(
    memory_manager: MemoryManager,
) -> ChapterWorkflow:
    """Create a ChapterWorkflow with all agents.

    Args:
        memory_manager: MemoryManager instance (injected by FastAPI).

    Returns:
        ChapterWorkflow instance.
    """
    return ChapterWorkflow(
        chapter_planner=get_chapter_planner_agent(),
        draft_writer=get_draft_writer_agent(),
        style_polisher=get_style_polisher_agent(),
        memory_manager=memory_manager,
    )
