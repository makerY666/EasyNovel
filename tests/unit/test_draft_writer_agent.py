"""Tests for the Draft Writer Agent."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from packages.agents.draft_writer_agent import DraftWriterAgent
from packages.models.model_gateway import ModelGateway


class TestDraftWriterAgentInitialization:
    """Tests for DraftWriterAgent initialization."""

    def test_agent_initializes_with_gateway(self):
        """Arrange: Create mock gateway.
        Act: Create DraftWriterAgent instance.
        Assert: Agent stores gateway correctly.
        """
        # Arrange
        mock_gateway = MagicMock()

        # Act
        agent = DraftWriterAgent(gateway=mock_gateway)

        # Assert
        assert agent.gateway == mock_gateway

    def test_agent_raises_error_without_gateway(self):
        """Arrange: Provide no gateway.
        Act: Create DraftWriterAgent instance.
        Assert: Raises ValueError.
        """
        # Arrange & Act & Assert
        with pytest.raises(ValueError, match="Gateway is required"):
            DraftWriterAgent(gateway=None)


class TestDraftWriterAgentWriting:
    """Tests for DraftWriterAgent draft writing."""

    @pytest.mark.asyncio
    async def test_write_draft_returns_text(self):
        """Arrange: Create agent with mock gateway.
        Act: Write a draft.
        Returns draft text.
        """
        # Arrange
        mock_gateway = MagicMock()
        agent = DraftWriterAgent(gateway=mock_gateway)

        mock_response = {
            "content": "深夜，李明独自走在空无一人的街道上。路灯忽明忽暗，投下摇曳的影子。他紧了紧外套，加快了脚步。\n\n突然，一阵奇怪的声音从远处传来。他停下脚步，侧耳倾听。那声音像是老式收音机的静电声，却又带着某种规律。\n\n\"这不可能……\"他喃喃自语，目光投向声音传来的方向。",
            "model": "deepseek-v4-flash",
            "usage": {"total_tokens": 500}
        }

        with patch.object(mock_gateway, 'generate', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = mock_response

            # Act
            result = await agent.write_draft(
                chapter_card={
                    "chapter_number": 1,
                    "title": "深夜的街道",
                    "chapter_goal": "介绍主角",
                    "opening_hook": "深夜，主角独自走在空无一人的街道上",
                    "main_conflict": "主角发现异常现象"
                },
                context_pack={"chapter_goal": "介绍主角"},
                style_guide={"narrative_pov": "第三人称有限视角"}
            )

        # Assert
        assert isinstance(result, str)
        assert len(result) > 0
        assert "李明" in result

    @pytest.mark.asyncio
    async def test_write_draft_uses_correct_task(self):
        """Arrange: Create agent with mock gateway.
        Act: Write a draft.
        Assert: Uses 'draft_writer' task.
        """
        # Arrange
        mock_gateway = MagicMock()
        agent = DraftWriterAgent(gateway=mock_gateway)

        mock_response = {
            "content": "Draft content",
            "model": "deepseek-v4-flash",
            "usage": {"total_tokens": 100}
        }

        with patch.object(mock_gateway, 'generate', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = mock_response

            # Act
            await agent.write_draft(
                chapter_card={"chapter_number": 1},
                context_pack={},
                style_guide={}
            )

        # Assert
        call_args = mock_generate.call_args
        assert call_args[1]["task"] == "draft_writer"

    @pytest.mark.asyncio
    async def test_write_draft_passes_parameters(self):
        """Arrange: Create agent with mock gateway.
        Act: Write a draft with custom parameters.
        Assert: Passes parameters correctly.
        """
        # Arrange
        mock_gateway = MagicMock()
        agent = DraftWriterAgent(gateway=mock_gateway)

        mock_response = {
            "content": "Draft content",
            "model": "deepseek-v4-flash",
            "usage": {"total_tokens": 100}
        }

        with patch.object(mock_gateway, 'generate', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = mock_response

            # Act
            await agent.write_draft(
                chapter_card={"chapter_number": 1},
                context_pack={},
                style_guide={},
                target_word_count=3000,
                temperature=0.8
            )

        # Assert
        assert mock_generate.called

    @pytest.mark.asyncio
    async def test_write_draft_handles_api_error(self):
        """Arrange: Create agent with mock gateway that raises error.
        Act: Write a draft.
        Assert: Propagates error.
        """
        # Arrange
        mock_gateway = MagicMock()
        agent = DraftWriterAgent(gateway=mock_gateway)

        with patch.object(mock_gateway, 'generate', new_callable=AsyncMock) as mock_generate:
            mock_generate.side_effect = Exception("API Error")

            # Act & Assert
            with pytest.raises(Exception, match="API Error"):
                await agent.write_draft(
                    chapter_card={"chapter_number": 1},
                    context_pack={},
                    style_guide={}
                )


class TestDraftWriterAgentPromptBuilding:
    """Tests for DraftWriterAgent prompt building."""

    def test_build_prompt_includes_chapter_card(self):
        """Arrange: Create agent.
        Act: Build prompt.
        Assert: Includes chapter card information.
        """
        # Arrange
        mock_gateway = MagicMock()
        agent = DraftWriterAgent(gateway=mock_gateway)

        chapter_card = {
            "chapter_number": 1,
            "title": "深夜的街道",
            "chapter_goal": "介绍主角",
            "opening_hook": "深夜，主角独自走在空无一人的街道上",
            "main_conflict": "主角发现异常现象"
        }

        # Act
        prompt = agent._build_prompt(
            chapter_card=chapter_card,
            context_pack={},
            style_guide={},
            target_word_count=3000
        )

        # Assert
        assert "深夜的街道" in prompt
        assert "介绍主角" in prompt
        assert "主角发现异常现象" in prompt

    def test_build_prompt_includes_style_guide(self):
        """Arrange: Create agent.
        Act: Build prompt.
        Assert: Includes style guide information.
        """
        # Arrange
        mock_gateway = MagicMock()
        agent = DraftWriterAgent(gateway=mock_gateway)

        style_guide = {
            "narrative_pov": "第三人称有限视角",
            "forbidden_words": ["他妈的", "草"],
            "forbidden_phrases": ["他不知道的是……"]
        }

        # Act
        prompt = agent._build_prompt(
            chapter_card={"chapter_number": 1},
            context_pack={},
            style_guide=style_guide,
            target_word_count=3000
        )

        # Assert
        assert "第三人称有限视角" in prompt
        assert "他妈的" in prompt
        assert "他不知道的是……" in prompt

    def test_build_prompt_includes_target_word_count(self):
        """Arrange: Create agent.
        Act: Build prompt.
        Assert: Includes target word count.
        """
        # Arrange
        mock_gateway = MagicMock()
        agent = DraftWriterAgent(gateway=mock_gateway)

        # Act
        prompt = agent._build_prompt(
            chapter_card={"chapter_number": 1},
            context_pack={},
            style_guide={},
            target_word_count=3000
        )

        # Assert
        assert "3000" in prompt

    def test_build_prompt_includes_format_instructions(self):
        """Arrange: Create agent.
        Act: Build prompt.
        Assert: Includes writing instructions.
        """
        # Arrange
        mock_gateway = MagicMock()
        agent = DraftWriterAgent(gateway=mock_gateway)

        # Act
        prompt = agent._build_prompt(
            chapter_card={"chapter_number": 1},
            context_pack={},
            style_guide={},
            target_word_count=3000
        )

        # Assert
        assert "章节卡" in prompt
        assert "不得新增" in prompt or "不能新增" in prompt or "不要新增" in prompt
