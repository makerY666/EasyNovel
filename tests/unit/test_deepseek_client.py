"""Tests for the DeepSeek API client."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from packages.models.deepseek_client import DeepSeekClient


class TestDeepSeekClientInitialization:
    """Tests for DeepSeekClient initialization."""

    def test_client_initializes_with_api_key(self):
        """Arrange: Provide valid API key.
        Act: Create DeepSeekClient instance.
        Assert: Client stores API key correctly.
        """
        # Arrange
        api_key = "sk-test-key-12345"

        # Act
        client = DeepSeekClient(api_key=api_key)

        # Assert
        assert client.api_key == api_key
        assert client.base_url == "https://api.deepseek.com/v1"

    def test_client_initializes_with_custom_base_url(self):
        """Arrange: Provide custom base URL.
        Act: Create DeepSeekClient instance.
        Assert: Client uses custom base URL.
        """
        # Arrange
        api_key = "sk-test-key"
        base_url = "https://custom.api.com/v1"

        # Act
        client = DeepSeekClient(api_key=api_key, base_url=base_url)

        # Assert
        assert client.base_url == base_url

    def test_client_raises_error_without_api_key(self):
        """Arrange: Provide no API key.
        Act: Create DeepSeekClient instance.
        Assert: Raises ValueError.
        """
        # Arrange & Act & Assert
        with pytest.raises(ValueError, match="API key is required"):
            DeepSeekClient(api_key=None)

    def test_client_raises_error_with_empty_api_key(self):
        """Arrange: Provide empty API key.
        Act: Create DeepSeekClient instance.
        Assert: Raises ValueError.
        """
        # Arrange & Act & Assert
        with pytest.raises(ValueError, match="API key is required"):
            DeepSeekClient(api_key="")


class TestDeepSeekClientModels:
    """Tests for DeepSeekClient model selection."""

    def test_get_model_name_flash(self):
        """Arrange: Request flash model.
        Act: Get model name.
        Assert: Returns correct model name.
        """
        # Arrange
        client = DeepSeekClient(api_key="sk-test")

        # Act
        model = client.get_model_name("flash")

        # Assert
        assert model == "deepseek-v4-flash"

    def test_get_model_name_pro(self):
        """Arrange: Request pro model.
        Act: Get model name.
        Assert: Returns correct model name.
        """
        # Arrange
        client = DeepSeekClient(api_key="sk-test")

        # Act
        model = client.get_model_name("pro")

        # Assert
        assert model == "deepseek-v4-pro"

    def test_get_model_name_raises_for_unknown(self):
        """Arrange: Request unknown model type.
        Act: Get model name.
        Assert: Raises ValueError.
        """
        # Arrange
        client = DeepSeekClient(api_key="sk-test")

        # Act & Assert
        with pytest.raises(ValueError, match="Unknown model type"):
            client.get_model_name("unknown")


class TestDeepSeekClientChatCompletion:
    """Tests for DeepSeekClient chat completion."""

    @pytest.mark.asyncio
    async def test_chat_completion_returns_response(self):
        """Arrange: Mock API response.
        Act: Call chat completion.
        Assert: Returns formatted response.
        """
        # Arrange
        client = DeepSeekClient(api_key="sk-test")
        mock_response = {
            "id": "chatcmpl-123",
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "Hello! How can I help?"
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 8,
                "total_tokens": 18
            }
        }

        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            # Act
            result = await client.chat_completion(
                messages=[{"role": "user", "content": "Hello"}],
                model_type="flash"
            )

        # Assert
        assert result["content"] == "Hello! How can I help?"
        assert result["model"] == "deepseek-v4-flash"
        assert result["usage"]["total_tokens"] == 18

    @pytest.mark.asyncio
    async def test_chat_completion_with_parameters(self):
        """Arrange: Mock API response with custom parameters.
        Act: Call chat completion with temperature and max_tokens.
        Assert: Passes parameters correctly.
        """
        # Arrange
        client = DeepSeekClient(api_key="sk-test")
        mock_response = {
            "id": "chatcmpl-456",
            "choices": [{"message": {"role": "assistant", "content": "Response"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8}
        }

        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            # Act
            result = await client.chat_completion(
                messages=[{"role": "user", "content": "Test"}],
                model_type="pro",
                temperature=0.7,
                max_tokens=1000
            )

        # Assert
        assert result["model"] == "deepseek-v4-pro"
        mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_chat_completion_handles_api_error(self):
        """Arrange: Mock API error.
        Act: Call chat completion.
        Assert: Raises appropriate error.
        """
        # Arrange
        client = DeepSeekClient(api_key="sk-test")

        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = Exception("API Error: Rate limit exceeded")

            # Act & Assert
            with pytest.raises(Exception, match="API Error"):
                await client.chat_completion(
                    messages=[{"role": "user", "content": "Hello"}],
                    model_type="flash"
                )

    @pytest.mark.asyncio
    async def test_chat_completion_with_json_mode(self):
        """Arrange: Mock API response in JSON mode.
        Act: Call chat completion with JSON response format.
        Assert: Returns parsed JSON response.
        """
        # Arrange
        client = DeepSeekClient(api_key="sk-test")
        mock_response = {
            "id": "chatcmpl-789",
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": '{"key": "value"}'
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
        }

        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            # Act
            result = await client.chat_completion(
                messages=[{"role": "user", "content": "Return JSON"}],
                model_type="flash",
                response_format={"type": "json_object"}
            )

        # Assert
        assert result["content"] == '{"key": "value"}'


class TestDeepSeekClientCostCalculation:
    """Tests for cost calculation."""

    def test_calculate_cost_flash_model(self):
        """Arrange: Provide token counts for flash model.
        Act: Calculate cost.
        Assert: Returns correct cost.
        """
        # Arrange
        client = DeepSeekClient(api_key="sk-test")
        prompt_tokens = 1000
        completion_tokens = 500

        # Act
        cost = client.calculate_cost(
            model_type="flash",
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens
        )

        # Assert
        assert cost > 0
        assert isinstance(cost, float)

    def test_calculate_cost_pro_model(self):
        """Arrange: Provide token counts for pro model.
        Act: Calculate cost.
        Assert: Returns correct cost (higher than flash).
        """
        # Arrange
        client = DeepSeekClient(api_key="sk-test")
        prompt_tokens = 1000
        completion_tokens = 500

        # Act
        cost_flash = client.calculate_cost("flash", prompt_tokens, completion_tokens)
        cost_pro = client.calculate_cost("pro", prompt_tokens, completion_tokens)

        # Assert
        assert cost_pro > cost_flash

    def test_calculate_cost_zero_tokens(self):
        """Arrange: Provide zero token counts.
        Act: Calculate cost.
        Assert: Returns zero cost.
        """
        # Arrange
        client = DeepSeekClient(api_key="sk-test")

        # Act
        cost = client.calculate_cost("flash", 0, 0)

        # Assert
        assert cost == 0.0
