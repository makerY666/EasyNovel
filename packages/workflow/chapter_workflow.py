"""Chapter Workflow for AI Novel Studio."""
from typing import Any, Callable, Dict, Optional
from packages.agents.chapter_planner_agent import ChapterPlannerAgent
from packages.agents.draft_writer_agent import DraftWriterAgent
from packages.agents.human_style_polisher_agent import HumanStylePolisherAgent
from packages.memory.memory_manager import MemoryManager


class ChapterWorkflow:
    """Workflow for generating a single chapter.

    Supports progress reporting via an optional callback function.
    """

    def __init__(
        self,
        chapter_planner: ChapterPlannerAgent,
        draft_writer: DraftWriterAgent,
        style_polisher: HumanStylePolisherAgent,
        memory_manager: MemoryManager,
    ):
        """Initialize ChapterWorkflow."""
        if not chapter_planner:
            raise ValueError("Chapter planner is required")
        if not draft_writer:
            raise ValueError("Draft writer is required")
        if not style_polisher:
            raise ValueError("Style polisher is required")
        if not memory_manager:
            raise ValueError("Memory manager is required")

        self.chapter_planner = chapter_planner
        self.draft_writer = draft_writer
        self.style_polisher = style_polisher
        self.memory_manager = memory_manager

    async def execute(
        self,
        novel_id: int,
        chapter_number: int,
        previous_chapter_summary: Optional[str] = None,
        chapter_goal: Optional[str] = None,
        style_guide: Optional[Dict[str, Any]] = None,
        character_voice_cards: Optional[list] = None,
        protected_facts: Optional[list] = None,
        forbidden_changes: Optional[list] = None,
        target_platform: str = "番茄小说",
        polish_level: str = "medium",
        on_progress: Optional[Callable[[str, Dict[str, Any]], None]] = None,
    ) -> Dict[str, Any]:
        """Execute the chapter generation workflow.

        Args:
            novel_id: Novel ID.
            chapter_number: Chapter number.
            previous_chapter_summary: Previous chapter summary.
            chapter_goal: Goal for this chapter.
            style_guide: Style guide dictionary.
            character_voice_cards: Character voice specs.
            protected_facts: Facts that cannot be changed.
            forbidden_changes: Changes not allowed.
            target_platform: Publishing platform.
            polish_level: Polish intensity (light/medium/heavy).
            on_progress: Optional callback(stage, data) for progress updates.

        Returns:
            Workflow state dict with results from all stages.
        """
        state = {
            "novel_id": novel_id,
            "chapter_number": chapter_number,
            "current_stage": "started",
            "chapter_card": None,
            "draft_text": None,
            "polished_text": None,
            "style_changes": None,
            "quality_score": None,
        }

        def _report(stage: str, extra: Optional[Dict] = None):
            state["current_stage"] = stage
            if on_progress:
                on_progress(stage, state if extra is None else {**state, **extra})

        try:
            # Stage 1: Build context pack
            _report("building_context")
            context_pack = self.memory_manager.build_context_pack(
                chapter_id=chapter_number,
                novel_id=novel_id,
                chapter_goal=chapter_goal or "未指定",
                previous_chapter_summary=previous_chapter_summary,
            )

            # Stage 2: Plan chapter card
            _report("planning_chapter")
            chapter_card = await self.chapter_planner.plan_chapter(
                novel_id=novel_id,
                chapter_number=chapter_number,
                context_pack=context_pack,
                previous_chapter_summary=previous_chapter_summary,
            )
            state["chapter_card"] = chapter_card
            _report("chapter_card_ready", {"chapter_card": chapter_card})

            # Stage 3: Write draft
            _report("writing_draft")
            draft_text = await self.draft_writer.write_draft(
                chapter_card=chapter_card,
                context_pack=context_pack,
                style_guide=style_guide or {},
                target_word_count=3000,
            )
            state["draft_text"] = draft_text
            _report("draft_ready", {"draft_preview": draft_text[:200] + "..."})

            # Stage 4: Polish draft
            _report("polishing_draft")
            polish_result = await self.style_polisher.polish(
                draft_text=draft_text,
                chapter_card=chapter_card,
                style_guide=style_guide or {},
                character_voice_cards=character_voice_cards or [],
                protected_facts=protected_facts or [],
                forbidden_changes=forbidden_changes or [],
                target_platform=target_platform,
                polish_level=polish_level,
            )
            state["polished_text"] = polish_result["polished_text"]
            state["style_changes"] = polish_result["style_changes"]
            state["quality_score"] = polish_result["quality_score"]
            _report("completed", {"quality_score": polish_result["quality_score"]})

        except Exception as e:
            state["current_stage"] = "failed"
            state["error"] = str(e)
            _report("failed", {"error": str(e)})
            raise

        return state
