from contextlib import contextmanager
from datetime import datetime, timezone
from threading import RLock
from uuid import uuid4
from sqlalchemy import create_engine, event, String, Text, Integer, Float, Boolean, JSON, UniqueConstraint, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

# Alembic's environment proxy is process-wide, even for distinct SQLite files.
_migration_lock=RLock()


def uid():
    return str(uuid4())


def now():
    return datetime.now(timezone.utc).isoformat()


class Base(DeclarativeBase):
    pass


class Project(Base):
    __tablename__ = 'projects'
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    title: Mapped[str] = mapped_column(String)
    genre: Mapped[str] = mapped_column(String, default='')
    mode: Mapped[str] = mapped_column(String, default='serial')
    description: Mapped[str] = mapped_column(Text, default='')
    revision: Mapped[int] = mapped_column(Integer, default=0)
    settings: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[str] = mapped_column(String, default=now)


class Branch(Base):
    __tablename__ = 'branches'
    __table_args__ = (UniqueConstraint('project_id','id'),)
    key: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    id: Mapped[str] = mapped_column(String, default='main')
    project_id: Mapped[str] = mapped_column(String, index=True)
    name: Mapped[str] = mapped_column(String, default='主线')
    created_at: Mapped[str] = mapped_column(String, default=now)


class Chapter(Base):
    __tablename__ = 'chapters'
    __table_args__ = (UniqueConstraint('project_id','branch_id','number'),)
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(String, index=True)
    branch_id: Mapped[str] = mapped_column(String, default='main', index=True)
    number: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String)
    story_time: Mapped[float] = mapped_column(Float)
    confirmed_version_id: Mapped[str | None] = mapped_column(String, nullable=True)
    draft_version_id: Mapped[str | None] = mapped_column(String, nullable=True)
    blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[str] = mapped_column(String, default=now)


class Version(Base):
    __tablename__ = 'versions'
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    chapter_id: Mapped[str] = mapped_column(String, index=True)
    content: Mapped[str] = mapped_column(Text)
    paragraphs: Mapped[list] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String, default='draft')
    source: Mapped[str] = mapped_column(String, default='manual')
    parent_id: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[str] = mapped_column(String, default=now)


class Record(Base):
    __tablename__ = 'records'
    __table_args__ = (Index('record_context','project_id','branch_id','status','kind','valid_from'),)
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(String)
    branch_id: Mapped[str] = mapped_column(String, default='main')
    kind: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(String)
    content: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String, default='candidate')
    source_type: Mapped[str] = mapped_column(String, default='author')
    source_version_id: Mapped[str | None] = mapped_column(String, nullable=True)
    source_paragraph_id: Mapped[str | None] = mapped_column(String, nullable=True)
    valid_from: Mapped[float] = mapped_column(Float, default=0)
    valid_until: Mapped[float | None] = mapped_column(Float, nullable=True)
    entity_ids: Mapped[list] = mapped_column(JSON, default=list)
    dependencies: Mapped[list] = mapped_column(JSON, default=list)
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    supersedes_id: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[str] = mapped_column(String, default=now)


class Impact(Base):
    __tablename__ = 'impacts'
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(String, index=True)
    source_chapter_id: Mapped[str | None] = mapped_column(String, nullable=True)
    version_id: Mapped[str | None] = mapped_column(String, nullable=True)
    source_record_id: Mapped[str | None] = mapped_column(String, nullable=True)
    base_revision: Mapped[int] = mapped_column(Integer)
    items: Mapped[list] = mapped_column(JSON)
    coverage: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String, default='analyzed')
    resolved_ids: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[str] = mapped_column(String, default=now)


class Provider(Base):
    __tablename__ = 'providers'
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String)
    base_url: Mapped[str] = mapped_column(String)
    model: Mapped[str] = mapped_column(String)
    context_limit: Mapped[int] = mapped_column(Integer, default=32000)
    max_output: Mapped[int] = mapped_column(Integer, default=4096)
    input_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    output_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    embedding_model: Mapped[str | None] = mapped_column(String, nullable=True)
    has_key: Mapped[bool] = mapped_column(Boolean, default=False)
    capabilities: Mapped[dict] = mapped_column(JSON, default=dict)
    extra_body: Mapped[dict] = mapped_column(JSON, default=dict)


class Profile(Base):
    __tablename__ = 'profiles'
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String)
    roles: Mapped[dict] = mapped_column(JSON, default=dict)
    max_revisions: Mapped[int] = mapped_column(Integer, default=2)
    review_dimensions: Mapped[list] = mapped_column(JSON, default=list)


