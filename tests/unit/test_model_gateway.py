"""Tests for the ModelGateway."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from packages.models.model_gateway import ModelGateway
from packages.models.deepseek_client import DeepSeekClient


class TestModelGatewayInitialization:
    """Tests for ModelGateway initialization."""

    def test_gateway_initializes_with_client(self):
        """Arrange: Create DeepSeekClient.
        Act: Create ModelGateway instance.
        Assert: Gateway stores client correctly.
        """
        # Arrange
        client = DeepSeekClient(api_key="sk-test")

        # Act
        gateway = ModelGateway(client=client)

        # Assert
        assert gateway.client == client

    def test_gateway_raises_error_without_client(self):
        """Arrange: Provide no client.
        Act: Create ModelGateway instance.
        Assert: Raises ValueError.
        """
        # Arrange & Act & Assert
        with pytest.raises(ValueError, match="Client is required"):
            ModelGateway(client=None)


class TestModelGatewayRouting:
    """Tests for ModelGateway model routing."""

    def test_route_selects_pro_for_complex_tasks(self):
        """Arrange: Create gateway with routing rules.
        Act: Route a complex task.
        Assert: Returns 'pro' model type.
        """
        # Arrange
        client = DeepSeekClient(api_key="sk-test")
        gateway = ModelGateway(client=client)

        # Act
        model_type = gateway.route("story_bible")

        # Assert
        assert model_type == "pro"

    def test_route_selects_flash_for_simple_tasks(self):
        """Arrange: Create gateway with routing rules.
        Act: Route a simple task.
        Assert: Returns 'flash' model type.
        """
        # Arrange
        client = DeepSeekClient(api_key="sk-test")
        gateway = ModelGateway(client=client)

        # Act
        model_type = gateway.route("draft_writer")

        # Assert
        assert model_type == "flash"

    def test_route_raises_for_unknown_task(self):
        """Arrange: Create gateway.
        Act: Route an unknown task.
        Assert: Raises ValueError.
        """
        # Arrange
        client = DeepSeekClient(api_key="sk-test")
        gateway = ModelGateway(client=client)

        # Act & Assert
        with pytest.raises(ValueError, match="Unknown task"):
            gateway.route("unknown_task")

    def test_route_returns_correct_model_for_all_tasks(self):
        """Arrange: Create gateway.
        Act: Route all known tasks.
        Assert: Each task maps to correct model type.
        """
        # Arrange
        client = DeepSeekClient(api_key="sk-test")
        gateway = ModelGateway(client=client)

        # Act & Assert
        assert gateway.route("story_bible") == "pro"
        assert gateway.route("character") == "pro"
        assert gateway.route("chapter_planner") == "pro"
        assert gateway.route("plot_editor") == "pro"
        assert gateway.route("quality_judge") == "pro"
        assert gateway.route("editor_in_chief") == "pro"
        assert gateway.route("draft_writer") == "flash"
        assert gateway.route("continuity_auditor") == "flash"
        assert gateway.route("style_polisher") == "pro"


class TestModelGatewayCompletion:
    """Tests for ModelGateway chat completion."""

    @pytest.mark.asyncio
    async def test_generate_uses_routed_model(self):
        """Arrange: Mock client and gateway.
        Act: Call generate.
        Assert: Uses correct model type based on routing.
        """
        # Arrange
        client = DeepSeekClient(api_key="sk-test")
        gateway = ModelGateway(client=client)

        mock_response = {
            "content": "Generated content",
            "model": "deepseek-v4-pro",
            "usage": {"prompt_tokens": 50, "completion_tokens": 50, "total_tokens": 100}
        }

        with patch.object(client, 'chat_completion', new_callable=AsyncMock) as mock_completion:
            mock_completion.return_value = mock_response

            # Act
            result = await gateway.generate(
                task="story_bible",
                messages=[{"role": "user", "content": "Create world rules"}]
            )

        # Assert
        assert result["content"] == "Generated content"
        mock_completion.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_passes_parameters(self):
        """Arrange: Mock client and gateway.
        Act: Call generate with custom parameters.
        Assert: Passes parameters correctly.
        """
        # Arrange
        client = DeepSeekClient(api_key="sk-test")
        gateway = ModelGateway(client=client)

        mock_response = {
            "content": "Response",
            "model": "deepseek-v4-flash",
            "usage": {"prompt_tokens": 25, "completion_tokens": 25, "total_tokens": 50}
        }

        with patch.object(client, 'chat_completion', new_callable=AsyncMock) as mock_completion:
            mock_completion.return_value = mock_response

            # Act
            result = await gateway.generate(
                task="draft_writer",
                messages=[{"role": "user", "content": "Write chapter"}],
                temperature=0.8,
                max_tokens=2000
            )

        # Assert
        assert result["content"] == "Response"

    @pytest.mark.asyncio
    async def test_generate_handles_client_error(self):
        """Arrange: Mock client that raises error.
        Act: Call generate.
        Assert: Propagates error.
        """
        # Arrange
        client = DeepSeekClient(api_key="sk-test")
        gateway = ModelGateway(client=client)

        with patch.object(client, 'chat_completion', new_callable=AsyncMock) as mock_completion:
            mock_completion.side_effect = Exception("API Error")

            # Act & Assert
            with pytest.raises(Exception, match="API Error"):
                await gateway.generate(
                    task="story_bible",
                    messages=[{"role": "user", "content": "Test"}]
                )


class TestModelGatewayCostTracking:
    """Tests for ModelGateway cost tracking."""

    def test_track_cost_records_call(self):
        """Arrange: Create gateway.
        Act: Track a cost.
        Assert: Cost is recorded.
        """
        # Arrange
        client = DeepSeekClient(api_key="sk-test")
        gateway = ModelGateway(client=client)

        # Act
        gateway.track_cost(
            task="story_bible",
            model_type="pro",
            prompt_tokens=1000,
            completion_tokens=500,
            cost_usd=0.01
        )

        # Assert
        assert len(gateway.cost_history) == 1
        assert gateway.cost_history[0]["task"] == "story_bible"
        assert gateway.cost_history[0]["cost_usd"] == 0.01

    def test_get_total_cost(self):
        """Arrange: Track multiple costs.
        Act: Get total cost.
        Assert: Returns sum of all costs.
        """
        # Arrange
        client = DeepSeekClient(api_key="sk-test")
        gateway = ModelGateway(client=client)

        gateway.track_cost("task1", "flash", 100, 50, 0.001)
        gateway.track_cost("task2", "pro", 200, 100, 0.005)

        # Act
        total = gateway.get_total_cost()

        # Assert
        assert total == pytest.approx(0.006)

    def test_get_cost_by_task(self):
        """Arrange: Track costs for different tasks.
        Act: Get cost for specific task.
        Assert: Returns correct cost.
        """
        # Arrange
        client = DeepSeekClient(api_key="sk-test")
        gateway = ModelGateway(client=client)

        gateway.track_cost("story_bible", "pro", 100, 50, 0.005)
        gateway.track_cost("draft_writer", "flash", 200, 100, 0.001)
        gateway.track_cost("story_bible", "pro", 150, 75, 0.007)

        # Act
        cost = gateway.get_cost_by_task("story_bible")

        # Assert
        assert cost == pytest.approx(0.012)

    def test_reset_cost_history(self):
        """Arrange: Track some costs.
        Act: Reset cost history.
        Assert: History is empty.
        """
        # Arrange
        client = DeepSeekClient(api_key="sk-test")
        gateway = ModelGateway(client=client)

        gateway.track_cost("task1", "flash", 100, 50, 0.001)

        # Act
        gateway.reset_cost_history()

        # Assert
        assert len(gateway.cost_history) == 0
        assert gateway.get_total_cost() == 0.0
