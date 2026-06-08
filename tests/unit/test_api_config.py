"""Tests for API configuration and dependencies."""
import os
import pytest
from unittest.mock import MagicMock, patch


class TestAPIConfig:
    """Tests for API configuration."""

    def test_config_loads_from_env(self):
        """Arrange: Set environment variables.
        Act: Create Settings instance.
        Assert: Values are loaded correctly.
        """
        # Arrange
        env_vars = {
            "DEEPSEEK_API_KEY": "sk-test-key-12345",
            "DATABASE_URL": "sqlite:///test.db",
            "API_HOST": "127.0.0.1",
            "API_PORT": "9000",
        }

        with patch.dict(os.environ, env_vars):
            # Import inside patch so it picks up env vars
            from apps.api.config import Settings

            # Act
            settings = Settings()

            # Assert
            assert settings.deepseek_api_key == "sk-test-key-12345"
            assert settings.database_url == "sqlite:///test.db"
            assert settings.api_host == "127.0.0.1"
            assert settings.api_port == 9000

    def test_config_has_defaults(self):
        """Arrange: Clear environment variables.
        Act: Create Settings instance.
        Assert: Default values are used.
        """
        # Arrange
        with patch.dict(os.environ, {}, clear=True):
            from apps.api.config import Settings

            # Act
            settings = Settings()

            # Assert
            assert settings.api_host == "0.0.0.0"
            assert settings.api_port == 8000
            assert settings.database_url == "sqlite:///./ai_novel_studio.db"
            assert settings.deepseek_api_key == ""

    def test_config_model_name_mapping(self):
        """Arrange: Create settings.
        Act: Access model name mapping.
        Assert: Returns correct model names.
        """
        # Arrange
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test"}, clear=False):
            from apps.api.config import Settings

            settings = Settings()

            # Assert
            assert settings.model_flash == "deepseek-v4-flash"
            assert settings.model_pro == "deepseek-v4-pro"
