"""OpenAI-compatible model client for AI Novel Studio.

The historical class name is kept for compatibility with existing imports.
"""
from typing import Any, Dict, List, Optional
import httpx


class DeepSeekClient:
    """Client for DeepSeek API."""

    # Model pricing per 1M tokens (USD)
    MODEL_PRICING = {
        "flash": {"input": 0.27, "output": 1.10},
        "pro": {"input": 2.19, "output": 8.76},
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.deepseek.com/v1",
        provider: str = "deepseek",
        model_flash: str = "deepseek-v4-flash",
        model_pro: str = "deepseek-v4-pro",
        timeout_seconds: float = 60.0,
    ):
        """Initialize DeepSeek client.

        Args:
            api_key: DeepSeek API key.
            base_url: Base URL for API requests.

        Raises:
            ValueError: If API key is not provided.
        """
        if not api_key:
            raise ValueError("API key is required")

        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.provider = provider
        self.model_names = {"flash": model_flash, "pro": model_pro}
        self.timeout_seconds = timeout_seconds

    def get_model_name(self, model_type: str) -> str:
        """Get the full model name for a model type.

        Args:
            model_type: Type of model ('flash' or 'pro').

        Returns:
            Full model name.

        Raises:
            ValueError: If model type is unknown.
        """
        if model_type not in self.model_names:
            raise ValueError(f"Unknown model type: {model_type}")
        return self.model_names[model_type]

    def calculate_cost(
        self,
        model_type: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> float:
        """Calculate cost for a model call.

        Args:
            model_type: Type of model ('flash' or 'pro').
            prompt_tokens: Number of input tokens.
            completion_tokens: Number of output tokens.

        Returns:
            Cost in USD.
        """
        if model_type not in self.MODEL_PRICING:
            raise ValueError(f"Unknown model type: {model_type}")

        pricing = self.MODEL_PRICING[model_type]
        input_cost = (prompt_tokens / 1_000_000) * pricing["input"]
        output_cost = (completion_tokens / 1_000_000) * pricing["output"]

        return input_cost + output_cost

    async def _make_request(self, **kwargs) -> Dict[str, Any]:
        """Make an API request to DeepSeek.

        This is a placeholder that should be overridden or mocked.
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=kwargs,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            return response.json()

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model_type: str = "flash",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Create a chat completion.

        Args:
            messages: List of message dictionaries.
            model_type: Type of model ('flash' or 'pro').
            temperature: Sampling temperature.
            max_tokens: Maximum tokens to generate.
            response_format: Response format specification.

        Returns:
            Formatted response dictionary.
        """
        model_name = self.get_model_name(model_type)

        request_params = {
            "model": model_name,
            "messages": messages,
            "temperature": temperature,
        }

        if max_tokens is not None:
            request_params["max_tokens"] = max_tokens

        if response_format is not None:
            request_params["response_format"] = response_format

        response = await self._make_request(**request_params)

        return {
            "content": response["choices"][0]["message"]["content"],
            "model": model_name,
            "usage": response["usage"],
        }
