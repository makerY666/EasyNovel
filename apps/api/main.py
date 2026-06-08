"""Main FastAPI application for AI Novel Studio."""
import re
import uuid
from typing import Any, Optional

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from apps.api.dependencies import (
    get_chapter_workflow,
    get_db,
    get_deepseek_client,
    get_memory_manager,
    get_model_gateway,
    get_settings,
)
from packages.database.models import (
    AgentRun,
    Chapter,
    ChapterVersion,
    Character,
    Foreshadowing,
    Novel,
    Project,
    QualityReport,
    StyleGuide,
    TimelineEvent,
    WorldRule,
)
from packages.memory.memory_manager import MemoryManager
from packages.models.deepseek_client import DeepSeekClient
from packages.models.model_gateway import ModelGateway
from packages.workflow.chapter_workflow import ChapterWorkflow


app = FastAPI(title="AI Novel Studio", version="0.3.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    target_platform: Optional[str] = None
    target_audience: Optional[str] = None
    expected_word_count: Optional[int] = None
    protagonist_type: Optional[str] = None
    pleasure_points: Optional[list[str]] = None
    forbidden_tropes: Optional[list[str]] = None
    reference_style: Optional[str] = None


class NovelCreate(BaseModel):
    project_id: int
    title: str = Field(..., min_length=1, max_length=255)
    subtitle: Optional[str] = None
    synopsis: Optional[str] = None
    genre: Optional[str] = None
    sub_genre: Optional[str] = None
    target_word_count: Optional[int] = None
    style_guide: Optional[str] = None
    taboo_words: Optional[list[str]] = None


class ChapterCreate(BaseModel):
    novel_id: int
    chapter_number: int = Field(..., gt=0)
    title: Optional[str] = None
    summary: Optional[str] = None
    target_word_count: Optional[int] = None


class CharacterCreate(BaseModel):
    novel_id: int
    name: str = Field(..., min_length=1, max_length=255)
    role: Optional[str] = None
    public_goal: Optional[str] = None
    hidden_desire: Optional[str] = None
    fear: Optional[str] = None
    relationship_to_protagonist: Optional[str] = None
    current_knowledge: Optional[list[str]] = None
    secrets: Optional[list[str]] = None
    voice_style: Optional[dict[str, Any]] = None
    physical_description: Optional[str] = None
    personality_traits: Optional[list[str]] = None
    background_story: Optional[str] = None
    skills: Optional[list[str]] = None
    weaknesses: Optional[list[str]] = None


class StyleGuideCreate(BaseModel):
    novel_id: int
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    narrative_pov: Optional[str] = None
    sentence_length_preference: Optional[str] = None
    dialogue_density: Optional[str] = None
    description_intensity: Optional[str] = None
    rhythm_preference: Optional[str] = None
    forbidden_words: Optional[list[str]] = None
    forbidden_phrases: Optional[list[str]] = None
    preferred_sentence_patterns: Optional[list[str]] = None
    character_voice_guidelines: Optional[dict[str, str]] = None
    platform_specific_rules: Optional[dict[str, str]] = None
    is_active: bool = True


class TimelineEventCreate(BaseModel):
    chapter_id: int
    novel_id: int
    date_in_story: str = "未指定"
    location: str = "未指定"
    events: Optional[list[str]] = None
    state_changes: Optional[list[str]] = None
    duration: Optional[str] = None
    weather: Optional[str] = None
    importance: Optional[str] = None


class WorkflowStartRequest(BaseModel):
    novel_id: int
    chapter_number: int = Field(..., gt=0)
    previous_chapter_summary: Optional[str] = None
    chapter_goal: Optional[str] = None
    style_guide: Optional[dict[str, Any]] = None
    target_platform: str = "番茄小说"
    polish_level: str = "medium"


class WorkflowApprovalRequest(BaseModel):
    chapter_id: Optional[int] = None
    stage: str = Field(..., min_length=1)
    content: Optional[str] = None
    chapter_card: Optional[dict[str, Any]] = None
    mark_final: bool = False


class WorldRuleCreate(BaseModel):
    novel_id: int
    rule_id: str
    content: str
    priority: str = "medium"
    category: Optional[str] = None


class ForeshadowingCreate(BaseModel):
    novel_id: int
    foreshadowing_id: str
    introduced_at_chapter: int
    content: str
    intended_payoff_chapter: Optional[int] = None
    intended_payoff_content: Optional[str] = None
    related_characters: Optional[list[str]] = None
    importance: Optional[str] = None
    notes: Optional[str] = None


class ChapterVersionCreate(BaseModel):
    stage: str = "manual"
    content: str = Field(..., min_length=1)
    source: str = "manual"
    workflow_id: Optional[str] = None
    version_metadata: Optional[dict[str, Any]] = None


_workflow_store: dict[str, dict[str, Any]] = {}


def _count_words(content: str) -> int:
    return len(re.sub(r"\s+", "", content or ""))


def _dump_update(model: BaseModel) -> dict[str, Any]:
    return {k: v for k, v in model.model_dump(exclude_unset=True).items()}


def _update_model(obj: Any, data: dict[str, Any]) -> Any:
    for key, value in data.items():
        if hasattr(obj, key):
            setattr(obj, key, value)
    return obj


def _next_version_number(db: Session, chapter_id: int) -> int:
    last = (
        db.query(ChapterVersion)
        .filter(ChapterVersion.chapter_id == chapter_id)
        .order_by(ChapterVersion.version_number.desc())
        .first()
    )
    return 1 if last is None else last.version_number + 1


def _create_chapter_version(
    db: Session,
    chapter: Chapter,
    stage: str,
    content: str,
    source: str = "manual",
    workflow_id: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> ChapterVersion:
    version = ChapterVersion(
        chapter_id=chapter.id,
        novel_id=chapter.novel_id,
        version_number=_next_version_number(db, chapter.id),
        stage=stage,
        content=content,
        word_count=_count_words(content),
        source=source,
        workflow_id=workflow_id,
        version_metadata=metadata,
    )
    db.add(version)
    db.flush()
    chapter.current_version_id = version.id
    chapter.current_word_count = version.word_count
    if stage in {"draft", "polished", "manual", "final"}:
        chapter.status = "final" if stage == "final" else stage
    return version


def _project_out(p: Project) -> dict[str, Any]:
    return {
        "id": p.id,
        "name": p.name,
        "description": p.description,
        "target_platform": p.target_platform,
        "target_audience": p.target_audience,
        "expected_word_count": p.expected_word_count,
        "protagonist_type": p.protagonist_type,
        "pleasure_points": p.pleasure_points or [],
        "forbidden_tropes": p.forbidden_tropes or [],
        "reference_style": p.reference_style,
        "created_at": str(p.created_at),
        "updated_at": str(p.updated_at),
    }


def _novel_out(n: Novel) -> dict[str, Any]:
    return {
        "id": n.id,
        "project_id": n.project_id,
        "title": n.title,
        "subtitle": n.subtitle,
        "synopsis": n.synopsis,
        "genre": n.genre,
        "sub_genre": n.sub_genre,
        "target_word_count": n.target_word_count,
        "current_word_count": n.current_word_count,
        "status": n.status,
        "style_guide": n.style_guide,
        "taboo_words": n.taboo_words or [],
        "created_at": str(n.created_at),
        "updated_at": str(n.updated_at),
    }


def _chapter_out(c: Chapter) -> dict[str, Any]:
    return {
        "id": c.id,
        "novel_id": c.novel_id,
        "chapter_number": c.chapter_number,
        "title": c.title,
        "summary": c.summary,
        "target_word_count": c.target_word_count,
        "current_word_count": c.current_word_count,
        "status": c.status,
        "chapter_card": c.chapter_card,
        "current_version_id": c.current_version_id,
        "pov": c.pov,
        "time_in_story": c.time_in_story,
        "location": c.location,
        "created_at": str(c.created_at),
        "updated_at": str(c.updated_at),
    }


def _version_out(v: ChapterVersion) -> dict[str, Any]:
    return {
        "id": v.id,
        "chapter_id": v.chapter_id,
        "novel_id": v.novel_id,
        "version_number": v.version_number,
        "stage": v.stage,
        "content": v.content,
        "word_count": v.word_count,
        "source": v.source,
        "workflow_id": v.workflow_id,
        "version_metadata": v.version_metadata or {},
        "created_at": str(v.created_at),
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "version": "0.3.0"}


@app.post("/api/v1/projects", status_code=201)
async def create_project(data: ProjectCreate, db: Session = Depends(get_db)):
    p = Project(**data.model_dump())
    db.add(p)
    db.commit()
    db.refresh(p)
    return _project_out(p)


@app.get("/api/v1/projects")
async def list_projects(db: Session = Depends(get_db)):
    return [_project_out(p) for p in db.query(Project).order_by(Project.id.desc()).all()]


@app.patch("/api/v1/projects/{project_id}")
async def update_project(
    project_id: int, data: ProjectCreate, db: Session = Depends(get_db)
):
    p = db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "Project not found")
    _update_model(p, _dump_update(data))
    db.commit()
    db.refresh(p)
    return _project_out(p)


@app.post("/api/v1/novels", status_code=201)
async def create_novel(data: NovelCreate, db: Session = Depends(get_db)):
    if not db.get(Project, data.project_id):
        raise HTTPException(404, "Project not found")
    n = Novel(**data.model_dump())
    db.add(n)
    db.commit()
    db.refresh(n)
    return _novel_out(n)


@app.get("/api/v1/novels")
async def list_novels(project_id: Optional[int] = None, db: Session = Depends(get_db)):
    q = db.query(Novel)
    if project_id is not None:
        q = q.filter(Novel.project_id == project_id)
    return [_novel_out(n) for n in q.order_by(Novel.id.desc()).all()]


@app.patch("/api/v1/novels/{novel_id}")
async def update_novel(novel_id: int, data: NovelCreate, db: Session = Depends(get_db)):
    n = db.get(Novel, novel_id)
    if not n:
        raise HTTPException(404, "Novel not found")
    _update_model(n, _dump_update(data))
    db.commit()
    db.refresh(n)
    return _novel_out(n)


@app.post("/api/v1/chapters", status_code=201)
async def create_chapter(data: ChapterCreate, db: Session = Depends(get_db)):
    if not db.get(Novel, data.novel_id):
        raise HTTPException(404, "Novel not found")
    c = Chapter(**data.model_dump(), status="planned")
    db.add(c)
    db.commit()
    db.refresh(c)
    return _chapter_out(c)


@app.get("/api/v1/chapters")
async def list_chapters(novel_id: int, db: Session = Depends(get_db)):
    chapters = (
        db.query(Chapter)
        .filter(Chapter.novel_id == novel_id)
        .order_by(Chapter.chapter_number)
        .all()
    )
    return [_chapter_out(c) for c in chapters]


@app.patch("/api/v1/chapters/{chapter_id}")
async def update_chapter(
    chapter_id: int, data: ChapterCreate, db: Session = Depends(get_db)
):
    c = db.get(Chapter, chapter_id)
    if not c:
        raise HTTPException(404, "Chapter not found")
    _update_model(c, _dump_update(data))
    db.commit()
    db.refresh(c)
    return _chapter_out(c)


@app.get("/api/v1/chapters/{chapter_id}/versions")
async def list_chapter_versions(chapter_id: int, db: Session = Depends(get_db)):
    versions = (
        db.query(ChapterVersion)
        .filter(ChapterVersion.chapter_id == chapter_id)
        .order_by(ChapterVersion.version_number)
        .all()
    )
    return [_version_out(v) for v in versions]


@app.post("/api/v1/chapters/{chapter_id}/versions", status_code=201)
async def create_chapter_version(
    chapter_id: int, data: ChapterVersionCreate, db: Session = Depends(get_db)
):
    chapter = db.get(Chapter, chapter_id)
    if not chapter:
        raise HTTPException(404, "Chapter not found")
    version = _create_chapter_version(
        db,
        chapter,
        stage=data.stage,
        content=data.content,
        source=data.source,
        workflow_id=data.workflow_id,
        metadata=data.version_metadata,
    )
    db.commit()
    db.refresh(version)
    return _version_out(version)


@app.patch("/api/v1/chapters/{chapter_id}/versions/{version_id}")
async def update_chapter_version(
    chapter_id: int,
    version_id: int,
    data: ChapterVersionCreate,
    db: Session = Depends(get_db),
):
    version = (
        db.query(ChapterVersion)
        .filter(ChapterVersion.chapter_id == chapter_id, ChapterVersion.id == version_id)
        .first()
    )
    if not version:
        raise HTTPException(404, "Chapter version not found")
    _update_model(version, _dump_update(data))
    version.word_count = _count_words(version.content)
    chapter = db.get(Chapter, chapter_id)
    if chapter:
        chapter.current_version_id = version.id
        chapter.current_word_count = version.word_count
        chapter.status = "final" if version.stage == "final" else version.stage
    db.commit()
    db.refresh(version)
    return _version_out(version)


@app.post("/api/v1/characters", status_code=201)
async def create_character(data: CharacterCreate, db: Session = Depends(get_db)):
    ch = Character(**data.model_dump())
    db.add(ch)
    db.commit()
    db.refresh(ch)
    return _model_dict(ch)


@app.get("/api/v1/characters")
async def list_characters(novel_id: int, db: Session = Depends(get_db)):
    rows = db.query(Character).filter(Character.novel_id == novel_id).order_by(Character.id).all()
    return [_model_dict(row) for row in rows]


@app.patch("/api/v1/characters/{character_id}")
async def update_character(
    character_id: int, data: CharacterCreate, db: Session = Depends(get_db)
):
    ch = db.get(Character, character_id)
    if not ch:
        raise HTTPException(404, "Character not found")
    _update_model(ch, _dump_update(data))
    db.commit()
    db.refresh(ch)
    return _model_dict(ch)


@app.post("/api/v1/style-guides", status_code=201)
async def create_style_guide(data: StyleGuideCreate, db: Session = Depends(get_db)):
    if data.is_active:
        db.query(StyleGuide).filter(StyleGuide.novel_id == data.novel_id).update(
            {"is_active": False}
        )
    sg = StyleGuide(**data.model_dump())
    db.add(sg)
    db.commit()
    db.refresh(sg)
    return _model_dict(sg)


@app.get("/api/v1/style-guides")
async def list_style_guides(novel_id: int, db: Session = Depends(get_db)):
    rows = (
        db.query(StyleGuide)
        .filter(StyleGuide.novel_id == novel_id)
        .order_by(StyleGuide.id.desc())
        .all()
    )
    return [_model_dict(row) for row in rows]


@app.patch("/api/v1/style-guides/{style_guide_id}")
async def update_style_guide(
    style_guide_id: int, data: StyleGuideCreate, db: Session = Depends(get_db)
):
    sg = db.get(StyleGuide, style_guide_id)
    if not sg:
        raise HTTPException(404, "Style guide not found")
    patch = _dump_update(data)
    if patch.get("is_active"):
        db.query(StyleGuide).filter(StyleGuide.novel_id == sg.novel_id).update(
            {"is_active": False}
        )
    _update_model(sg, patch)
    db.commit()
    db.refresh(sg)
    return _model_dict(sg)


@app.post("/api/v1/timeline-events", status_code=201)
async def create_timeline_event(
    data: TimelineEventCreate, db: Session = Depends(get_db)
):
    event = TimelineEvent(**data.model_dump())
    db.add(event)
    db.commit()
    db.refresh(event)
    return _model_dict(event)


@app.get("/api/v1/timeline-events")
async def list_timeline_events(novel_id: int, db: Session = Depends(get_db)):
    rows = (
        db.query(TimelineEvent)
        .filter(TimelineEvent.novel_id == novel_id)
        .order_by(TimelineEvent.id)
        .all()
    )
    return [_model_dict(row) for row in rows]


@app.patch("/api/v1/timeline-events/{event_id}")
async def update_timeline_event(
    event_id: int, data: TimelineEventCreate, db: Session = Depends(get_db)
):
    event = db.get(TimelineEvent, event_id)
    if not event:
        raise HTTPException(404, "Timeline event not found")
    _update_model(event, _dump_update(data))
    db.commit()
    db.refresh(event)
    return _model_dict(event)


@app.get("/api/v1/quality-reports")
async def list_quality_reports(chapter_id: int, db: Session = Depends(get_db)):
    rows = (
        db.query(QualityReport)
        .filter(QualityReport.chapter_id == chapter_id)
        .order_by(QualityReport.id.desc())
        .all()
    )
    return [_model_dict(row) for row in rows]


@app.get("/api/v1/agent-runs")
async def list_agent_runs(chapter_id: int, db: Session = Depends(get_db)):
    rows = (
        db.query(AgentRun)
        .filter(AgentRun.chapter_id == chapter_id)
        .order_by(AgentRun.id.desc())
        .all()
    )
    return [_model_dict(row) for row in rows]


def _model_dict(obj: Any) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for column in obj.__table__.columns:
        value = getattr(obj, column.name)
        data[column.name] = str(value) if column.name.endswith("_at") else value
    return data


def _update_workflow(wf_id: str, **kwargs: Any) -> None:
    if wf_id in _workflow_store:
        _workflow_store[wf_id].update(kwargs)


def _ensure_chapter(db: Session, novel_id: int, chapter_number: int) -> Chapter:
    chapter = (
        db.query(Chapter)
        .filter(Chapter.novel_id == novel_id, Chapter.chapter_number == chapter_number)
        .first()
    )
    if chapter:
        return chapter
    chapter = Chapter(
        novel_id=novel_id,
        chapter_number=chapter_number,
        title=f"第 {chapter_number} 章",
        status="planned",
    )
    db.add(chapter)
    db.flush()
    return chapter


async def _run_workflow_background(
    wf_id: str,
    workflow: ChapterWorkflow,
    memory_manager: MemoryManager,
    db: Session,
    data: WorkflowStartRequest,
) -> None:
    try:
        chapter = _ensure_chapter(db, data.novel_id, data.chapter_number)
        db.commit()
        _update_workflow(wf_id, chapter_id=chapter.id)

        def on_progress(stage: str, state: dict[str, Any]) -> None:
            _update_workflow(
                wf_id,
                current_stage=stage,
                **{k: v for k, v in state.items() if k != "current_stage"},
            )

        result = await workflow.execute(
            novel_id=data.novel_id,
            chapter_number=data.chapter_number,
            previous_chapter_summary=data.previous_chapter_summary,
            chapter_goal=data.chapter_goal,
            style_guide=data.style_guide,
            target_platform=data.target_platform,
            polish_level=data.polish_level,
            on_progress=on_progress,
        )

        chapter = db.get(Chapter, chapter.id)
        if chapter is None:
            raise RuntimeError("Chapter disappeared during workflow")
        chapter.chapter_card = result.get("chapter_card")
        if result.get("draft_text"):
            _create_chapter_version(
                db, chapter, "draft", result["draft_text"], "ai", wf_id
            )
        if result.get("polished_text"):
            _create_chapter_version(
                db,
                chapter,
                "polished",
                result["polished_text"],
                "ai",
                wf_id,
                {"style_changes": result.get("style_changes", [])},
            )

        quality_score = result.get("quality_score") or {}
        if quality_score:
            report = QualityReport(
                chapter_id=chapter.id,
                novel_id=chapter.novel_id,
                report_type="auto",
                overall_score=sum(float(v) for v in quality_score.values())
                / max(len(quality_score), 1),
                style_naturalness=quality_score.get("naturalness"),
                dialogue_quality=quality_score.get("character_voice"),
                cliche_density=quality_score.get("cliche_control"),
                strengths=result.get("style_changes") or [],
                is_passing=True,
                evaluator_agent="chapter_workflow",
                evaluator_version="v0.3.0",
            )
            db.add(report)

        db.add(
            AgentRun(
                chapter_id=chapter.id,
                novel_id=chapter.novel_id,
                agent_name="chapter_workflow",
                agent_version="v0.3.0",
                output_data={
                    "workflow_id": wf_id,
                    "chapter_card": result.get("chapter_card"),
                    "quality_score": quality_score,
                },
                status="completed",
            )
        )
        db.commit()
        _update_workflow(wf_id, status="completed", chapter_id=chapter.id, **result)
    except Exception as exc:
        db.rollback()
        _update_workflow(wf_id, status="failed", current_stage="failed", error=str(exc))


@app.post("/api/v1/workflows/chapter", status_code=202)
async def start_workflow(
    data: WorkflowStartRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    if not db.get(Novel, data.novel_id):
        raise HTTPException(404, "Novel not found")
    wf_id = str(uuid.uuid4())[:8]
    memory_manager = get_memory_manager(db)
    workflow = get_chapter_workflow(memory_manager)
    chapter = _ensure_chapter(db, data.novel_id, data.chapter_number)
    db.commit()

    _workflow_store[wf_id] = {
        "workflow_id": wf_id,
        "status": "pending",
        "current_stage": "building_context",
        "novel_id": data.novel_id,
        "chapter_id": chapter.id,
        "chapter_number": data.chapter_number,
    }
    background_tasks.add_task(
        _run_workflow_background, wf_id, workflow, memory_manager, db, data
    )
    return _workflow_store[wf_id]


@app.get("/api/v1/workflows/{workflow_id}/status")
async def workflow_status(workflow_id: str):
    if workflow_id not in _workflow_store:
        raise HTTPException(404, "Workflow not found")
    return _workflow_store[workflow_id]


@app.post("/api/v1/workflows/chapter/{workflow_id}/approve-stage")
async def approve_workflow_stage(
    workflow_id: str, data: WorkflowApprovalRequest, db: Session = Depends(get_db)
):
    state = _workflow_store.get(workflow_id)
    if not state:
        raise HTTPException(404, "Workflow not found")
    chapter_id = data.chapter_id or state.get("chapter_id")
    if not chapter_id:
        raise HTTPException(400, "chapter_id is required")
    chapter = db.get(Chapter, chapter_id)
    if not chapter:
        raise HTTPException(404, "Chapter not found")
    if data.chapter_card is not None:
        chapter.chapter_card = data.chapter_card
    version = None
    if data.content:
        stage = "final" if data.mark_final else data.stage
        version = _create_chapter_version(
            db, chapter, stage, data.content, "manual", workflow_id
        )
    db.commit()
    return {
        "workflow_id": workflow_id,
        "chapter": _chapter_out(chapter),
        "version": _version_out(version) if version else None,
    }


@app.get("/api/v1/memory/world-rules")
async def get_world_rules(novel_id: int, db: Session = Depends(get_db)):
    mm = get_memory_manager(db)
    return [_model_dict(r) for r in mm.get_world_rules(novel_id)]


@app.post("/api/v1/memory/world-rules", status_code=201)
async def add_world_rule(data: WorldRuleCreate, db: Session = Depends(get_db)):
    mm = get_memory_manager(db)
    rid = mm.add_world_rule(
        novel_id=data.novel_id,
        rule_id=data.rule_id,
        content=data.content,
        priority=data.priority,
        category=data.category,
    )
    db.commit()
    return _model_dict(db.get(WorldRule, rid))


@app.get("/api/v1/memory/timeline")
async def get_timeline(
    novel_id: int, limit: Optional[int] = None, db: Session = Depends(get_db)
):
    mm = get_memory_manager(db)
    return [_model_dict(e) for e in mm.get_timeline_for_novel(novel_id, limit=limit)]


@app.get("/api/v1/memory/foreshadowings")
async def get_foreshadowings(novel_id: int, db: Session = Depends(get_db)):
    mm = get_memory_manager(db)
    return [_model_dict(f) for f in mm.get_open_foreshadowings(novel_id)]


@app.post("/api/v1/memory/foreshadowings", status_code=201)
async def add_foreshadowing(data: ForeshadowingCreate, db: Session = Depends(get_db)):
    mm = get_memory_manager(db)
    fid = mm.add_foreshadowing(**data.model_dump())
    db.commit()
    return _model_dict(db.get(Foreshadowing, fid))


@app.get("/api/v1/memory/style-guide")
async def get_style_guide(novel_id: int, db: Session = Depends(get_db)):
    mm = get_memory_manager(db)
    sg = mm.get_active_style_guide(novel_id)
    if not sg:
        raise HTTPException(404, "No active style guide found")
    return _model_dict(sg)


@app.get("/api/v1/memory/context-pack")
async def get_context_pack(
    novel_id: int,
    chapter_id: int,
    chapter_goal: str = "",
    db: Session = Depends(get_db),
):
    mm = get_memory_manager(db)
    return mm.build_context_pack(
        chapter_id=chapter_id, novel_id=novel_id, chapter_goal=chapter_goal
    )


@app.post("/api/v1/exports/novel/{novel_id}")
async def export_novel(
    novel_id: int,
    format: str = "markdown",
    chapter_ids: Optional[str] = None,
    db: Session = Depends(get_db),
):
    if format not in {"txt", "markdown"}:
        raise HTTPException(400, "format must be txt or markdown")
    novel = db.get(Novel, novel_id)
    if not novel:
        raise HTTPException(404, "Novel not found")
    query = db.query(Chapter).filter(Chapter.novel_id == novel_id)
    if chapter_ids:
        ids = [int(part) for part in chapter_ids.split(",") if part.strip()]
        query = query.filter(Chapter.id.in_(ids))
    chapters = query.order_by(Chapter.chapter_number).all()
    parts: list[str] = []
    if format == "markdown":
        parts.append(f"# {novel.title}\n")
    else:
        parts.append(f"{novel.title}\n{'=' * len(novel.title)}\n")
    for chapter in chapters:
        title = chapter.title or f"第 {chapter.chapter_number} 章"
        heading = f"## {title}" if format == "markdown" else title
        content = _current_chapter_content(db, chapter)
        parts.append(f"\n{heading}\n\n{content}\n")
    body = "\n".join(parts)
    media_type = "text/markdown" if format == "markdown" else "text/plain"
    ext = "md" if format == "markdown" else "txt"
    headers = {"Content-Disposition": f'attachment; filename="novel_{novel_id}.{ext}"'}
    return Response(content=body, media_type=f"{media_type}; charset=utf-8", headers=headers)


def _current_chapter_content(db: Session, chapter: Chapter) -> str:
    version = None
    if chapter.current_version_id:
        version = db.get(ChapterVersion, chapter.current_version_id)
    if version is None:
        version = (
            db.query(ChapterVersion)
            .filter(ChapterVersion.chapter_id == chapter.id)
            .order_by(ChapterVersion.version_number.desc())
            .first()
        )
    return version.content if version else ""


@app.get("/api/v1/models/status")
async def model_status(client: DeepSeekClient = Depends(get_deepseek_client)):
    return {
        "flash": {
            "status": "configured",
            "provider": client.provider,
            "model": client.get_model_name("flash"),
        },
        "pro": {
            "status": "configured",
            "provider": client.provider,
            "model": client.get_model_name("pro"),
        },
    }


@app.get("/api/v1/models/config")
async def model_config():
    settings = get_settings()
    return {
        "provider": settings.model_provider,
        "base_url": settings.model_base_url,
        "flash_model": settings.model_flash,
        "pro_model": settings.model_pro,
        "timeout_seconds": settings.model_timeout_seconds,
        "api_key_configured": settings.model_configured,
    }


@app.post("/api/v1/models/check")
async def model_check():
    settings = get_settings()
    if not settings.model_configured:
        return {
            "ok": False,
            "message": "MODEL_API_KEY or DEEPSEEK_API_KEY is not configured.",
        }
    try:
        client = get_deepseek_client()
        return {
            "ok": True,
            "provider": client.provider,
            "flash_model": client.get_model_name("flash"),
            "pro_model": client.get_model_name("pro"),
        }
    except Exception as exc:
        return {"ok": False, "message": str(exc)}


@app.get("/api/v1/models/cost-summary")
async def cost_summary(gateway: ModelGateway = Depends(get_model_gateway)):
    by_task: dict[str, float] = {}
    by_model: dict[str, float] = {}
    for entry in gateway.cost_history:
        by_task[entry["task"]] = by_task.get(entry["task"], 0.0) + entry["cost_usd"]
        by_model[entry["model_type"]] = by_model.get(entry["model_type"], 0.0) + entry[
            "cost_usd"
        ]
    return {
        "total_cost_usd": gateway.get_total_cost(),
        "calls_count": len(gateway.cost_history),
        "by_task": by_task,
        "by_model": by_model,
    }