class Run(Base):
    __tablename__ = 'runs'
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(String, index=True)
    chapter_id: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default='queued')
    node: Mapped[str] = mapped_column(String, default='context')
    input_revision: Mapped[int] = mapped_column(Integer)
    request: Mapped[dict] = mapped_column(JSON)
    artifacts: Mapped[dict] = mapped_column(JSON, default=dict)
    usage: Mapped[dict] = mapped_column(JSON, default=lambda: {'input_tokens':0,'output_tokens':0,'reserved_tokens':0,'cost':0.0})
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(String, default=now)


class Call(Base):
    __tablename__ = 'model_calls'
    __table_args__ = (UniqueConstraint('run_id','call_key'),)
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    run_id: Mapped[str] = mapped_column(String, index=True)
    call_key: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default='reserved')
    provider_id: Mapped[str] = mapped_column(String)
    prompt: Mapped[str] = mapped_column(Text)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    reserved_tokens: Mapped[int] = mapped_column(Integer)
    reserved_cost: Mapped[float] = mapped_column(Float, default=0)
    usage: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[str] = mapped_column(String, default=now)


class RunEvent(Base):
    __tablename__ = 'run_events'
    seq: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String, index=True)
    event: Mapped[str] = mapped_column(String)
    data: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[str] = mapped_column(String, default=now)


class Job(Base):
    __tablename__ = 'jobs'
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(String, index=True)
    kind: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default='queued')
    total: Mapped[int] = mapped_column(Integer, default=0)
    completed: Mapped[int] = mapped_column(Integer, default=0)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


class Receipt(Base):
    __tablename__ = 'receipts'
    key: Mapped[str] = mapped_column(String, primary_key=True)
    project_id: Mapped[str] = mapped_column(String)
    payload_hash: Mapped[str] = mapped_column(String)
    result: Mapped[dict] = mapped_column(JSON)


def dump(obj):
    return {col.name:getattr(obj,col.name) for col in obj.__table__.columns}


class Database:
    def __init__(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path=path
        self.lock=RLock()
        self.engine=create_engine(f'sqlite:///{path.as_posix()}',connect_args={'check_same_thread':False,'timeout':30})
        @event.listens_for(self.engine,'connect')
        def configure(conn,_):
            conn.execute('PRAGMA journal_mode=WAL')
            conn.execute('PRAGMA foreign_keys=ON')
            conn.execute('PRAGMA busy_timeout=30000')
        self.Session=sessionmaker(self.engine,expire_on_commit=False)

    def initialize(self):
        from alembic.config import Config
        from alembic import command
        from pathlib import Path
        root=Path(__file__).resolve().parents[1]
        config=Config(str(root/'alembic.ini'))
        config.set_main_option('script_location',str(root/'migrations'))
        from alembic.script import ScriptDirectory
        from alembic.runtime.migration import MigrationContext
        with self.engine.connect() as connection:
            current=MigrationContext.configure(connection).get_current_revision()
        if current and current!=ScriptDirectory.from_config(config).get_current_head():
            from .storage import Storage
            from .config import Settings
            Storage(self,Settings(data_dir=self.path.parent)).backup(automatic=True)
        with _migration_lock,self.engine.begin() as connection:
            config.attributes['connection']=connection
            command.upgrade(config,'head')
        with self.engine.begin() as conn:
            conn.exec_driver_sql('CREATE VIRTUAL TABLE IF NOT EXISTS search_fts USING fts5(doc_id UNINDEXED, project_id UNINDEXED, branch_id UNINDEXED, title, body, tokenize="unicode61")')
        with self.write() as s:
            if not s.query(Profile).first():
                s.add(Profile(name='作者导演',roles={},max_revisions=2,review_dimensions=['人物动机','因果与代价','信息揭示','节奏','语言与对白']))
            for run in s.query(Run).filter(Run.status.in_(['queued','running'])).all():
                run.status='paused'
                run.error='上次运行意外中断，已保留成果；恢复前请检查未完成调用的预算预留。'
            for job in s.query(Job).filter(Job.status.in_(['queued','running'])).all():
                job.status='paused'

    @contextmanager
    def read(self):
        with self.Session() as s:
            yield s

    @contextmanager
    def write(self):
        with self.lock,self.Session.begin() as s:
            yield s

    def emit(self,run_id,event_name,data):
        with self.write() as s:
            e=RunEvent(run_id=run_id,event=event_name,data=data)
            s.add(e)
            s.flush()
            return e.seq
