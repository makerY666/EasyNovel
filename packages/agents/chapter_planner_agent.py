"""Chapter Planner Agent for AI Novel Studio."""
import json
from typing import Any, Dict, List, Optional
from packages.models.model_gateway import ModelGateway


class ChapterPlannerAgent:
    """Agent for planning chapters with structured chapter cards."""

    REQUIRED_FIELDS = [
        "chapter_number",
        "title",
        "chapter_goal",
        "opening_hook",
        "main_conflict",
    ]

    def __init__(self, gateway: ModelGateway):
        """Initialize ChapterPlannerAgent.

        Args:
            gateway: Model gateway for API calls.

        Raises:
            ValueError: If gateway is not provided.
        """
        if not gateway:
            raise ValueError("Gateway is required")

        self.gateway = gateway

    async def plan_chapter(
        self,
        novel_id: int,
        chapter_number: int,
        context_pack: Dict[str, Any],
        previous_chapter_summary: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Plan a chapter and generate a chapter card.

        Args:
            novel_id: Novel ID.
            chapter_number: Chapter number to plan.
            context_pack: Context pack with novel information.
            previous_chapter_summary: Summary of the previous chapter.

        Returns:
            Structured chapter card dictionary.

        Raises:
            ValueError: If response is invalid JSON or missing required fields.
        """
        # Build prompt
        prompt = self._build_prompt(
            chapter_number=chapter_number,
            context_pack=context_pack,
            previous_chapter_summary=previous_chapter_summary,
        )

        # Generate response
        response = await self.gateway.generate(
            task="chapter_planner",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )

        # Parse and validate response
        chapter_card = self._parse_response(response["content"])

        return chapter_card

    def _build_prompt(
        self,
        chapter_number: int,
        context_pack: Dict[str, Any],
        previous_chapter_summary: Optional[str] = None,
    ) -> str:
        """Build the prompt for chapter planning.

        Args:
            chapter_number: Chapter number to plan.
            context_pack: Context pack with novel information.
            previous_chapter_summary: Summary of the previous chapter.

        Returns:
            Formatted prompt string.
        """
        # Extract context information
        chapter_goal = context_pack.get("chapter_goal", "未指定")
        world_rules = context_pack.get("world_rules", [])
        style_guide = context_pack.get("style_guide", {})
        character_states = context_pack.get("character_states")
        open_foreshadowings = context_pack.get("open_foreshadowings", [])

        # Format world rules
        world_rules_text = ""
        if world_rules:
            world_rules_text = "\n".join([f"- {rule.get('content', '')}" for rule in world_rules])

        # Format style guide
        style_guide_text = ""
        if style_guide:
            style_guide_text = f"""
叙述视角: {style_guide.get('narrative_pov', '未指定')}
句子长度偏好: {style_guide.get('sentence_length_preference', '未指定')}
对话密度: {style_guide.get('dialogue_density', '未指定')}
禁用词: {', '.join(style_guide.get('forbidden_words', []))}
禁用短语: {', '.join(style_guide.get('forbidden_phrases', []))}
"""

        # Format foreshadowings
        foreshadowings_text = ""
        if open_foreshadowings:
            foreshadowings_text = "\n".join([
                f"- {fs.get('id', '')}: {fs.get('content', '')}"
                for fs in open_foreshadowings
            ])

        # Build prompt
        prompt = f"""你是一个专业的小说章节规划师。请为第 {chapter_number} 章创建一个结构化的章节卡。

## 小说信息

### 章节目标
{chapter_goal}

### 上一章摘要
{previous_chapter_summary or "这是第一章，没有上一章摘要。"}

### 世界观规则
{world_rules_text or "暂无特定规则。"}

### 文风指南
{style_guide_text or "暂无特定文风要求。"}

### 未回收伏笔
{foreshadowings_text or "暂无未回收伏笔。"}

## 任务要求

请创建一个 JSON 格式的章节卡，包含以下字段：

```json
{{
    "chapter_number": 章节号,
    "title": "章节标题",
    "pov": "视角人物",
    "chapter_goal": "本章要达成的具体目标",
    "opening_hook": "开头钩子，吸引读者继续阅读",
    "main_conflict": "主要冲突",
    "turning_point": "中段转折点",
    "emotional_shift": "人物情绪变化",
    "new_information": ["新增信息列表"],
    "foreshadowing": ["伏笔列表"],
    "ending_hook": "章末钩子，让读者想看下一章",
    "must_not_violate": ["不能违反的设定列表"]
}}
```

## 注意事项

1. 章节目标必须具体、可执行
2. 开头钩子必须在前200字内抓住读者
3. 主要冲突必须足够具体，不能模糊
4. 章末钩子必须留下悬念或疑问
5. 不得违反世界观规则
6. 不得使用禁用词和禁用短语
7. 每500-800字必须有一次剧情推进

请直接返回 JSON 格式的章节卡，不要添加其他说明。"""

        return prompt

    def _parse_response(self, content: str) -> Dict[str, Any]:
        """Parse and validate the response from the model.

        Args:
            content: Raw response content from the model.

        Returns:
            Validated chapter card dictionary.

        Raises:
            ValueError: If response is invalid JSON or missing required fields.
        """
        # Try to extract JSON from the response
        content = content.strip()

        # Handle cases where response might be wrapped in markdown code blocks
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]

        content = content.strip()

        # Parse JSON
        try:
            chapter_card = json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON response: {e}")

        # Validate required fields
        for field in self.REQUIRED_FIELDS:
            if field not in chapter_card:
                raise ValueError(f"Missing required field: {field}")

        return chapter_card
