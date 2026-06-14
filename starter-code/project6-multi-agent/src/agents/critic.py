"""
批评者 Agent（可选）

对通过审校的文章进行独立评价，给出评分和详细评论。
与审校者不同，批评者更关注文章的深度、洞察力和阅读体验。
"""

import json
import logging
from typing import Optional

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)


class CriticAgent:
    """
    批评者 Agent，对文章进行深度评价和打分。

    与审校者的区别：
    - 审校者：检查错误、规范性（"是否合格"）
    - 批评者：评价质量、深度、洞察力（"是否优秀"）

    评价维度：
    1. 深度与洞察力：是否有独到见解
    2. 可读性与吸引力：是否引人入胜
    3. 信息密度：是否提供了有价值的信息
    4. 逻辑严密性：论证是否严谨
    5. 创新性：是否有新颖的角度或观点
    """

    SYSTEM_PROMPT = """你是一个资深的内容批评者，负责对文章进行深度评价。

评价维度（每项 1-10 分）：
1. 深度与洞察力：是否有独到见解，避免陈词滥调
2. 可读性与吸引力：语言是否生动，结构是否引人入胜
3. 信息密度：是否提供了足够有价值的信息
4. 逻辑严密性：论证是否严谨，有无逻辑漏洞
5. 创新性：是否有新颖的角度或观点

总分计算：各项得分的加权平均
- 深度与洞察力: 30%
- 可读性与吸引力: 25%
- 信息密度: 20%
- 逻辑严密性: 15%
- 创新性: 10%

输出 JSON 格式：
{
  "score": 8.5,
  "scores": {
    "depth": 8,
    "readability": 9,
    "information_density": 7,
    "logic": 8,
    "originality": 9
  },
  "comments": "详细的总体评价（200 字以内）",
  "highlights": ["亮点1", "亮点2"],
  "suggestions": ["改进建议1", "改进建议2"],
  "recommendation": "强烈推荐 / 推荐 / 一般 / 不推荐"
}"""

    def __init__(self, llm: Optional[ChatOpenAI] = None):
        """
        初始化批评者 Agent。

        Args:
            llm: 语言模型实例；为 None 时从环境变量初始化
        """
        import os
        if llm is None:
            self.llm = ChatOpenAI(
                model=os.getenv("MODEL_NAME", "gpt-4o-mini"),
                api_key=os.getenv("OPENAI_API_KEY", ""),
                base_url=os.getenv("OPENAI_BASE_URL", None),
                temperature=0.3,
            )
        else:
            self.llm = llm

        logger.info("批评者 Agent 初始化完成")

    def evaluate(self, topic: str, article: str) -> dict:
        """
        评价文章，返回评分和评论。

        Args:
            topic: 文章主题
            article: 文章全文（Markdown 格式）

        Returns:
            评价结果字典，包含 score、comments 等
        """
        logger.info(f"批评者开始评价文章，主题: {topic}，字数: {len(article)}")

        prompt = f"""{self.SYSTEM_PROMPT}

## 文章主题
{topic}

## 文章内容
{article}

请对文章进行评价，输出 JSON："""

        try:
            response = self.llm.invoke(prompt)
            result = self._parse_result(response.content)
            logger.info(f"评价完成，评分: {result.get('score', 'N/A')}")
            return result

        except Exception as e:
            logger.error(f"评价失败: {e}")
            return {
                "score": 0,
                "scores": {},
                "comments": f"评价过程出错: {e}",
                "highlights": [],
                "suggestions": ["评价失败，请检查文章格式"],
                "recommendation": "未知",
            }

    def _parse_result(self, text: str) -> dict:
        """解析 LLM 返回的 JSON 结果。"""
        import re
        text = text.strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 尝试提取 ```json ``` 中的内容
        pattern = r"```(?:json)?\s*\n(.*?)\n```"
        matches = re.findall(pattern, text, re.DOTALL)
        if matches:
            try:
                return json.loads(matches[0])
            except json.JSONDecodeError:
                pass

        logger.warning(f"批评者结果解析失败，原始输出: {text[:200]}")
        return {
            "score": 5.0,
            "scores": {},
            "comments": "结果解析失败",
            "highlights": [],
            "suggestions": [],
            "recommendation": "一般",
        }

    def format_review(self, result: dict) -> str:
        """
        将评价结果格式化为可读文本。

        Args:
            result: 评价结果字典

        Returns:
            格式化的评价报告
        """
        lines = [
            "📝 批评者评价报告",
            "=" * 40,
            f"总评分: {result.get('score', 'N/A')} / 10",
            "",
            "各项得分:",
        ]

        scores = result.get("scores", {})
        for key, label in [
            ("depth", "深度与洞察力"),
            ("readability", "可读性与吸引力"),
            ("information_density", "信息密度"),
            ("logic", "逻辑严密性"),
            ("originality", "创新性"),
        ]:
            if key in scores:
                lines.append(f"  - {label}: {scores[key]}/10")

        lines.extend([
            "",
            f"总体评价: {result.get('comments', '无')}",
            "",
            "亮点:",
        ])
        for h in result.get("highlights", []):
            lines.append(f"  ✅ {h}")

        lines.extend([
            "",
            "改进建议:",
        ])
        for s in result.get("suggestions", []):
            lines.append(f"  💡 {s}")

        lines.append("")
        lines.append(f"推荐度: {result.get('recommendation', '未知')}")
        lines.append("=" * 40)

        return "\n".join(lines)
