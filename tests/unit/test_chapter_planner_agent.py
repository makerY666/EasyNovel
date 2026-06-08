"""Tests for the Chapter Planner Agent."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from packages.agents.chapter_planner_agent import ChapterPlannerAgent
from packages.models.model_gateway import ModelGateway


class TestChapterPlannerAgentInitialization:
    """Tests for ChapterPlannerAgent initialization."""

    def test_agent_initializes_with_gateway(self):
        """Arrange: Create mock gateway.
        Act: Create ChapterPlannerAgent instance.
        Assert: Agent stores gateway correctly.
        """
        # Arrange
        mock_gateway = MagicMock()

        # Act
        agent = ChapterPlannerAgent(gateway=mock_gateway)

        # Assert
        assert agent.gateway == mock_gateway

    def test_agent_raises_error_without_gateway(self):
        """Arrange: Provide no gateway.
        Act: Create ChapterPlannerAgent instance.
        Assert: Raises ValueError.
        """
        # Arrange & Act & Assert
        with pytest.raises(ValueError, match="Gateway is required"):
            ChapterPlannerAgent(gateway=None)


class TestChapterPlannerAgentPlanning:
    """Tests for ChapterPlannerAgent chapter planning."""

    @pytest.mark.asyncio
    async def test_plan_chapter_returns_chapter_card(self):
        """Arrange: Create agent with mock gateway.
        Act: Plan a chapter.
        Assert: Returns structured chapter card.
        """
        # Arrange
        mock_gateway = MagicMock()
        agent = ChapterPlannerAgent(gateway=mock_gateway)

        mock_response = {
            "content": '''
            {
                "chapter_number": 1,
                "title": "深夜的街道",
                "pov": "主角",
                "chapter_goal": "介绍主角和世界观",
                "opening_hook": "深夜，主角独自走在空无一人的街道上",
                "main_conflict": "主角发现异常现象",
                "turning_point": "决定调查真相",
                "emotional_shift": "从平静到紧张",
                "new_information": ["世界并非表面那样"],
                "foreshadowing": ["旧收音机自动响起"],
                "ending_hook": "收音机传来神秘声音",
                "must_not_violate": ["主角不能突然获得超能力"]
            }
            ''',
            "model": "deepseek-v4-pro",
            "usage": {"total_tokens": 500}
        }

        with patch.object(mock_gateway, 'generate', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = mock_response

            # Act
            result = await agent.plan_chapter(
                novel_id=1,
                chapter_number=1,
                context_pack={"chapter_goal": "介绍主角"},
                previous_chapter_summary="这是第一章"
            )

        # Assert
        assert "chapter_number" in result
        assert "title" in result
        assert "chapter_goal" in result
        assert "opening_hook" in result
        assert "main_conflict" in result
        assert result["chapter_number"] == 1

    @pytest.mark.asyncio
    async def test_plan_chapter_uses_correct_task(self):
        """Arrange: Create agent with mock gateway.
        Act: Plan a chapter.
        Assert: Uses 'chapter_planner' task.
        """
        # Arrange
        mock_gateway = MagicMock()
        agent = ChapterPlannerAgent(gateway=mock_gateway)

        mock_response = {
            "content": '{"chapter_number": 1, "title": "Test", "chapter_goal": "Test goal", "opening_hook": "Test hook", "main_conflict": "Test conflict"}',
            "model": "deepseek-v4-pro",
            "usage": {"total_tokens": 100}
        }

        with patch.object(mock_gateway, 'generate', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = mock_response

            # Act
            await agent.plan_chapter(
                novel_id=1,
                chapter_number=1,
                context_pack={},
                previous_chapter_summary=""
            )

        # Assert
        call_args = mock_generate.call_args
        assert call_args[1]["task"] == "chapter_planner"

    @pytest.mark.asyncio
    async def test_plan_chapter_handles_invalid_json(self):
        """Arrange: Create agent with mock gateway returning invalid JSON.
        Act: Plan a chapter.
        Assert: Raises ValueError.
        """
        # Arrange
        mock_gateway = MagicMock()
        agent = ChapterPlannerAgent(gateway=mock_gateway)

        mock_response = {
            "content": "This is not JSON",
            "model": "deepseek-v4-pro",
            "usage": {"total_tokens": 100}
        }

        with patch.object(mock_gateway, 'generate', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = mock_response

            # Act & Assert
            with pytest.raises(ValueError, match="Invalid JSON"):
                await agent.plan_chapter(
                    novel_id=1,
                    chapter_number=1,
                    context_pack={},
                    previous_chapter_summary=""
                )

    @pytest.mark.asyncio
    async def test_plan_chapter_validates_required_fields(self):
        """Arrange: Create agent with mock gateway returning incomplete JSON.
        Act: Plan a chapter.
        Assert: Raises ValueError for missing fields.
        """
        # Arrange
        mock_gateway = MagicMock()
        agent = ChapterPlannerAgent(gateway=mock_gateway)

        mock_response = {
            "content": '{"chapter_number": 1}',
            "model": "deepseek-v4-pro",
            "usage": {"total_tokens": 100}
        }

        with patch.object(mock_gateway, 'generate', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = mock_response

            # Act & Assert
            with pytest.raises(ValueError, match="Missing required field"):
                await agent.plan_chapter(
                    novel_id=1,
                    chapter_number=1,
                    context_pack={},
                    previous_chapter_summary=""
                )


class TestChapterPlannerAgentPromptBuilding:
    """Tests for ChapterPlannerAgent prompt building."""

    def test_build_prompt_includes_context(self):
        """Arrange: Create agent.
        Act: Build prompt.
        Assert: Includes context pack information.
        """
        # Arrange
        mock_gateway = MagicMock()
        agent = ChapterPlannerAgent(gateway=mock_gateway)

        context_pack = {
            "chapter_goal": "介绍主角",
            "previous_chapter_summary": "上一章摘要",
            "world_rules": [{"content": "规则1"}],
            "style_guide": {"narrative_pov": "第三人称"}
        }

        # Act
        prompt = agent._build_prompt(
            chapter_number=1,
            context_pack=context_pack,
            previous_chapter_summary="这是第一章"
        )

        # Assert
        assert "介绍主角" in prompt
        assert "上一章摘要" in prompt
        assert "规则1" in prompt
        assert "第三人称" in prompt

    def test_build_prompt_includes_chapter_number(self):
        """Arrange: Create agent.
        Act: Build prompt.
        Assert: Includes chapter number.
        """
        # Arrange
        mock_gateway = MagicMock()
        agent = ChapterPlannerAgent(gateway=mock_gateway)

        # Act
        prompt = agent._build_prompt(
            chapter_number=5,
            context_pack={},
            previous_chapter_summary=""
        )

        # Assert
        assert "5" in prompt

    def test_build_prompt_includes_format_instructions(self):
        """Arrange: Create agent.
        Act: Build prompt.
        Assert: Includes JSON format instructions.
        """
        # Arrange
        mock_gateway = MagicMock()
        agent = ChapterPlannerAgent(gateway=mock_gateway)

        # Act
        prompt = agent._build_prompt(
            chapter_number=1,
            context_pack={},
            previous_chapter_summary=""
        )

        # Assert
        assert "JSON" in prompt or "json" in prompt
        assert "chapter_goal" in prompt
        assert "opening_hook" in prompt
