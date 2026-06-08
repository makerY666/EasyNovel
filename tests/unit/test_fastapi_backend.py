"""Tests for FastAPI backend."""
import pytest
from unittest.mock import AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from apps.api.main import app
from apps.api.dependencies import get_db, get_deepseek_client, get_model_gateway
from packages.database.models import Base
from packages.models.deepseek_client import DeepSeekClient
from packages.models.model_gateway import ModelGateway


@pytest.fixture
def test_db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = Session()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(test_db):
    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    ds = DeepSeekClient(api_key="sk-test")
    ds._make_request = AsyncMock(return_value={
        "id": "x",
        "choices": [{"message": {"role": "assistant", "content": '{"k":"v"}'}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
    })
    gw = ModelGateway(client=ds)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_deepseek_client] = lambda: ds
    app.dependency_overrides[get_model_gateway] = lambda: gw

    c = TestClient(app)
    yield c
    app.dependency_overrides.clear()


def _novel_id(client):
    pid = client.post("/api/v1/projects", json={"name": "P"}).json()["id"]
    return client.post("/api/v1/novels", json={"project_id": pid, "title": "N"}).json()["id"]


class TestHealth:
    def test_health(self, client):
        assert client.get("/health").status_code == 200


class TestProjects:
    def test_create(self, client):
        r = client.post("/api/v1/projects", json={"name": "X"})
        assert r.status_code == 201
        assert r.json()["name"] == "X"

    def test_list(self, client):
        client.post("/api/v1/projects", json={"name": "X"})
        assert len(client.get("/api/v1/projects").json()) > 0


class TestNovels:
    def test_create(self, client):
        pid = client.post("/api/v1/projects", json={"name": "P"}).json()["id"]
        assert client.post("/api/v1/novels", json={"project_id": pid, "title": "N"}).status_code == 201

    def test_list(self, client):
        pid = client.post("/api/v1/projects", json={"name": "P"}).json()["id"]
        client.post("/api/v1/novels", json={"project_id": pid, "title": "N"})
        assert len(client.get(f"/api/v1/novels?project_id={pid}").json()) > 0


class TestChapters:
    def test_create(self, client):
        nid = _novel_id(client)
        assert client.post("/api/v1/chapters", json={"novel_id": nid, "chapter_number": 1}).status_code == 201

    def test_list(self, client):
        nid = _novel_id(client)
        client.post("/api/v1/chapters", json={"novel_id": nid, "chapter_number": 1})
        assert len(client.get(f"/api/v1/chapters?novel_id={nid}").json()) > 0


class TestWorkflow:
    @pytest.mark.skip(reason="BackgroundTasks not supported in TestClient")
    def test_start_returns_202(self, client):
        nid = _novel_id(client)
        r = client.post("/api/v1/workflows/chapter", json={"novel_id": nid, "chapter_number": 1})
        assert r.status_code == 202
        assert "workflow_id" in r.json()


class TestMemory:
    def test_rules(self, client):
        nid = _novel_id(client)
        assert client.get(f"/api/v1/memory/world-rules?novel_id={nid}").status_code == 200

    def test_add_rule(self, client):
        nid = _novel_id(client)
        r = client.post("/api/v1/memory/world-rules", json={"novel_id": nid, "rule_id": "r1", "content": "test"})
        assert r.status_code == 201

    def test_timeline(self, client):
        nid = _novel_id(client)
        assert client.get(f"/api/v1/memory/timeline?novel_id={nid}").status_code == 200


class TestModelGateway:
    def test_status(self, client):
        assert client.get("/api/v1/models/status").status_code == 200

    def test_cost(self, client):
        assert client.get("/api/v1/models/cost-summary").status_code == 200
