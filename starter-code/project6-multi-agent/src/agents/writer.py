"""
写作者 Agent

根据研究员提供的资料撰写文章草稿，支持根据审校反馈进行修订。
生成的文章要求 1000+ 字，结构清晰，语言流畅。
"""

import json
import logging
from typing import Optional

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)


class WriterAgent:
    """
    写作者 Agent，负责根据研究材料撰写文章。

    支持两种模式：
    1. 初稿模式：根据研究材料撰写完整文章
    2. 修订模式：根据审校反馈修订已有草稿

    Attributes:
        llm: 语言模型实例
        min_length: 文章最小字数，默认 1000
        style: 文章风格（"科普"、"学术"、"新闻"等）
    """

    SYSTEM_PROMPT = """你是一个专业的内容写作者，擅长将复杂信息整理为结构清晰、易读性强的文章。

写作要求：
1. 文章长度不少于 1000 字
2. 结构清晰：包含引言、主体（多个小节）、结论
3. 语言流畅自然，避免生硬的 AI 味
4. 合理使用小标题、列表、强调等排版
5. 基于提供的研究材料写作，不编造虚假数据
6. 若材料不足，明确标注"待补充"

输出格式：Markdown
- 使用 # 表示文章标题
- 使用 ## 表示章节标题
- 使用 ### 表示小节标题
- 使用 - 或 1. 表示列表
- 关键概念用 **加粗** 强调"""

    def __init__(
        self,
        llm: Optional[ChatOpenAI] = None,
        min_length: int = 1000,
        style: str = "科普",
    ):
        """
        初始化写作者 Agent。

        Args:
            llm: 语言模型实例；为 None 时从环境变量初始化
            min_length: 文章最小字数
            style: 文章风格
        """
        import os
        if llm is None:
            self.llm = ChatOpenAI(
                model=os.getenv("MODEL_NAME", "gpt-4o-mini"),
                api_key=os.getenv("OPENAI_API_KEY", ""),
                base_url=os.getenv("OPENAI_BASE_URL", None),
                temperature=0.7,
            )
        else:
            self.llm = llm

        self.min_length = min_length
        self.style = style
        logger.info(f"写作者 Agent 初始化完成，min_length={min_length}，style={style}")

    def write(
        self,
        topic: str,
        research_material: str,
        revision_feedback: str = "",
        is_revision: bool = False,
    ) -> str:
        """
        撰写或修订文章。

        Args:
            topic: 文章主题
            research_material: 研究员提供的资料
            revision_feedback: 审校反馈（修订模式时使用）
            is_revision: 是否为修订模式

        Returns:
            文章草稿（Markdown 格式）
        """
        if is_revision:
            logger.info(f"写作者开始修订文章，主题: {topic}")
            return self._revise(topic, research_material, revision_feedback)
        else:
            logger.info(f"写作者开始撰写文章，主题: {topic}")
            return self._write_first_draft(topic, research_material)

    def _write_first_draft(self, topic: str, research_material: str) -> str:
        """撰写初稿。"""
        # 尝试解析研究材料中的大纲
        outline = self._extract_outline(research_material)

        prompt = f"""{self.SYSTEM_PROMPT}

## 文章主题
{topic}

## 文章风格
{self.style}

## 研究材料
{research_material}

## 建议大纲
{outline}

请撰写一篇不少于 {self.min_length} 字的文章，输出 Markdown 格式："""

        try:
            response = self.llm.invoke(prompt)
            article = response.content

            # 检查字数，若不足则要求扩充
            if self._count_words(article) < self.min_length:
                logger.info("文章字数不足，进行扩充...")
                article = self._expand_article(article, topic)

            logger.info(f"初稿完成，字数={self._count_words(article)}")
            return article

        except Exception as e:
            logger.error(f"撰写文章失败: {e}")
            raise

    def _revise(self, topic: str, draft: str, feedback: str) -> str:
        """
        根据审校反馈修订文章。

        Args:
            topic: 文章主题
            draft: 当前草稿
            feedback: 审校反馈意见

        Returns:
            修订后的文章
        """
        prompt = f"""{self.SYSTEM_PROMPT}

## 文章主题
{topic}

## 当前草稿
{draft}

## 审校反馈意见
{feedback}

请根据审校意见修订文章，保持文章结构清晰、字数不少于 {self.min_length} 字。
输出修订后的完整文章（Markdown 格式）："""

        try:
            response = self.llm.invoke(prompt)
            revised = response.content
            logger.info(f"修订完成，字数={self._count_words(revised)}")
            return revised
        except Exception as e:
            logger.error(f"修订文章失败: {e}")
            return draft  # 修订失败时返回原稿

    def _expand_article(self, article: str, topic: str) -> str:
        """扩充文章字数。"""
        prompt = f"""以下文章字数不足 {self.min_length} 字，请在保持质量和结构的前提下进行合理扩充。

原文：
{article}

请输出扩充后的完整文章："""

        try:
            response = self.llm.invoke(prompt)
            return response.content
        except Exception:
            return article

    def _extract_outline(self, research_material: str) -> str:
        """从研究材料中提取大纲。"""
        try:
            data = json.loads(research_material)
            return data.get("outline", "请自行规划文章结构")
        except json.JSONDecodeError:
            return "请自行规划文章结构"

    def _count_words(self, text: str) -> int:
        """统计中文字数（汉字 + 英文单词）。"""
        import re
        # 统计汉字
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        # 统计英文单词
        english_words = len(re.findall(r'[a-zA-Z]+', text))
        return chinese_chars + english_words

    def set_style(self, style: str) -> None:
        """设置文章风格。"""
        self.style = style
        logger.info(f"文章风格已设置为: {style}")
