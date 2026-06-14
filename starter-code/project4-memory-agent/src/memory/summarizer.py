"""
对话摘要模块

定期将对话历史压缩为摘要，存入长期记忆，
以释放短期记忆空间并实现跨会话记忆。
"""

import logging
from typing import Optional

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)


class ConversationSummarizer:
    """
    对话摘要器，使用 LLM 将对话历史压缩为精炼摘要。

    摘要内容包含：
    - 用户提及的关键信息（偏好、需求、背景）
    - 对话中达成的重要结论
    - 待跟进的事项

    Attributes:
        llm: 用于生成摘要的语言模型
    """

    def __init__(self, llm: Optional[ChatOpenAI] = None):
        """
        初始化摘要器。

        Args:
            llm: 语言模型实例；为 None 时自动从环境变量初始化
        """
        if llm is None:
            import os
            self.llm = ChatOpenAI(
                model=os.getenv("MODEL_NAME", "gpt-4o-mini"),
                api_key=os.getenv("OPENAI_API_KEY", ""),
                base_url=os.getenv("OPENAI_BASE_URL", None),
                temperature=0.3,
            )
        else:
            self.llm = llm

    def summarize(self, messages: list[BaseMessage]) -> str:
        """
        将对话消息列表压缩为摘要文本。

        Args:
            messages: 对话消息列表

        Returns:
            摘要文本（中文，200 字以内）
        """
        if not messages:
            return ""

        # 将消息格式化为可读文本
        conversation_text = self._format_messages(messages)

        prompt = f"""请将以下对话历史压缩为一段简洁的摘要（200 字以内）。
摘要应包含：
1. 用户表达的关键偏好、需求或背景信息
2. 对话中达成的重要结论
3. 任何待跟进的事项

对话历史：
{conversation_text}

请直接输出摘要内容，不要加标题或额外说明。"""

        try:
            response = self.llm.invoke(prompt)
            summary = response.content.strip()
            logger.info(f"对话摘要生成成功，长度={len(summary)}")
            return summary
        except Exception as e:
            logger.error(f"生成摘要失败: {e}")
            return f"[摘要生成失败] {conversation_text[:100]}"

    def should_summarize(self, message_count: int, threshold: int = 20) -> bool:
        """
        判断是否需要触发摘要。

        Args:
            message_count: 当前会话消息总数
            threshold: 触发摘要的消息数阈值，默认 20

        Returns:
            是否应该摘要
        """
        return message_count >= threshold

    def extract_key_facts(self, messages: list[BaseMessage]) -> list[str]:
        """
        从对话中提取关键事实（结构化信息），用于更新用户画像。

        Args:
            messages: 对话消息列表

        Returns:
            关键事实列表，每项为一个字符串
        """
        conversation_text = self._format_messages(messages)

        prompt = f"""从以下对话中提取用户表达的关键事实，每条事实单独一行。
只提取客观事实，不要包含推测或评价。
如果没有明确事实，输出"无"。

对话历史：
{conversation_text}

关键事实："""

        try:
            response = self.llm.invoke(prompt)
            facts = [
                line.strip().lstrip("0123456789.-、")
                for line in response.content.strip().split("\n")
                if line.strip() and line.strip() != "无"
            ]
            return facts
        except Exception as e:
            logger.error(f"提取关键事实失败: {e}")
            return []

    def _format_messages(self, messages: list[BaseMessage]) -> str:
        """将消息列表格式化为可读文本。"""
        lines = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                role = "用户"
            elif isinstance(msg, AIMessage):
                role = "助手"
            else:
                role = "系统"
            lines.append(f"{role}: {msg.content}")
        return "\n".join(lines)
