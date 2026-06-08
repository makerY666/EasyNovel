"""Tests for the Memory System."""
import pytest
from unittest.mock import MagicMock, patch
from packages.memory.memory_manager import MemoryManager


class TestMemoryManagerInitialization:
    """Tests for MemoryManager initialization."""

    def test_manager_initializes_with_database(self):
        """Arrange: Create mock database session.
        Act: Create MemoryManager instance.
        Assert: Manager stores database session.
        """
        # Arrange
        mock_db = MagicMock()

        # Act
        manager = MemoryManager(db=mock_db)

        # Assert
        assert manager.db == mock_db

    def test_manager_raises_error_without_database(self):
        """Arrange: Provide no database.
        Act: Create MemoryManager instance.
        Assert: Raises ValueError.
        """
        # Arrange & Act & Assert
        with pytest.raises(ValueError, match="Database session is required"):
            MemoryManager(db=None)


class TestCanonMemory:
    """Tests for Canon Memory (硬设定库)."""

    def test_add_world_rule(self):
        """Arrange: Create manager with mock database.
        Act: Add a world rule.
        Assert: Rule is stored correctly.
        """
        # Arrange
        mock_db = MagicMock()
        mock_rule = MagicMock()
        mock_rule.id = 1
        mock_db.add.return_value = None
        mock_db.flush.return_value = None

        # Mock the WorldRule constructor
        with patch('packages.memory.memory_manager.WorldRule') as MockWorldRule:
            MockWorldRule.return_value = mock_rule
            manager = MemoryManager(db=mock_db)

            # Act
            rule_id = manager.add_world_rule(
                novel_id=1,
                rule_id="rule_001",
                content="能力不能凭空升级，必须通过代价触发。",
                priority="high",
                category="power_system"
            )

        # Assert
        assert rule_id == 1
        mock_db.add.assert_called_once()

    def test_get_world_rules(self):
        """Arrange: Create manager with mock database containing rules.
        Act: Get world rules.
        Assert: Returns list of rules.
        """
        # Arrange
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value.all.return_value = [
            MagicMock(content="Rule 1"),
            MagicMock(content="Rule 2")
        ]
        mock_db.query.return_value = mock_query

        manager = MemoryManager(db=mock_db)

        # Act
        rules = manager.get_world_rules(novel_id=1)

        # Assert
        assert len(rules) == 2

    def test_get_active_rules_only(self):
        """Arrange: Create manager with mock database.
        Act: Get active world rules.
        Assert: Filters by is_active=True.
        """
        # Arrange
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value.filter.return_value.all.return_value = [
            MagicMock(content="Active Rule")
        ]
        mock_db.query.return_value = mock_query

        manager = MemoryManager(db=mock_db)

        # Act
        rules = manager.get_world_rules(novel_id=1, active_only=True)

        # Assert
        assert len(rules) == 1


class TestTimelineMemory:
    """Tests for Timeline Memory."""

    def test_add_timeline_event(self):
        """Arrange: Create manager with mock database.
        Act: Add a timeline event.
        Assert: Event is stored correctly.
        """
        # Arrange
        mock_db = MagicMock()
        mock_event = MagicMock()
        mock_event.id = 1
        mock_db.add.return_value = None
        mock_db.flush.return_value = None

        # Mock the TimelineEvent constructor
        with patch('packages.memory.memory_manager.TimelineEvent') as MockTimelineEvent:
            MockTimelineEvent.return_value = mock_event
            manager = MemoryManager(db=mock_db)

            # Act
            event_id = manager.add_timeline_event(
                chapter_id=1,
                novel_id=1,
                date_in_story="第一天晚上",
                location="城市街道",
                events=["主角发现异常信号"],
                state_changes=["主角获得线索A"]
            )

        # Assert
        assert event_id == 1
        mock_db.add.assert_called_once()

    def test_get_timeline_for_chapter(self):
        """Arrange: Create manager with mock database.
        Act: Get timeline events for a chapter.
        Assert: Returns events for the chapter.
        """
        # Arrange
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value.all.return_value = [
            MagicMock(date_in_story="第一天晚上")
        ]
        mock_db.query.return_value = mock_query

        manager = MemoryManager(db=mock_db)

        # Act
        events = manager.get_timeline_for_chapter(chapter_id=1)

        # Assert
        assert len(events) == 1


