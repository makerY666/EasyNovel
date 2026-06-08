"""Tests for the LangGraph Workflow."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from packages.workflow.chapter_workflow import ChapterWorkflow


class TestChapterWorkflowInitialization:
    """Tests for ChapterWorkflow initialization."""

    def test_workflow_initializes_with_agents(self):
        """Arrange: Create mock agents.
        Act: Create ChapterWorkflow instance.
        Assert: Workflow stores agents correctly.
        """
        # Arrange
        mock_chapter_planner = MagicMock()
        mock_draft_writer = MagicMock()
        mock_style_polisher = MagicMock()
        mock_memory_manager = MagicMock()

        # Act
        workflow = ChapterWorkflow(
            chapter_planner=mock_chapter_planner,
            draft_writer=mock_draft_writer,
            style_polisher=mock_style_polisher,
            memory_manager=mock_memory_manager,
        )

        # Assert
        assert workflow.chapter_planner == mock_chapter_planner
        assert workflow.draft_writer == mock_draft_writer
        assert workflow.style_polisher == mock_style_polisher
        assert workflow.memory_manager == mock_memory_manager

    def test_workflow_raises_error_without_chapter_planner(self):
        """Arrange: Provide no chapter planner.
        Act: Create ChapterWorkflow instance.
        Assert: Raises ValueError.
        """
        # Arrange & Act & Assert
        with pytest.raises(ValueError, match="Chapter planner is required"):
            ChapterWorkflow(
                chapter_planner=None,
                draft_writer=MagicMock(),
                style_polisher=MagicMock(),
                memory_manager=MagicMock(),
            )


class TestChapterWorkflowExecution:
    """Tests for ChapterWorkflow execution."""

    @pytest.mark.asyncio
    async def test_execute_returns_workflow_state(self):
        """Arrange: Create workflow with mock agents.
        Act: Execute workflow.
        Assert: Returns workflow state with all stages.
        """
        # Arrange
        mock_chapter_planner = MagicMock()
        mock_draft_writer = MagicMock()
        mock_style_polisher = MagicMock()
        mock_memory_manager = MagicMock()

        # Mock chapter planner
        mock_chapter_planner.plan_chapter = AsyncMock(return_value={
            "chapter_number": 1,
            "title": "Test Chapter",
            "chapter_goal": "Test goal",
            "opening_hook": "Test hook",
            "main_conflict": "Test conflict"
        })

        # Mock draft writer
        mock_draft_writer.write_draft = AsyncMock(return_value="Draft content")

        # Mock style polisher
        mock_style_polisher.polish = AsyncMock(return_value={
            "polished_text": "Polished content",
            "style_changes": ["Change 1"],
            "facts_changed": [],
            "risk_notes": [],
            "quality_score": {"naturalness": 8.0}
        })

        # Mock memory manager
        mock_memory_manager.build_context_pack.return_value = {"chapter_goal": "Test"}

        workflow = ChapterWorkflow(
            chapter_planner=mock_chapter_planner,
            draft_writer=mock_draft_writer,
            style_polisher=mock_style_polisher,
            memory_manager=mock_memory_manager,
        )

        # Act
        result = await workflow.execute(
            novel_id=1,
            chapter_number=1,
            previous_chapter_summary="Previous chapter summary"
        )

        # Assert
        assert "chapter_card" in result
        assert "draft_text" in result
        assert "polished_text" in result
        assert "style_changes" in result
        assert "quality_score" in result

    @pytest.mark.asyncio
    async def test_execute_calls_chapter_planner(self):
        """Arrange: Create workflow with mock agents.
        Act: Execute workflow.
        Assert: Calls chapter planner with correct arguments.
        """
        # Arrange
        mock_chapter_planner = MagicMock()
        mock_draft_writer = MagicMock()
        mock_style_polisher = MagicMock()
        mock_memory_manager = MagicMock()

        mock_chapter_planner.plan_chapter = AsyncMock(return_value={
            "chapter_number": 1,
            "title": "Test",
            "chapter_goal": "Test",
            "opening_hook": "Test",
            "main_conflict": "Test"
        })
        mock_draft_writer.write_draft = AsyncMock(return_value="Draft")
        mock_style_polisher.polish = AsyncMock(return_value={
            "polished_text": "Polished",
            "style_changes": [],
            "facts_changed": [],
            "risk_notes": [],
            "quality_score": {}
        })
        mock_memory_manager.build_context_pack.return_value = {}

        workflow = ChapterWorkflow(
            chapter_planner=mock_chapter_planner,
            draft_writer=mock_draft_writer,
            style_polisher=mock_style_polisher,
            memory_manager=mock_memory_manager,
        )

        # Act
        await workflow.execute(
            novel_id=1,
            chapter_number=1,
            previous_chapter_summary="Previous"
        )

        # Assert
        mock_chapter_planner.plan_chapter.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_calls_draft_writer(self):
        """Arrange: Create workflow with mock agents.
        Act: Execute workflow.
        Assert: Calls draft writer with chapter card.
        """
        # Arrange
        mock_chapter_planner = MagicMock()
        mock_draft_writer = MagicMock()
        mock_style_polisher = MagicMock()
        mock_memory_manager = MagicMock()

        chapter_card = {
            "chapter_number": 1,
            "title": "Test",
            "chapter_goal": "Test",
            "opening_hook": "Test",
            "main_conflict": "Test"
        }

        mock_chapter_planner.plan_chapter = AsyncMock(return_value=chapter_card)
        mock_draft_writer.write_draft = AsyncMock(return_value="Draft")
        mock_style_polisher.polish = AsyncMock(return_value={
            "polished_text": "Polished",
            "style_changes": [],
            "facts_changed": [],
            "risk_notes": [],
            "quality_score": {}
        })
        mock_memory_manager.build_context_pack.return_value = {}

        workflow = ChapterWorkflow(
            chapter_planner=mock_chapter_planner,
            draft_writer=mock_draft_writer,
            style_polisher=mock_style_polisher,
            memory_manager=mock_memory_manager,
        )

        # Act
        await workflow.execute(
            novel_id=1,
            chapter_number=1,
            previous_chapter_summary="Previous"
        )

        # Assert
        call_args = mock_draft_writer.write_draft.call_args
        assert call_args[1]["chapter_card"] == chapter_card

    @pytest.mark.asyncio
    async def test_execute_calls_style_polisher(self):
        """Arrange: Create workflow with mock agents.
        Act: Execute workflow.
        Assert: Calls style polisher with draft text.
        """
        # Arrange
        mock_chapter_planner = MagicMock()
        mock_draft_writer = MagicMock()
        mock_style_polisher = MagicMock()
        mock_memory_manager = MagicMock()

        mock_chapter_planner.plan_chapter = AsyncMock(return_value={
            "chapter_number": 1,
            "title": "Test",
            "chapter_goal": "Test",
            "opening_hook": "Test",
            "main_conflict": "Test"
        })
        mock_draft_writer.write_draft = AsyncMock(return_value="Draft content")
        mock_style_polisher.polish = AsyncMock(return_value={
            "polished_text": "Polished",
            "style_changes": [],
            "facts_changed": [],
            "risk_notes": [],
            "quality_score": {}
        })
        mock_memory_manager.build_context_pack.return_value = {}

        workflow = ChapterWorkflow(
            chapter_planner=mock_chapter_planner,
            draft_writer=mock_draft_writer,
            style_polisher=mock_style_polisher,
            memory_manager=mock_memory_manager,
        )

        # Act
        await workflow.execute(
            novel_id=1,
            chapter_number=1,
            previous_chapter_summary="Previous"
        )

        # Assert
        call_args = mock_style_polisher.polish.call_args
        assert call_args[1]["draft_text"] == "Draft content"

    @pytest.mark.asyncio
    async def test_execute_handles_chapter_planner_error(self):
        """Arrange: Create workflow with failing chapter planner.
        Act: Execute workflow.
        Assert: Raises error.
        """
        # Arrange
        mock_chapter_planner = MagicMock()
        mock_draft_writer = MagicMock()
        mock_style_polisher = MagicMock()
        mock_memory_manager = MagicMock()

        mock_chapter_planner.plan_chapter = AsyncMock(side_effect=Exception("Planning failed"))
        mock_memory_manager.build_context_pack.return_value = {}

        workflow = ChapterWorkflow(
            chapter_planner=mock_chapter_planner,
            draft_writer=mock_draft_writer,
            style_polisher=mock_style_polisher,
            memory_manager=mock_memory_manager,
        )

        # Act & Assert
        with pytest.raises(Exception, match="Planning failed"):
            await workflow.execute(
                novel_id=1,
                chapter_number=1,
                previous_chapter_summary="Previous"
            )


class TestChapterWorkflowStateManagement:
    """Tests for ChapterWorkflow state management."""

    @pytest.mark.asyncio
    async def test_workflow_state_tracks_progress(self):
        """Arrange: Create workflow with mock agents.
        Act: Execute workflow.
        Assert: State tracks progress through stages.
        """
        # Arrange
        mock_chapter_planner = MagicMock()
        mock_draft_writer = MagicMock()
        mock_style_polisher = MagicMock()
        mock_memory_manager = MagicMock()

        mock_chapter_planner.plan_chapter = AsyncMock(return_value={
            "chapter_number": 1,
            "title": "Test",
            "chapter_goal": "Test",
            "opening_hook": "Test",
            "main_conflict": "Test"
        })
        mock_draft_writer.write_draft = AsyncMock(return_value="Draft")
        mock_style_polisher.polish = AsyncMock(return_value={
            "polished_text": "Polished",
            "style_changes": [],
            "facts_changed": [],
            "risk_notes": [],
            "quality_score": {}
        })
        mock_memory_manager.build_context_pack.return_value = {}

        workflow = ChapterWorkflow(
            chapter_planner=mock_chapter_planner,
            draft_writer=mock_draft_writer,
            style_polisher=mock_style_polisher,
            memory_manager=mock_memory_manager,
        )

        # Act
        result = await workflow.execute(
            novel_id=1,
            chapter_number=1,
            previous_chapter_summary="Previous"
        )

        # Assert
        assert "current_stage" in result
        assert result["current_stage"] == "completed"
