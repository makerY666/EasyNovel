"""Model Gateway for AI Novel Studio."""
from typing import Any, Dict, List, Optional
from packages.models.deepseek_client import DeepSeekClient


class ModelGateway:
    """Unified model gateway with routing and cost tracking."""

    # Task to model type mapping
    TASK_ROUTING = {
        # Pro model tasks (complex, high-quality)
        "story_bible": "pro",
        "character": "pro",
        "chapter_planner": "pro",
        "plot_editor": "pro",
        "quality_judge": "pro",
        "editor_in_chief": "pro",
        "style_polisher": "pro",
        # Flash model tasks (batch, routine)
        "draft_writer": "flash",
        "continuity_auditor": "flash",
        "summary_generator": "flash",
    }

    def __init__(self, client: DeepSeekClient):
        """Initialize ModelGateway.

        Args:
            client: DeepSeek API client.

        Raises:
            ValueError: If client is not provided.
        """
        if not client:
            raise ValueError("Client is required")

        self.client = client
        self.cost_history: List[Dict[str, Any]] = []

    def route(self, task: str) -> str:
        """Route a task to the appropriate model type.

        Args:
            task: Task name.

        Returns:
            Model type ('flash' or 'pro').

        Raises:
            ValueError: If task is unknown.
        """
        if task not in self.TASK_ROUTING:
            raise ValueError(f"Unknown task: {task}")
        return self.TASK_ROUTING[task]

    async def generate(
        self,
        task: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Generate a response using the appropriate model.

        Args:
            task: Task name for routing.
            messages: List of message dictionaries.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens to generate.
            response_format: Response format specification.

        Returns:
            Response dictionary.
        """
        model_type = self.route(task)

        response = await self.client.chat_completion(
            messages=messages,
            model_type=model_type,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
        )

        # Track cost
        cost = self.client.calculate_cost(
            model_type=model_type,
            prompt_tokens=response["usage"]["prompt_tokens"],
            completion_tokens=response["usage"]["completion_tokens"],
        )

        self.track_cost(
            task=task,
            model_type=model_type,
            prompt_tokens=response["usage"]["prompt_tokens"],
            completion_tokens=response["usage"]["completion_tokens"],
            cost_usd=cost,
        )

        return response

    def track_cost(
        self,
        task: str,
        model_type: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost_usd: float,
    ) -> None:
        """Track cost for a model call.

        Args:
            task: Task name.
            model_type: Model type used.
            prompt_tokens: Number of input tokens.
            completion_tokens: Number of output tokens.
            cost_usd: Cost in USD.
        """
        self.cost_history.append({
            "task": task,
            "model_type": model_type,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "cost_usd": cost_usd,
        })

    def get_total_cost(self) -> float:
        """Get total cost of all tracked calls.

        Returns:
            Total cost in USD.
        """
        return sum(entry["cost_usd"] for entry in self.cost_history)

    def get_cost_by_task(self, task: str) -> float:
        """Get total cost for a specific task.

        Args:
            task: Task name.

        Returns:
            Total cost for the task in USD.
        """
        return sum(
            entry["cost_usd"]
            for entry in self.cost_history
            if entry["task"] == task
        )

    def reset_cost_history(self) -> None:
        """Reset cost history."""
        self.cost_history = []
