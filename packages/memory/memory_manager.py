"""Memory Manager for AI Novel Studio."""
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from packages.database.models import (
    WorldRule,
    TimelineEvent,
    CharacterState,
    Foreshadowing,
    StyleGuide,
    Chapter,
)


class MemoryManager:
    """Manages all memory systems for novel writing."""

    def __init__(self, db: Session):
        """Initialize MemoryManager.

        Args:
            db: SQLAlchemy database session.

        Raises:
            ValueError: If database session is not provided.
        """
        if not db:
            raise ValueError("Database session is required")

        self.db = db

    # Canon Memory (硬设定库)

    def add_world_rule(
        self,
        novel_id: int,
        rule_id: str,
        content: str,
        priority: str = "medium",
        category: Optional[str] = None,
        created_by: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> int:
        """Add a world rule to the canon.

        Args:
            novel_id: Novel ID.
            rule_id: Unique rule identifier.
            content: Rule content.
            priority: Priority level ('high', 'medium', 'low').
            category: Rule category.
            created_by: Creator identifier.
            notes: Additional notes.

        Returns:
            ID of the created rule.
        """
        rule = WorldRule(
            novel_id=novel_id,
            rule_id=rule_id,
            content=content,
            priority=priority,
            category=category,
            created_by=created_by,
            notes=notes,
        )
        self.db.add(rule)
        self.db.flush()
        return rule.id

    def get_world_rules(
        self,
        novel_id: int,
        active_only: bool = False,
        category: Optional[str] = None,
    ) -> List[WorldRule]:
        """Get world rules for a novel.

        Args:
            novel_id: Novel ID.
            active_only: If True, return only active rules.
            category: Filter by category.

        Returns:
            List of world rules.
        """
        query = self.db.query(WorldRule).filter(WorldRule.novel_id == novel_id)

        if active_only:
            query = query.filter(WorldRule.is_active == True)

        if category:
            query = query.filter(WorldRule.category == category)

        return query.all()

    # Timeline Memory (时间线)

    def add_timeline_event(
        self,
        chapter_id: int,
        novel_id: int,
        date_in_story: str,
        location: str,
        events: Optional[List[str]] = None,
        state_changes: Optional[List[str]] = None,
        duration: Optional[str] = None,
        weather: Optional[str] = None,
        importance: Optional[str] = None,
    ) -> int:
        """Add a timeline event.

        Args:
            chapter_id: Chapter ID.
            novel_id: Novel ID.
            date_in_story: Date within the story.
            location: Location of the event.
            events: List of events that occurred.
            state_changes: List of state changes.
            duration: Duration of the event.
            weather: Weather conditions.
            importance: Importance level.

        Returns:
            ID of the created event.
        """
        event = TimelineEvent(
            chapter_id=chapter_id,
            novel_id=novel_id,
            date_in_story=date_in_story,
            location=location,
            events=events,
            state_changes=state_changes,
            duration=duration,
            weather=weather,
            importance=importance,
        )
        self.db.add(event)
        self.db.flush()
        return event.id

    def get_timeline_for_chapter(self, chapter_id: int) -> List[TimelineEvent]:
        """Get timeline events for a chapter.

        Args:
            chapter_id: Chapter ID.

        Returns:
            List of timeline events.
        """
        return self.db.query(TimelineEvent).filter(
            TimelineEvent.chapter_id == chapter_id
        ).all()

    def get_timeline_for_novel(
        self,
        novel_id: int,
        limit: Optional[int] = None,
    ) -> List[TimelineEvent]:
        """Get timeline events for a novel.

        Args:
            novel_id: Novel ID.
            limit: Maximum number of events to return.

        Returns:
            List of timeline events.
        """
        query = self.db.query(TimelineEvent).filter(
            TimelineEvent.novel_id == novel_id
        ).order_by(TimelineEvent.id)

        if limit:
            query = query.limit(limit)

        return query.all()

    # Character State Memory (人物状态)

    def update_character_state(
        self,
        character_id: int,
        chapter_id: int,
        current_knowledge: Optional[List[str]] = None,
        emotion: Optional[str] = None,
        injury: Optional[str] = None,
        trust_level: Optional[str] = None,
        relationship_changes: Optional[Dict[str, str]] = None,
        inventory_changes: Optional[List[str]] = None,
    ) -> int:
        """Update character state after a chapter.

        Args:
            character_id: Character ID.
            chapter_id: Chapter ID.
            current_knowledge: What the character currently knows.
            emotion: Current emotional state.
            injury: Current injuries.
            trust_level: Trust level.
            relationship_changes: Changes in relationships.
            inventory_changes: Changes in inventory.

        Returns:
            ID of the created state.
        """
        state = CharacterState(
            character_id=character_id,
            chapter_id=chapter_id,
            current_knowledge=current_knowledge,
            emotion=emotion,
            injury=injury,
            trust_level=trust_level,
            relationship_changes=relationship_changes,
            inventory_changes=inventory_changes,
        )
        self.db.add(state)
        self.db.flush()
        return state.id

    def get_character_state_at_chapter(
        self,
        character_id: int,
        chapter_id: int,
    ) -> Optional[CharacterState]:
        """Get character state at a specific chapter.

        Args:
            character_id: Character ID.
            chapter_id: Chapter ID.

        Returns:
            Character state or None.
        """
        return self.db.query(CharacterState).filter(
            CharacterState.character_id == character_id,
            CharacterState.chapter_id <= chapter_id,
        ).order_by(CharacterState.chapter_id.desc()).first()

    # Foreshadowing Ledger (伏笔账本)

    def add_foreshadowing(
        self,
        novel_id: int,
        foreshadowing_id: str,
        introduced_at_chapter: int,
        content: str,
        intended_payoff_chapter: Optional[int] = None,
        intended_payoff_content: Optional[str] = None,
        related_characters: Optional[List[str]] = None,
        importance: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> int:
        """Add a foreshadowing.

        Args:
            novel_id: Novel ID.
            foreshadowing_id: Unique foreshadowing identifier.
            introduced_at_chapter: Chapter where foreshadowing was introduced.
            content: Foreshadowing content.
            intended_payoff_chapter: Planned chapter for payoff.
            intended_payoff_content: Planned payoff content.
            related_characters: Related characters.
            importance: Importance level.
            notes: Additional notes.

        Returns:
            ID of the created foreshadowing.
        """
        foreshadowing = Foreshadowing(
            novel_id=novel_id,
            foreshadowing_id=foreshadowing_id,
            introduced_at_chapter=introduced_at_chapter,
            content=content,
            intended_payoff_chapter=intended_payoff_chapter,
            intended_payoff_content=intended_payoff_content,
            related_characters=related_characters,
            importance=importance,
            notes=notes,
        )
        self.db.add(foreshadowing)
        self.db.flush()
        return foreshadowing.id

    def get_open_foreshadowings(self, novel_id: int) -> List[Foreshadowing]:
        """Get open foreshadowings for a novel.

        Args:
            novel_id: Novel ID.

        Returns:
            List of open foreshadowings.
        """
        return self.db.query(Foreshadowing).filter(
            Foreshadowing.novel_id == novel_id,
            Foreshadowing.status == "open",
        ).all()

    def resolve_foreshadowing(
        self,
        foreshadowing_id: str,
        chapter_id: int,
    ) -> bool:
        """Resolve a foreshadowing.

        Args:
            foreshadowing_id: Foreshadowing identifier.
            chapter_id: Chapter where foreshadowing was resolved.

        Returns:
            True if successful.
        """
        foreshadowing = self.db.query(Foreshadowing).filter(
            Foreshadowing.foreshadowing_id == foreshadowing_id,
        ).first()

        if foreshadowing:
            foreshadowing.status = "resolved"
            foreshadowing.actual_payoff_chapter = chapter_id
            return True

        return False

    # Style Memory (文风记忆)

    def add_style_guide(
        self,
        novel_id: int,
        name: str,
        description: Optional[str] = None,
        narrative_pov: Optional[str] = None,
        sentence_length_preference: Optional[str] = None,
        dialogue_density: Optional[str] = None,
        description_intensity: Optional[str] = None,
        rhythm_preference: Optional[str] = None,
        forbidden_words: Optional[List[str]] = None,
        forbidden_phrases: Optional[List[str]] = None,
        preferred_sentence_patterns: Optional[List[str]] = None,
        character_voice_guidelines: Optional[Dict[str, str]] = None,
        platform_specific_rules: Optional[Dict[str, str]] = None,
    ) -> int:
        """Add a style guide.

        Args:
            novel_id: Novel ID.
            name: Style guide name.
            description: Description.
            narrative_pov: Narrative point of view.
            sentence_length_preference: Sentence length preference.
            dialogue_density: Dialogue density.
            description_intensity: Description intensity.
            rhythm_preference: Rhythm preference.
            forbidden_words: List of forbidden words.
            forbidden_phrases: List of forbidden phrases.
            preferred_sentence_patterns: Preferred sentence patterns.
            character_voice_guidelines: Character voice guidelines.
            platform_specific_rules: Platform-specific rules.

        Returns:
            ID of the created style guide.
        """
        guide = StyleGuide(
            novel_id=novel_id,
            name=name,
            description=description,
            narrative_pov=narrative_pov,
            sentence_length_preference=sentence_length_preference,
            dialogue_density=dialogue_density,
            description_intensity=description_intensity,
            rhythm_preference=rhythm_preference,
            forbidden_words=forbidden_words,
            forbidden_phrases=forbidden_phrases,
            preferred_sentence_patterns=preferred_sentence_patterns,
            character_voice_guidelines=character_voice_guidelines,
            platform_specific_rules=platform_specific_rules,
        )
        self.db.add(guide)
        self.db.flush()
        return guide.id

    def get_active_style_guide(self, novel_id: int) -> Optional[StyleGuide]:
        """Get the active style guide for a novel.

        Args:
            novel_id: Novel ID.

        Returns:
            Active style guide or None.
        """
        return self.db.query(StyleGuide).filter(
            StyleGuide.novel_id == novel_id,
            StyleGuide.is_active == True,
        ).first()

    # Context Pack Builder

    def build_context_pack(
        self,
        chapter_id: int,
        novel_id: int,
        chapter_goal: str,
        previous_chapter_summary: Optional[str] = None,
        chapter_card: Optional[Dict[str, Any]] = None,
        recent_chapters_count: int = 3,
    ) -> Dict[str, Any]:
        """Build a context pack for chapter generation.

        Args:
            chapter_id: Current chapter ID.
            novel_id: Novel ID.
            chapter_goal: Goal for the current chapter.
            previous_chapter_summary: Summary of the previous chapter.
            chapter_card: Chapter card if available.
            recent_chapters_count: Number of recent chapters to include.

        Returns:
            Context pack dictionary.
        """
        # Get world rules
        world_rules = self.get_world_rules(novel_id, active_only=True)

        # Get timeline for current chapter
        timeline = self.get_timeline_for_chapter(chapter_id)

        # Get character states (simplified - in real implementation,
        # you'd get states for all relevant characters)
        character_states = None

        # Get open foreshadowings
        open_foreshadowings = self.get_open_foreshadowings(novel_id)

        # Get active style guide
        style_guide = self.get_active_style_guide(novel_id)

        # Build context pack
        context_pack = {
            "chapter_goal": chapter_goal,
            "previous_chapter_summary": previous_chapter_summary,
            "world_rules": [
                {"content": rule.content, "priority": rule.priority}
                for rule in world_rules
            ],
            "timeline": [
                {
                    "date": event.date_in_story,
                    "location": event.location,
                    "events": event.events,
                }
                for event in timeline
            ],
            "character_states": character_states,
            "open_foreshadowings": [
                {
                    "id": fs.foreshadowing_id,
                    "content": fs.content,
                    "introduced_at": fs.introduced_at_chapter,
                }
                for fs in open_foreshadowings
            ],
            "style_guide": {
                "narrative_pov": style_guide.narrative_pov if style_guide else None,
                "forbidden_words": style_guide.forbidden_words if style_guide else [],
                "forbidden_phrases": style_guide.forbidden_phrases if style_guide else [],
                "sentence_length_preference": style_guide.sentence_length_preference if style_guide else None,
                "dialogue_density": style_guide.dialogue_density if style_guide else None,
            } if style_guide else None,
        }

        # Add chapter card if provided
        if chapter_card:
            context_pack["chapter_card"] = chapter_card

        return context_pack
