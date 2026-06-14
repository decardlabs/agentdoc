"""
用户画像工具

从对话中自动提取并更新用户画像，包括：
- 基本信息（姓名、职业等）
- 兴趣爱好
- 偏好习惯
- 技能水平
- 目标与需求

画像以 JSON 格式存储在 Redis 中，Key 格式：user_profile:{user_id}
"""

import json
import logging
from typing import Optional

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)


class UserProfileTool:
    """
    用户画像管理工具。

    使用 LLM 从对话中推断用户特征，持久化到 Redis。
    每次对话后可调用 update_from_conversation 增量更新画像。

    Attributes:
        llm: 用于信息提取的语言模型
        redis_url: Redis 连接 URL
    """

    # 画像的默认结构
    DEFAULT_PROFILE = {
        "name": None,
        "occupation": None,
        "interests": [],
        "preferences": {},
        "skill_level": None,
        "goals": [],
        "language": "中文",
        "notes": [],
    }

    def __init__(
        self,
        llm: Optional[ChatOpenAI] = None,
        redis_url: str = "redis://localhost:6379",
    ):
        """
        初始化用户画像工具。

        Args:
            llm: 语言模型实例；为 None 时从环境变量初始化
            redis_url: Redis 连接 URL
        """
        import os
        if llm is None:
            self.llm = ChatOpenAI(
                model=os.getenv("MODEL_NAME", "gpt-4o-mini"),
                api_key=os.getenv("OPENAI_API_KEY", ""),
                base_url=os.getenv("OPENAI_BASE_URL", None),
                temperature=0.2,
            )
        else:
            self.llm = llm
        self.redis_url = redis_url
        self._redis = None

    def _get_redis(self):
        """懒加载 Redis 连接。"""
        if self._redis is None:
            import redis
            self._redis = redis.from_url(self.redis_url, decode_responses=True)
        return self._redis

    def get_profile(self, user_id: str) -> dict:
        """
        获取指定用户的画像。

        Args:
            user_id: 用户 ID

        Returns:
            用户画像字典；若用户不存在则返回默认结构
        """
        r = self._get_redis()
        key = f"user_profile:{user_id}"
        data = r.get(key)
        if data:
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                logger.warning(f"用户画像数据损坏，重置: {user_id}")
        return self.DEFAULT_PROFILE.copy()

    def save_profile(self, user_id: str, profile: dict) -> None:
        """
        保存用户画像到 Redis。

        Args:
            user_id: 用户 ID
            profile: 画像字典
        """
        r = self._get_redis()
        key = f"user_profile:{user_id}"
        r.set(key, json.dumps(profile, ensure_ascii=False))
        logger.debug(f"用户画像已保存: {user_id}")

    def update_from_conversation(self, user_id: str, messages: list[BaseMessage]) -> dict:
        """
        从对话中推断并更新用户画像（增量更新）。

        调用 LLM 分析对话，提取用户特征，合并到已有画像中。

        Args:
            user_id: 用户 ID
            messages: 对话消息列表

        Returns:
            更新后的用户画像
        """
        existing_profile = self.get_profile(user_id)

        # 格式化对话供 LLM 分析
        conversation_text = self._format_messages(messages)

        # 构造提示词，让 LLM 提取用户信息
        prompt = f"""分析以下对话，提取关于用户的任何信息。
当前已知用户画像：{json.dumps(existing_profile, ensure_ascii=False)}

对话内容：
{conversation_text}

请以 JSON 格式输出更新后的用户画像，包含以下字段（无法确定的字段保留原值）：
- name: 用户姓名（若提及）
- occupation: 职业
- interests: 兴趣列表
- preferences: 偏好字典（如 {{"编程语言": "Python"}}）
- skill_level: 技能水平描述
- goals: 目标或需求列表
- language: 使用语言
- notes: 其他值得记录的信息列表

只输出 JSON，不要输出其他内容。"""

        try:
            response = self.llm.invoke(prompt)
            content = response.content.strip()

            # 尝试提取 JSON（LLM 可能包裹在 ```json ``` 中）
            content = self._extract_json(content)

            updated = json.loads(content)
            # 合并：保留原有值，用新值覆盖
            merged = self._merge_profile(existing_profile, updated)
            self.save_profile(user_id, merged)
            logger.info(f"用户画像已更新: {user_id}")
            return merged
        except json.JSONDecodeError as e:
            logger.error(f"LLM 返回内容解析失败: {e}, 内容={content[:200]}")
            return existing_profile
        except Exception as e:
            logger.error(f"更新用户画像失败: {e}")
            return existing_profile

    def add_note(self, user_id: str, note: str) -> None:
        """
        手动添加一条备注到用户画像。

        Args:
            user_id: 用户 ID
            note: 备注内容
        """
        profile = self.get_profile(user_id)
        profile.setdefault("notes", []).append(note)
        self.save_profile(user_id, profile)

    def reset_profile(self, user_id: str) -> None:
        """
        重置指定用户的画像为默认值。

        Args:
            user_id: 用户 ID
        """
        r = self._get_redis()
        r.delete(f"user_profile:{user_id}")
        logger.info(f"用户画像已重置: {user_id}")

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
            # 只取前 500 字符，避免超长
            content = msg.content[:500] if msg.content else ""
            lines.append(f"{role}: {content}")
        return "\n".join(lines)

    def _extract_json(self, text: str) -> str:
        """从 LLM 输出中提取 JSON 字符串。"""
        text = text.strip()
        # 去掉 ```json ... ``` 包裹
        if text.startswith("```"):
            lines = text.split("\n")
            # 去掉第一行和最后一行
            text = "\n".join(lines[1:-1]).strip()
        return text

    def _merge_profile(self, old: dict, new: dict) -> dict:
        """
        合并新旧画像，保留旧值中未被新值覆盖的字段。
        列表类型字段进行合并去重。
        """
        merged = old.copy()
        for key, value in new.items():
            if key in merged:
                if isinstance(merged[key], list) and isinstance(value, list):
                    # 列表合并去重
                    merged[key] = list(set(merged[key] + value))
                elif value:  # 非空值覆盖
                    merged[key] = value
            else:
                merged[key] = value
        return merged
