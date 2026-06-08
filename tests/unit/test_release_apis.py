"""Release-readiness API tests for local EasyNovel workflows."""
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from apps.api.dependencies import get_db, get_deepseek_client, get_model_gateway, get_settings
from apps.api.main import app
from packages.database.models import Base
from packages.models.deepseek_client import DeepSeekClient
from packages.models.model_gateway import ModelGateway


@pytest.fixture
def client(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = Session()

    def override_get_db():
        try:
            yield db
        finally:
            pass

    monkeypatch.setenv("MODEL_API_KEY", "sk-test")
    get_settings.cache_clear()
    ds = DeepSeekClient(api_key="sk-test")
    ds._make_request = AsyncMock(
        return_value={
            "choices": [{"message": {"content": "{}"}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        }
    )
    gw = ModelGateway(client=ds)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_deepseek_client] = lambda: ds
    app.dependency_overrides[get_model_gateway] = lambda: gw
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
        db.close()
        Base.metadata.drop_all(bind=engine)
        get_settings.cache_clear()


def create_novel(client):
    project = client.post(
        "/api/v1/projects",
        json={"name": "Release Project", "target_platform": "番茄小说"},
    ).json()
    novel = client.post(
        "/api/v1/novels",
        json={"project_id": project["id"], "title": "Release Novel", "genre": "玄幻"},
    ).json()
    return project, novel


def test_chapter_versions_and_markdown_export(client):
    _, novel = create_novel(client)
    chapter = client.post(
        "/api/v1/chapters",
        json={"novel_id": novel["id"], "chapter_number": 1, "title": "第一章"},
    ).json()

    created = client.post(
        f"/api/v1/chapters/{chapter['id']}/versions",
        json={"stage": "draft", "content": "这是初稿。", "source": "manual"},
    )
    assert created.status_code == 201
    assert created.json()["version_number"] == 1

    final = client.post(
        f"/api/v1/chapters/{chapter['id']}/versions",
        json={"stage": "final", "content": "这是定稿。", "source": "manual"},
    ).json()
    assert final["word_count"] == 5

    versions = client.get(f"/api/v1/chapters/{chapter['id']}/versions").json()
    assert [item["stage"] for item in versions] == ["draft", "final"]

    exported = client.post(f"/api/v1/exports/novel/{novel['id']}?format=markdown")
    assert exported.status_code == 200
    assert "# Release Novel" in exported.text
    assert "这是定稿。" in exported.text


def test_story_bible_crud_endpoints(client):
    _, novel = create_novel(client)
    chapter = client.post(
        "/api/v1/chapters",
        json={"novel_id": novel["id"], "chapter_number": 1},
    ).json()

    character = client.post(
        "/api/v1/characters",
        json={"novel_id": novel["id"], "name": "林澈", "role": "protagonist"},
    )
    assert character.status_code == 201
    assert client.get(f"/api/v1/characters?novel_id={novel['id']}").json()[0]["name"] == "林澈"

    style = client.post(
        "/api/v1/style-guides",
        json={"novel_id": novel["id"], "name": "快节奏", "dialogue_density": "high"},
    )
    assert style.status_code == 201
    assert client.get(f"/api/v1/style-guides?novel_id={novel['id']}").json()[0]["name"] == "快节奏"

    event = client.post(
        "/api/v1/timeline-events",
        json={
            "novel_id": novel["id"],
            "chapter_id": chapter["id"],
            "date_in_story": "第一天",
            "location": "旧城",
            "events": ["主角得到线索"],
        },
    )
    assert event.status_code == 201
    assert client.get(f"/api/v1/timeline-events?novel_id={novel['id']}").json()[0]["location"] == "旧城"


def test_model_config_and_check(client):
    config = client.get("/api/v1/models/config")
    assert config.status_code == 200
    assert config.json()["api_key_configured"] is True

    check = client.post("/api/v1/models/check")
    assert check.status_code == 200
    assert check.json()["ok"] is True
