"""Tests for the Human Style Polisher Agent."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from packages.agents.human_style_polisher_agent import HumanStylePolisherAgent
from packages.models.model_gateway import ModelGateway


class TestHumanStylePolisherAgentInitialization:
    """Tests for HumanStylePolisherAgent initialization."""

    def test_agent_initializes_with_gateway(self):
        """Arrange: Create mock gateway.
        Act: Create HumanStylePolisherAgent instance.
        Assert: Agent stores gateway correctly.
        """
        # Arrange
        mock_gateway = MagicMock()

        # Act
        agent = HumanStylePolisherAgent(gateway=mock_gateway)

        # Assert
        assert agent.gateway == mock_gateway

    def test_agent_raises_error_without_gateway(self):
        """Arrange: Provide no gateway.
        Act: Create HumanStylePolisherAgent instance.
        Assert: Raises ValueError.
        """
        # Arrange & Act & Assert
        with pytest.raises(ValueError, match="Gateway is required"):
            HumanStylePolisherAgent(gateway=None)


class TestHumanStylePolisherAgentPolishing:
    """Tests for HumanStylePolisherAgent polishing."""

    @pytest.mark.asyncio
    async def test_polish_returns_polished_text(self):
        """Arrange: Create agent with mock gateway.
        Act: Polish a draft.
        Assert: Returns polished text.
        """
        # Arrange
        mock_gateway = MagicMock()
        agent = HumanStylePolisherAgent(gateway=mock_gateway)

        mock_response = {
            "content": '''
            {
                "polished_text": "深夜，李明独自走在空无一人的街道上。路灯忽明忽暗，投下摇曳的影子。他紧了紧外套，加快了脚步。\\n\\n突然，一阵奇怪的声音从远处传来。他停下脚步，侧耳倾听。那声音像是老式收音机的静电声，却又带着某种规律。\\n\\n\\"这不可能……\\"他喃喃自语，目光投向声音传来的方向。",
                "style_changes": [
                    "删除了多余的解释性旁白",
                    "增强了对话中的潜台词",
                    "调整了段落节奏"
                ],
                "facts_changed": [],
                "risk_notes": [
                    "第3段新增了轻微心理描写，不影响剧情事实"
                ],
                "quality_score": {
                    "naturalness": 8.5,
                    "character_voice": 8.0,
                    "rhythm": 8.2,
                    "cliche_control": 7.8
                }
            }
            ''',
            "model": "deepseek-v4-pro",
            "usage": {"total_tokens": 1000}
        }

        with patch.object(mock_gateway, 'generate', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = mock_response

            # Act
            result = await agent.polish(
                draft_text="深夜，李明独自走在空无一人的街道上。路灯忽明忽暗，投下摇曳的影子。他紧了紧外套，加快了脚步。\n\n突然，一阵奇怪的声音从远处传来。他停下脚步，侧耳倾听。那声音像是老式收音机的静电声，却又带着某种规律。\n\n\"这不可能……\"他喃喃自语，目光投向声音传来的方向。",
                chapter_card={"chapter_number": 1},
                style_guide={"narrative_pov": "第三人称有限视角"},
                character_voice_cards=[],
                protected_facts=[],
                forbidden_changes=[],
                target_platform="番茄小说",
                polish_level="medium"
            )

        # Assert
        assert "polished_text" in result
        assert "style_changes" in result
        assert "quality_score" in result
        assert len(result["polished_text"]) > 0

    @pytest.mark.asyncio
    async def test_polish_uses_correct_task(self):
        """Arrange: Create agent with mock gateway.
        Act: Polish a draft.
        Assert: Uses 'style_polisher' task.
        """
        # Arrange
        mock_gateway = MagicMock()
        agent = HumanStylePolisherAgent(gateway=mock_gateway)

        mock_response = {
            "content": '{"polished_text": "Polished", "style_changes": [], "facts_changed": [], "risk_notes": [], "quality_score": {"naturalness": 8.0, "character_voice": 8.0, "rhythm": 8.0, "cliche_control": 8.0}}',
            "model": "deepseek-v4-pro",
            "usage": {"total_tokens": 100}
        }

        with patch.object(mock_gateway, 'generate', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = mock_response

            # Act
            await agent.polish(
                draft_text="Draft text",
                chapter_card={},
                style_guide={},
                character_voice_cards=[],
                protected_facts=[],
                forbidden_changes=[],
                target_platform="番茄小说",
                polish_level="medium"
            )

        # Assert
        call_args = mock_generate.call_args
        assert call_args[1]["task"] == "style_polisher"

    @pytest.mark.asyncio
    async def test_polish_handles_invalid_json(self):
        """Arrange: Create agent with mock gateway returning invalid JSON.
        Act: Polish a draft.
        Assert: Raises ValueError.
        """
        # Arrange
        mock_gateway = MagicMock()
        agent = HumanStylePolisherAgent(gateway=mock_gateway)

        mock_response = {
            "content": "This is not JSON",
            "model": "deepseek-v4-pro",
            "usage": {"total_tokens": 100}
        }

        with patch.object(mock_gateway, 'generate', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = mock_response

            # Act & Assert
            with pytest.raises(ValueError, match="Invalid JSON"):
                await agent.polish(
                    draft_text="Draft text",
                    chapter_card={},
                    style_guide={},
                    character_voice_cards=[],
                    protected_facts=[],
                    forbidden_changes=[],
                    target_platform="番茄小说",
                    polish_level="medium"
                )

    @pytest.mark.asyncio
    async def test_polish_validates_required_fields(self):
        """Arrange: Create agent with mock gateway returning incomplete JSON.
        Act: Polish a draft.
        Assert: Raises ValueError for missing fields.
        """
        # Arrange
        mock_gateway = MagicMock()
        agent = HumanStylePolisherAgent(gateway=mock_gateway)

        mock_response = {
            "content": '{"polished_text": "Polished"}',
            "model": "deepseek-v4-pro",
            "usage": {"total_tokens": 100}
        }

        with patch.object(mock_gateway, 'generate', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = mock_response

            # Act & Assert
            with pytest.raises(ValueError, match="Missing required field"):
                await agent.polish(
                    draft_text="Draft text",
                    chapter_card={},
                    style_guide={},
                    character_voice_cards=[],
                    protected_facts=[],
                    forbidden_changes=[],
                    target_platform="番茄小说",
                    polish_level="medium"
                )


class TestHumanStylePolisherAgentPromptBuilding:
    """Tests for HumanStylePolisherAgent prompt building."""

    def test_build_prompt_includes_draft_text(self):
        """Arrange: Create agent.
        Act: Build prompt.
        Assert: Includes draft text.
        """
        # Arrange
        mock_gateway = MagicMock()
        agent = HumanStylePolisherAgent(gateway=mock_gateway)

        # Act
        prompt = agent._build_prompt(
            draft_text="这是初稿内容",
            chapter_card={},
            style_guide={},
            character_voice_cards=[],
            protected_facts=[],
            forbidden_changes=[],
            target_platform="番茄小说",
            polish_level="medium"
        )

        # Assert
        assert "这是初稿内容" in prompt

    def test_build_prompt_includes_style_guide(self):
        """Arrange: Create agent.
        Act: Build prompt.
        Assert: Includes style guide information.
        """
        # Arrange
        mock_gateway = MagicMock()
        agent = HumanStylePolisherAgent(gateway=mock_gateway)

        style_guide = {
            "forbidden_words": ["他妈的"],
            "forbidden_phrases": ["他不知道的是……"]
        }

        # Act
        prompt = agent._build_prompt(
            draft_text="Draft",
            chapter_card={},
            style_guide=style_guide,
            character_voice_cards=[],
            protected_facts=[],
            forbidden_changes=[],
            target_platform="番茄小说",
            polish_level="medium"
        )

        # Assert
        assert "他妈的" in prompt
        assert "他不知道的是……" in prompt

    def test_build_prompt_includes_polish_level(self):
        """Arrange: Create agent.
        Act: Build prompt.
        Assert: Includes polish level.
        """
        # Arrange
        mock_gateway = MagicMock()
        agent = HumanStylePolisherAgent(gateway=mock_gateway)

        # Act
        prompt = agent._build_prompt(
            draft_text="Draft",
            chapter_card={},
            style_guide={},
            character_voice_cards=[],
            protected_facts=[],
            forbidden_changes=[],
            target_platform="番茄小说",
            polish_level="heavy"
        )

        # Assert
        assert "heavy" in prompt

    def test_build_prompt_includes_hard_rules(self):
        """Arrange: Create agent.
        Act: Build prompt.
        Assert: Includes hard rules.
        """
        # Arrange
        mock_gateway = MagicMock()
        agent = HumanStylePolisherAgent(gateway=mock_gateway)

        # Act
        prompt = agent._build_prompt(
            draft_text="Draft",
            chapter_card={},
            style_guide={},
            character_voice_cards=[],
            protected_facts=[],
            forbidden_changes=[],
            target_platform="番茄小说",
            polish_level="medium"
        )

        # Assert
        assert "不得改变剧情事实" in prompt or "不能改变剧情事实" in prompt
        assert "不得新增" in prompt or "不能新增" in prompt
