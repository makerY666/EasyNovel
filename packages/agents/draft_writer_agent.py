"""Draft Writer Agent for AI Novel Studio."""
from typing import Any, Dict, List, Optional
from packages.models.model_gateway import ModelGateway


class DraftWriterAgent:
    """Agent for writing chapter drafts based on chapter cards."""

    def __init__(self, gateway: ModelGateway):
        """Initialize DraftWriterAgent.

        Args:
            gateway: Model gateway for API calls.

        Raises:
            ValueError: If gateway is not provided.
        """
        if not gateway:
            raise ValueError("Gateway is required")

        self.gateway = gateway

    async def write_draft(
        self,
        chapter_card: Dict[str, Any],
        context_pack: Dict[str, Any],
        style_guide: Dict[str, Any],
        target_word_count: int = 3000,
        temperature: float = 0.7,
    ) -> str:
        """Write a chapter draft based on the chapter card.

        Args:
            chapter_card: Structured chapter card.
            context_pack: Context pack with novel information.
            style_guide: Style guide for writing.
            target_word_count: Target word count for the chapter.
            temperature: Sampling temperature.

        Returns:
            Draft text string.
        """
        # Build prompt
        prompt = self._build_prompt(
            chapter_card=chapter_card,
            context_pack=context_pack,
            style_guide=style_guide,
            target_word_count=target_word_count,
        )

        # Generate response
        response = await self.gateway.generate(
            task="draft_writer",
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
        )

        return response["content"]

    def _build_prompt(
        self,
        chapter_card: Dict[str, Any],
        context_pack: Dict[str, Any],
        style_guide: Dict[str, Any],
        target_word_count: int,
    ) -> str:
        """Build the prompt for draft writing.

        Args:
            chapter_card: Structured chapter card.
            context_pack: Context pack with novel information.
            style_guide: Style guide for writing.
            target_word_count: Target word count.

        Returns:
            Formatted prompt string.
        """
        # Extract chapter card information
        chapter_number = chapter_card.get("chapter_number", 1)
        title = chapter_card.get("title", "未命名章节")
        chapter_goal = chapter_card.get("chapter_goal", "未指定")
        opening_hook = chapter_card.get("opening_hook", "")
        main_conflict = chapter_card.get("main_conflict", "")
        turning_point = chapter_card.get("turning_point", "")
        emotional_shift = chapter_card.get("emotional_shift", "")
        new_information = chapter_card.get("new_information", [])
        foreshadowing = chapter_card.get("foreshadowing", [])
        ending_hook = chapter_card.get("ending_hook", "")
        must_not_violate = chapter_card.get("must_not_violate", [])

        # Extract style guide information
        narrative_pov = style_guide.get("narrative_pov", "第三人称有限视角")
        forbidden_words = style_guide.get("forbidden_words", [])
        forbidden_phrases = style_guide.get("forbidden_phrases", [])
        sentence_length_preference = style_guide.get("sentence_length_preference", "medium")
        dialogue_density = style_guide.get("dialogue_density", "medium")

        # Format lists
        new_information_text = "\n".join([f"- {info}" for info in new_information]) if new_information else "无"
        foreshadowing_text = "\n".join([f"- {fs}" for fs in foreshadowing]) if foreshadowing else "无"
        must_not_violate_text = "\n".join([f"- {rule}" for rule in must_not_violate]) if must_not_violate else "无"
        forbidden_words_text = ", ".join(forbidden_words) if forbidden_words else "无"
        forbidden_phrases_text = "\n".join([f"- {phrase}" for phrase in forbidden_phrases]) if forbidden_phrases else "无"

        # Build prompt
        prompt = f"""你是一个专业的小说写手。请根据以下章节卡撰写第 {chapter_number} 章的初稿。

## 章节卡

### 基本信息
- 章节号: {chapter_number}
- 标题: {title}
- 章节目标: {chapter_goal}
- 目标字数: {target_word_count} 字

### 剧情要素
- 开头钩子: {opening_hook}
- 主要冲突: {main_conflict}
- 中段转折: {turning_point}
- 情绪变化: {emotional_shift}
- 章末钩子: {ending_hook}

### 新增信息
{new_information_text}

### 伏笔
{foreshadowing_text}

### 禁止事项
{must_not_violate_text}

## 文风要求

- 叙述视角: {narrative_pov}
- 句子长度偏好: {sentence_length_preference}
- 对话密度: {dialogue_density}
- 禁用词: {forbidden_words_text}
- 禁用短语:
{forbidden_phrases_text}

## 写作要求

1. **严格按章节卡写**：不得偏离章节卡中的目标和冲突
2. **不得新增重大设定**：不得引入章节卡中没有的重要设定
3. **不得改变人物关系**：保持现有人物关系不变
4. **不得提前回收伏笔**：伏笔要在指定章节才能回收
5. **每500-800字必须有一次推进**：保持剧情节奏
6. **结尾必须有具体钩子**：让读者想看下一章
7. **不得使用禁用词和禁用短语**：保持文风一致性
8. **保持人物一致性**：人物言行要符合其性格设定

## 输出要求

请直接输出小说正文，不要添加任何说明、注释或元数据。正文应该是一段连贯的叙事，包含对话、描写和动作。

开始撰写第 {chapter_number} 章："""

        return prompt
