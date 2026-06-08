"""Application configuration loaded from environment variables."""
import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parents[2] / ".env")


class Settings:
    """Application settings loaded from environment variables."""

    def __init__(self) -> None:
        # Model provider. DeepSeek remains the default OpenAI-compatible target.
        self.model_provider: str = os.environ.get("MODEL_PROVIDER", "deepseek")
        self.model_api_key: str = os.environ.get(
            "MODEL_API_KEY", os.environ.get("DEEPSEEK_API_KEY", "")
        )
        self.model_base_url: str = os.environ.get(
            "MODEL_BASE_URL",
            os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
        )
        self.model_flash_name: str = os.environ.get(
            "MODEL_FLASH", "deepseek-v4-flash"
        )
        self.model_pro_name: str = os.environ.get("MODEL_PRO", "deepseek-v4-pro")
        self.model_timeout_seconds: float = float(
            os.environ.get("MODEL_TIMEOUT_SECONDS", "60")
        )

        # Backward-compatible DeepSeek names.
        self.deepseek_api_key: str = os.environ.get("DEEPSEEK_API_KEY", "")
        self.deepseek_base_url: str = os.environ.get(
            "DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"
        )

        # Database
        self.database_url: str = os.environ.get(
            "DATABASE_URL", "sqlite:///./ai_novel_studio.db"
        )

        # API Server
        self.api_host: str = os.environ.get("API_HOST", "0.0.0.0")
        self.api_port: int = int(os.environ.get("API_PORT", "8000"))

        # Debug
        self.debug: bool = os.environ.get("DEBUG", "false").lower() == "true"

    @property
    def model_flash(self) -> str:
        return self.model_flash_name

    @property
    def model_pro(self) -> str:
        return self.model_pro_name

    @property
    def model_configured(self) -> bool:
        return bool(self.model_api_key and not self.model_api_key.startswith("sk-your"))
