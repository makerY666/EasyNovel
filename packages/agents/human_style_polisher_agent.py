"""Human Style Polisher Agent for AI Novel Studio."""
import json
from typing import Any, Dict, List, Optional
from packages.models.model_gateway import ModelGateway


class HumanStylePolisherAgent:
    """Agent for polishing AI-generated drafts to sound more human-written."""

    REQUIRED_FIELDS = [
        "polished_text",
        "style_changes",
        "facts_changed",
        "risk_notes",
        "quality_score",
    ]

    def __init__(self, gateway: ModelGateway):
        """Initialize HumanStylePolisherAgent.

        Args:
            gateway: Model gateway for API calls.

        Raises:
            ValueError: If gateway is not provided.
        """
        if not gateway:
            raise ValueError("Gateway is required")

        self.gateway = gateway

    async def polish(
        self,
        draft_text: str,
        chapter_card: Dict[str, Any],
        style_guide: Dict[str, Any],
        character_voice_cards: List[Dict[str, Any]],
        protected_facts: List[str],
        forbidden_changes: List[str],
        target_platform: str,
        polish_level: str = "medium",
    ) -> Dict[str, Any]:
        """Polish a draft to sound more human-written.

        Args:
            draft_text: Original draft text.
            chapter_card: Chapter card with plot information.
            style_guide: Style guide for writing.
            character_voice_cards: Character voice specifications.
            protected_facts: Facts that cannot be changed.
            forbidden_changes: Changes that are not allowed.
            target_platform: Target publishing platform.
            polish_level: Level of polishing ('light', 'medium', 'heavy').

        Returns:
            Dictionary with polished text and metadata.

        Raises:
            ValueError: If response is invalid JSON or missing required fields.
        """
        # Build prompt
        prompt = self._build_prompt(
            draft_text=draft_text,
            chapter_card=chapter_card,
            style_guide=style_guide,
            character_voice_cards=character_voice_cards,
            protected_facts=protected_facts,
            forbidden_changes=forbidden_changes,
            target_platform=target_platform,
            polish_level=polish_level,
        )

        # Generate response
        response = await self.gateway.generate(
            task="style_polisher",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )

        # Parse and validate response
        result = self._parse_response(response["content"])

        return result

    def _build_prompt(
        self,
        draft_text: str,
        chapter_card: Dict[str, Any],
        style_guide: Dict[str, Any],
        character_voice_cards: List[Dict[str, Any]],
        protected_facts: List[str],
        forbidden_changes: List[str],
        target_platform: str,
        polish_level: str,
    ) -> str:
        """Build the prompt for style polishing.

        Args:
            draft_text: Original draft text.
            chapter_card: Chapter card with plot information.
            style_guide: Style guide for writing.
            character_voice_cards: Character voice specifications.
            protected_facts: Facts that cannot be changed.
            forbidden_changes: Changes that are not allowed.
            target_platform: Target publishing platform.
            polish_level: Level of polishing.

        Returns:
            Formatted prompt string.
        """
        # Extract style guide information
        forbidden_words = style_guide.get("forbidden_words", [])
        forbidden_phrases = style_guide.get("forbidden_phrases", [])

        # Format lists
        protected_facts_text = "\n".join([f"- {fact}" for fact in protected_facts]) if protected_facts else "无"
        forbidden_changes_text = "\n".join([f"- {change}" for change in forbidden_changes]) if forbidden_changes else "无"
        forbidden_words_text = ", ".join(forbidden_words) if forbidden_words else "无"
        forbidden_phrases_text = "\n".join([f"- {phrase}" for phrase in forbidden_phrases]) if forbidden_phrases else "无"

        # Format character voice cards
        character_voices_text = ""
        if character_voice_cards:
            for card in character_voice_cards:
                name = card.get("name", "未知")
                voice_style = card.get("voice_style", {})
                tone = voice_style.get("tone", "未指定")
                sentence_length = voice_style.get("sentence_length", "未指定")
                taboo_words = voice_style.get("taboo_words", [])
                character_voices_text += f"""
### {name}
- 语气: {tone}
- 句子长度: {sentence_length}
- 禁用词: {', '.join(taboo_words) if taboo_words else '无'}
"""
        else:
            character_voices_text = "暂无特定人物口吻要求。"

        # Build prompt
        prompt = f"""你是一个专业的小说润色师。你的任务是在不改变剧情事实的前提下，把 AI 初稿改成更像真实作者写出来的、有节奏、有取舍、有个人风格的文本。

## 初稿

{draft_text}

## 润色要求

### 目标平台
{target_platform}

### 润色级别
{polish_level}

### 受保护的事实（不得改变）
{protected_facts_text}

### 禁止的修改
{forbidden_changes_text}

### 禁用词
{forbidden_words_text}

### 禁用短语
{forbidden_phrases_text}

### 人物口吻要求
{character_voices_text}

## 硬规则（必须遵守）

1. **不得改变剧情事实**：所有剧情事件必须保持原样
2. **不得新增关键设定**：不能引入新的重要设定
3. **不得让人物说出不符合人物卡的话**：人物言行必须符合其性格
4. **不得把普通网文润色成散文腔**：保持网文风格
5. **不得过度使用比喻**：适度使用修辞手法
6. **不得把所有句子改得一样工整**：保持句式变化
7. **必须保留原章节的冲突推进**：不能削弱冲突
8. **如果发现初稿剧情问题，只能标注，不能私自大改**：剧情问题需要人工处理

## 润色任务

### 重点清除的 AI 味
- "他不知道的是……"
- "命运的齿轮开始转动。"
- "空气仿佛凝固了。"
- "这一刻，他终于明白……"
- "眼神中闪过一丝复杂。"
- "心中涌起一股难以言喻的情绪。"
- "大脑飞速运转。"
- "事情远没有这么简单。"
- "真正的考验才刚刚开始。"

### 应该做的事
1. 删除 AI 味解释句
2. 打散过于整齐的句式
3. 增加动作、停顿、眼神、环境细节
4. 增强对话潜台词
5. 让不同人物说话方式不同
6. 减少"他感到震惊""她很愤怒"这类直白说明
7. 把抽象情绪改成可感知动作
8. 控制段落长短变化
9. 保留适度不完美的人类表达

## 输出格式

请返回 JSON 格式的结果：

```json
{{
    "polished_text": "润色后的正文",
    "style_changes": [
        "修改1: 描述",
        "修改2: 描述"
    ],
    "facts_changed": [
        "如果发现剧情事实被改变，在此列出"
    ],
    "risk_notes": [
        "风险提示1",
        "风险提示2"
    ],
    "quality_score": {{
        "naturalness": 8.5,
        "character_voice": 8.0,
        "rhythm": 8.2,
        "cliche_control": 7.8
    }}
}}
```

请直接返回 JSON 格式的结果，不要添加其他说明。"""

        return prompt

    def _parse_response(self, content: str) -> Dict[str, Any]:
        """Parse and validate the response from the model.

        Args:
            content: Raw response content from the model.

        Returns:
            Validated result dictionary.

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
            result = json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON response: {e}")

        # Validate required fields
        for field in self.REQUIRED_FIELDS:
            if field not in result:
                raise ValueError(f"Missing required field: {field}")

        return result