class TestCharacterStateMemory:
    """Tests for Character State Memory."""

    def test_update_character_state(self):
        """Arrange: Create manager with mock database.
        Act: Update character state.
        Assert: State is updated correctly.
        """
        # Arrange
        mock_db = MagicMock()
        mock_state = MagicMock()
        mock_state.id = 1
        mock_db.add.return_value = None
        mock_db.flush.return_value = None

        # Mock the CharacterState constructor
        with patch('packages.memory.memory_manager.CharacterState') as MockCharacterState:
            MockCharacterState.return_value = mock_state
            manager = MemoryManager(db=mock_db)

            # Act
            state_id = manager.update_character_state(
                character_id=1,
                chapter_id=1,
                current_knowledge=["知道妹妹失踪与公司有关"],
                emotion="紧张",
                injury="无",
                trust_level="中等"
            )

        # Assert
        assert state_id == 1
        mock_db.add.assert_called_once()

    def test_get_character_state_at_chapter(self):
        """Arrange: Create manager with mock database.
        Act: Get character state at a specific chapter.
        Assert: Returns the state.
        """
        # Arrange
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value.order_by.return_value.first.return_value = MagicMock(
            emotion="紧张"
        )
        mock_db.query.return_value = mock_query

        manager = MemoryManager(db=mock_db)

        # Act
        state = manager.get_character_state_at_chapter(character_id=1, chapter_id=5)

        # Assert
        assert state is not None


class TestForeshadowingMemory:
    """Tests for Foreshadowing Ledger."""

    def test_add_foreshadowing(self):
        """Arrange: Create manager with mock database.
        Act: Add a foreshadowing.
        Assert: Foreshadowing is stored correctly.
        """
        # Arrange
        mock_db = MagicMock()
        mock_foreshadowing = MagicMock()
        mock_foreshadowing.id = 1
        mock_db.add.return_value = None
        mock_db.flush.return_value = None

        # Mock the Foreshadowing constructor
        with patch('packages.memory.memory_manager.Foreshadowing') as MockForeshadowing:
            MockForeshadowing.return_value = mock_foreshadowing
            manager = MemoryManager(db=mock_db)

            # Act
            fs_id = manager.add_foreshadowing(
                novel_id=1,
                foreshadowing_id="f023",
                introduced_at_chapter=7,
                content="旧收音机只在凌晨2:17自动响起",
                intended_payoff_chapter=42,
                intended_payoff_content="揭示它是信号接收器",
                related_characters=["主角", "管理员"]
            )

        # Assert
        assert fs_id == 1
        mock_db.add.assert_called_once()

    def test_get_open_foreshadowings(self):
        """Arrange: Create manager with mock database.
        Act: Get open foreshadowings.
        Assert: Returns only open foreshadowings.
        """
        # Arrange
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value.all.return_value = [
            MagicMock(foreshadowing_id="f023", status="open")
        ]
        mock_db.query.return_value = mock_query

        manager = MemoryManager(db=mock_db)

        # Act
        foreshadowings = manager.get_open_foreshadowings(novel_id=1)

        # Assert
        assert len(foreshadowings) == 1

    def test_resolve_foreshadowing(self):
        """Arrange: Create manager with mock database.
        Act: Resolve a foreshadowing.
        Assert: Status is updated to 'resolved'.
        """
        # Arrange
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_filter.first.return_value = MagicMock(status="open")
        mock_query.filter.return_value = mock_filter
        mock_db.query.return_value = mock_query

        manager = MemoryManager(db=mock_db)

        # Act
        success = manager.resolve_foreshadowing(foreshadowing_id="f023", chapter_id=42)

        # Assert
        assert success is True


