"""Tests for React frontend structure."""
import os


class TestFrontendFiles:
    def test_package_json(self):
        assert os.path.exists("apps/web/package.json")

    def test_public_index(self):
        assert os.path.exists("apps/web/public/index.html")

    def test_src_index(self):
        assert os.path.exists("apps/web/src/index.tsx")

    def test_src_app(self):
        assert os.path.exists("apps/web/src/App.tsx")

    def test_pages_exist(self):
        for f in ["Dashboard.tsx", "Projects.tsx", "NovelEditor.tsx", "ChapterWorkbench.tsx"]:
            assert os.path.exists(f"apps/web/src/pages/{f}"), f"Missing {f}"

    def test_api_client(self):
        assert os.path.exists("apps/web/src/api/client.ts")

    def test_api_types(self):
        assert os.path.exists("apps/web/src/api/types.ts")
