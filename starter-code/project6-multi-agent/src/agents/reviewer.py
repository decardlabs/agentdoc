"""
审校者 Agent

对写作者生成的草稿进行审校，检查内容质量、逻辑连贯性、
事实准确性、语言表达等，决定是否通过，并提供修改意见。
"""

import json
import logging
from typing import Optional

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)


class ReviewerAgent:
    """
    审校者 Agent，负责对文章草稿进行质量审校。

    审校维度：
    1. 内容完整性：是否覆盖主题的核心要点
    2. 逻辑连贯性：段落之间是否有清晰的逻辑关系
    3. 事实准确性：是否包含明显错误的事实陈述
    4. 语言表达：是否有语病、错别字、表达不清的地方
    5. 结构合理性：章节安排是否合理
    6. 字数要求：是否达到最小字数要求

    Attributes:
        llm: 语言模型实例
        min_score: 通过审校的最低分数（1-10），默认 7
        min_length: 最小字数要求，默认 1000
    """

    SYSTEM_PROMPT = """你是一个专业的内容审校者，负责对文章草稿进行审校评估。

审校维度（每项 1-10 分）：
1. 内容完整性：是否覆盖主题的核心要点
2. 逻辑连贯性：段落之间是否有清晰的逻辑关系
3. 事实准确性：是否包含明显错误的事实陈述
4. 语言表达：是否有语病、表达不清的地方
5. 结构合理性：章节安排是否合理
6. 字数要求：是否达到要求（不达标则此项 1 分）

总分 ≥ {min_score} 且各项均 ≥ 5 分视为通过。

输出 JSON 格式：
{
  "approved": true/false,
  "scores": {
    "completeness": 8,
    "logic": 7,
    "accuracy": 9,
    "language": 8,
    "structure": 7,
    "length": 6
  },
  "total_score": 7.5,
  "feedback": "具体的修改建议，逐条列出",
  "strengths": ["优点1", "优点2"],
  "weaknesses": ["需要改进的地方1", "需要改进的地方2"]
}

注意：feedback 应尽可能具体，指出需要修改的段落或表述。"""

    def __init__(
        self,
        llm: Optional[ChatOpenAI] = None,
        min_score: float = 7.0,
        min_length: int = 1000,
    ):
        """
        初始化审校者 Agent。

        Args:
            llm: 语言模型实例；为 None 时从环境变量初始化
            min_score: 通过审校的最低平均分（1-10）
            min_length: 最小字数要求
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

        self.min_score = min_score
        self.min_length = min_length
        logger.info(f"审校者 Agent 初始化完成，min_score={min_score}，min_length={min_length}")

    def review(self, topic: str, draft: str) -> dict:
        """
        审校文章草稿，返回审校结果。

        Args:
            topic: 文章主题
            draft: 文章草稿（Markdown 格式）

        Returns:
            审校结果字典，包含 approved、scores、feedback 等
        """
        import re
        word_count = self._count_words(draft)
        logger.info(f"审校者开始审校，主题: {topic}，字数={word_count}")

        prompt = f"""{self.SYSTEM_PROMPT.format(min_score=self.min_score)}

## 文章主题
{topic}

## 文章草稿
{draft}

## 字数统计
{word_count} 字（要求不少于 {self.min_length} 字）

请进行审校评估，输出 JSON："""

        try:
            response = self.llm.invoke(prompt)
            result = self._parse_result(response.content)

            # 强制检查字数
            if word_count < self.min_length:
                result["scores"]["length"] = 1
                result["total_score"] = (
                    sum(result["scores"].values()) / len(result["scores"])
                    if result.get("scores") else 0
                )
                result["approved"] = False
                result["feedback"] += f"\n- 字数不足：当前 {word_count} 字，要求不少于 {self.min_length} 字"

            logger.info(
                f"审校完成，通过={result['approved']}，总分={result.get('total_score', 'N/A')}"
            )
            return result

        except Exception as e:
            logger.error(f"审校失败: {e}")
            # 返回默认不通过结果
            return {
                "approved": False,
                "scores": {},
                "total_score": 0,
                "feedback": f"审校过程出错: {e}",
                "strengths": [],
                "weaknesses": ["审校失败，请检查草稿格式"],
            }

    def _parse_result(self, text: str) -> dict:
        """解析 LLM 返回的 JSON 结果。"""
        import re
        text = text.strip()

        # 尝试直接解析
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

        # 解析失败，返回默认值
        logger.warning(f"审校结果解析失败，原始输出: {text[:200]}")
        return {
            "approved": False,
            "scores": {},
            "total_score": 0,
            "feedback": "审校结果解析失败，默认不通过",
            "strengths": [],
            "weaknesses": ["审校结果格式异常"],
        }

    def _count_words(self, text: str) -> int:
        """统计中文字数。"""
        import re
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        english_words = len(re.findall(r'[a-zA-Z]+', text))
        return chinese_chars + english_words

    def set_min_score(self, score: float) -> None:
        """设置通过审校的最低分数。"""
        self.min_score = score
        logger.info(f"最低审校分数已设置为: {score}")
