from dataclasses import dataclass, field
from pathlib import Path
import os
import secrets


@dataclass
class Settings:
    data_dir: Path = field(default_factory=lambda: Path(os.environ.get('EASYNOVEL_DATA_DIR', str(Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'EasyNovel'))))
    token: str = field(default_factory=lambda: os.environ.get('EASYNOVEL_TOKEN') or secrets.token_urlsafe(32))
    legacy_path: Path = field(default_factory=lambda: Path(__file__).resolve().parents[1] / 'ai_novel_studio.db')
    test_mode: bool = False
    port: int = 8765

    @property
    def db_path(self):
        return self.data_dir / 'studio.sqlite3'
