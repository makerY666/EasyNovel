from typing import Literal, Any
from pydantic import BaseModel, Field, model_validator

Kind = Literal['rule','character','state','knowledge','relationship','event','foreshadow','plan','directive','summary']


class ProjectInput(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    genre: str = ''
    mode: Literal['serial', 'literary'] = 'serial'
    description: str = ''
    settings: dict = Field(default_factory=dict)


class ChapterInput(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    number: int | None = Field(default=None, ge=1)
    branch_id: str = 'main'
    story_time: float | None = None


class Paragraph(BaseModel):
    id: str = Field(min_length=1, max_length=100)
    text: str
    locked: bool = False


class VersionInput(BaseModel):
    content: str = Field(max_length=500000)
    paragraphs: list[Paragraph] | None = None
    expected_revision: int
    source: Literal['manual','ai','import'] = 'manual'
    parent_id: str | None = None
    check_head: bool = False
    expected_head_id: str | None = None


class RecordInput(BaseModel):
    kind: Kind
    title: str = Field(min_length=1, max_length=250)
    content: str = Field(max_length=100000)
    branch_id: str = 'main'
    entity_ids: list[str] = Field(default_factory=list)
    valid_from: float = 0
    valid_until: float | None = None
    source_version_id: str | None = None
    source_paragraph_id: str | None = None
    source_type: Literal['author','text','speech','inference'] = 'author'
    status: Literal['candidate','confirmed'] = 'candidate'
    data: dict[str, Any] = Field(default_factory=dict)
    dependencies: list[str] = Field(default_factory=list)

    @model_validator(mode='after')
    def times(self):
        if self.valid_until is not None and self.valid_until < self.valid_from:
            raise ValueError('生效结束时间不能早于开始时间')
        if self.source_type in ('text', 'speech') and not self.source_version_id:
            raise ValueError('正文或言论必须提供来源版本')
        return self


class CommitInput(BaseModel):
    version_id: str
    expected_revision: int
    idempotency_key: str = Field(min_length=1, max_length=100)
    accepted_memory_ids: list[str] = Field(default_factory=list)
    memory_delta: list[RecordInput] = Field(default_factory=list)
    override_reason: str = ''


class ContextInput(BaseModel):
    chapter_id: str
    task: str = ''
    pov: str | None = None
    entities: list[str] = Field(default_factory=list)
    story_time: float | None = None
    token_limit: int = Field(default=8000, ge=256, le=500000)


class ProviderInput(BaseModel):
    name: str = Field(min_length=1)
    base_url: str
    model: str = Field(min_length=1)
    api_key: str | None = None
    context_limit: int = Field(default=32000, ge=1024)
    max_output: int = Field(default=4096, ge=128, le=100000)
    input_price: float | None = Field(default=None, ge=0)
    output_price: float | None = Field(default=None, ge=0)
    embedding_model: str | None = None
    extra_body: dict = Field(default_factory=dict)

    @model_validator(mode='after')
    def url(self):
        from urllib.parse import urlparse
        p=urlparse(self.base_url)
        if p.scheme not in ('http','https') or not p.hostname or p.username or p.password or p.query or p.fragment:
            raise ValueError('模型地址必须是没有凭据和查询参数的 HTTP(S) 地址')
        if set(self.extra_body)-{'thinking','reasoning_effort','top_p','frequency_penalty','presence_penalty','response_format'}:
            raise ValueError('额外参数只能配置 thinking、reasoning_effort、top_p、frequency_penalty、presence_penalty、response_format')
        return self


class RoleConfig(BaseModel):
    provider_id: str | None = None
    prompt: str = ''
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_output: int | None = Field(default=None, ge=128, le=100000)


class ProfileInput(BaseModel):
    name: str = Field(min_length=1)
    roles: dict[str, RoleConfig] = Field(default_factory=dict)
    max_revisions: int = Field(default=2, ge=0, le=2)
    review_dimensions: list[str] = Field(default_factory=list)


class RunInput(BaseModel):
    chapter_id: str
    task: str = Field(min_length=1, max_length=50000)
    provider_id: str
    token_budget: int = Field(ge=100, le=10000000)
    money_budget: float | None = Field(default=None, gt=0)
    profile_id: str | None = None
    pov: str | None = None
    entities: list[str] = Field(default_factory=list)
    story_time: float | None = None
    candidate_count: Literal[1,3] = 1
    auto_approve_plan: bool = False


class ScenePlan(BaseModel):
    pov: str = ''
    story_time: float | None = None
    location: str = ''
    goal: str
    obstacle: str
    action: str
    turn: str
    cause: str
    cost: str
    state_changes: list[str] = Field(default_factory=list)
    revelations: list[str] = Field(default_factory=list)


class ChapterPlan(BaseModel):
    title: str
    goal: str
    scenes: list[ScenePlan] = Field(min_length=1)
    promises: list[str] = Field(default_factory=list)
    protected_events: list[str] = Field(default_factory=list)


class PlansOutput(BaseModel):
    plans: list[ChapterPlan] = Field(min_length=1, max_length=3)


class ReviewIssue(BaseModel):
    severity: Literal['critical','warning','suggestion']
    category: str
    description: str
    paragraph_id: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    suggestion: str = ''
    basis: Literal['observed_conflict','missing_cause','future_risk','creative_detail','preference'] = 'observed_conflict'
    quote: str = ''


class ReviewOutput(BaseModel):
    issues: list[ReviewIssue]
    summary: str


class IssueVerdict(BaseModel):
    issue_index: int = Field(ge=0)
    verdict: Literal['confirmed','warning','dismissed']
    reason: str = Field(min_length=1)


class IssueVerdicts(BaseModel):
    verdicts: list[IssueVerdict]


class DraftOutput(BaseModel):
    content: str = Field(min_length=1, max_length=500000)
    plan_changed: bool = False
    change_reason: str = ''


class MemoryItem(BaseModel):
    kind: Kind
    title: str
    content: str
    quote: str = Field(min_length=1)
    source_type: Literal['text','speech','inference'] = 'text'
    entity_ids: list[str] = Field(default_factory=list)
    valid_from: float | None = None
    data: dict = Field(default_factory=dict)
    dependencies: list[str] = Field(default_factory=list)


class MemoryOutput(BaseModel):
    records: list[MemoryItem]