class TestStyleMemory:
    """Tests for Style Memory."""

    def test_add_style_guide(self):
        """Arrange: Create manager with mock database.
        Act: Add a style guide.
        Assert: Style guide is stored correctly.
        """
        # Arrange
        mock_db = MagicMock()
        mock_guide = MagicMock()
        mock_guide.id = 1
        mock_db.add.return_value = None
        mock_db.flush.return_value = None

        # Mock the StyleGuide constructor
        with patch('packages.memory.memory_manager.StyleGuide') as MockStyleGuide:
            MockStyleGuide.return_value = mock_guide
            manager = MemoryManager(db=mock_db)

            # Act
            guide_id = manager.add_style_guide(
                novel_id=1,
                name="网文风格指南",
                narrative_pov="第三人称有限视角",
                sentence_length_preference="medium",
                dialogue_density="high",
                forbidden_words=["他妈的", "草"]
            )

        # Assert
        assert guide_id == 1
        mock_db.add.assert_called_once()

    def test_get_active_style_guide(self):
        """Arrange: Create manager with mock database.
        Act: Get active style guide.
        Assert: Returns the active guide.
        """
        # Arrange
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value.filter.return_value.first.return_value = MagicMock(
            name="网文风格指南"
        )
        mock_db.query.return_value = mock_query

        manager = MemoryManager(db=mock_db)

        # Act
        guide = manager.get_active_style_guide(novel_id=1)

        # Assert
        assert guide is not None


class TestContextPackBuilder:
    """Tests for Context Pack Builder."""

    def test_build_context_pack(self):
        """Arrange: Create manager with mock database.
        Act: Build context pack for a chapter.
        Assert: Returns context pack with all required fields.
        """
        # Arrange
        mock_db = MagicMock()
        manager = MemoryManager(db=mock_db)

        # Mock all the database queries
        with patch.object(manager, 'get_world_rules', return_value=[]), \
             patch.object(manager, 'get_timeline_for_chapter', return_value=[]), \
             patch.object(manager, 'get_character_state_at_chapter', return_value=None), \
             patch.object(manager, 'get_open_foreshadowings', return_value=[]), \
             patch.object(manager, 'get_active_style_guide', return_value=None):

            # Act
            context_pack = manager.build_context_pack(
                chapter_id=1,
                novel_id=1,
                chapter_goal="介绍主角",
                previous_chapter_summary="上一章摘要"
            )

        # Assert
        assert "chapter_goal" in context_pack
        assert "previous_chapter_summary" in context_pack
        assert "world_rules" in context_pack
        assert "timeline" in context_pack
        assert "character_states" in context_pack
        assert "open_foreshadowings" in context_pack
        assert "style_guide" in context_pack

    def test_build_context_pack_with_chapter_card(self):
        """Arrange: Create manager with mock database.
        Act: Build context pack with chapter card.
        Assert: Includes chapter card in context pack.
        """
        # Arrange
        mock_db = MagicMock()
        manager = MemoryManager(db=mock_db)

        chapter_card = {
            "chapter_goal": "介绍主角",
            "opening_hook": "深夜，主角独自走在空无一人的街道上",
            "main_conflict": "主角发现异常现象"
        }

        with patch.object(manager, 'get_world_rules', return_value=[]), \
             patch.object(manager, 'get_timeline_for_chapter', return_value=[]), \
             patch.object(manager, 'get_character_state_at_chapter', return_value=None), \
             patch.object(manager, 'get_open_foreshadowings', return_value=[]), \
             patch.object(manager, 'get_active_style_guide', return_value=None):

            # Act
            context_pack = manager.build_context_pack(
                chapter_id=1,
                novel_id=1,
                chapter_goal="介绍主角",
                previous_chapter_summary="上一章摘要",
                chapter_card=chapter_card
            )

        # Assert
        assert "chapter_card" in context_pack
        assert context_pack["chapter_card"] == chapter_card
