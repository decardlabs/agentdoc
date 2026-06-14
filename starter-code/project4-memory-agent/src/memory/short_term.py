"""
短期记忆模块

使用 Redis 存储当前会话的近期对话消息，支持：
- 添加消息
- 获取最近 N 条消息
- 清空会话
- TTL 自动过期
"""

import json
import logging
from typing import Optional

from langchain_core.messages import (
    BaseMessage, HumanMessage, AIMessage, SystemMessage,
)

logger = logging.getLogger(__name__)


class ShortTermMemory:
    """
    短期记忆管理器，基于 Redis 实现。

    每个会话的消息以 List 形式存储在 Redis 中，Key 格式：
        short_term:{user_id}:{session_id}

    每条消息序列化为 JSON 存储，格式：
        {"type": "human|ai|system", "content": "..."}

    Attributes:
        redis_url: Redis 连接 URL
        ttl_seconds: 会话过期时间（秒），默认 3600（1 小时）
    """

    def __init__(self, redis_url: str = "redis://localhost:6379", ttl_seconds: int = 3600):
        self.redis_url = redis_url
        self.ttl_seconds = ttl_seconds
        self._redis = None

    def _get_redis(self):
        """懒加载 Redis 连接。"""
        if self._redis is None:
            import redis
            self._redis = redis.from_url(self.redis_url, decode_responses=True)
        return self._redis

    def _serialize_message(self, message: BaseMessage) -> dict:
        """将 LangChain 消息对象序列化为字典。"""
        if isinstance(message, HumanMessage):
            msg_type = "human"
        elif isinstance(message, AIMessage):
            msg_type = "ai"
        elif isinstance(message, SystemMessage):
            msg_type = "system"
        else:
            msg_type = "unknown"
        return {"type": msg_type, "content": message.content}

    def _deserialize_message(self, data: dict) -> BaseMessage:
        """将字典反序列化为 LangChain 消息对象。"""
        msg_type = data.get("type", "unknown")
        content = data.get("content", "")
        if msg_type == "human":
            return HumanMessage(content=content)
        elif msg_type == "ai":
            return AIMessage(content=content)
        elif msg_type == "system":
            return SystemMessage(content=content)
        else:
            return HumanMessage(content=content)

    def _make_key(self, user_id: str, session_id: str) -> str:
        """生成 Redis Key。"""
        return f"short_term:{user_id}:{session_id}"

    def add_message(self, user_id: str, session_id: str, message: BaseMessage) -> None:
        """
        向指定会话添加一条消息。

        Args:
            user_id: 用户 ID
            session_id: 会话 ID
            message: LangChain 消息对象
        """
        r = self._get_redis()
        key = self._make_key(user_id, session_id)
        serialized = json.dumps(self._serialize_message(message), ensure_ascii=False)
        r.rpush(key, serialized)
        r.expire(key, self.ttl_seconds)
        logger.debug(f"短期记忆已添加消息: {key}, 类型={serialized[:50]}...")

    def get_recent(self, user_id: str, session_id: str, limit: int = 10) -> list[BaseMessage]:
        """
        获取指定会话最近的 N 条消息。

        Args:
            user_id: 用户 ID
            session_id: 会话 ID
            limit: 最多返回的消息条数

        Returns:
            消息对象列表（按时间顺序，最早的在前）
        """
        r = self._get_redis()
        key = self._make_key(user_id, session_id)
        # 获取最近 limit 条（-limit 到 -1）
        raw_list = r.lrange(key, -limit, -1)
        messages = [self._deserialize_message(json.loads(item)) for item in raw_list]
        return messages

    def get_all(self, user_id: str, session_id: str) -> list[BaseMessage]:
        """
        获取指定会话的所有消息。

        Args:
            user_id: 用户 ID
            session_id: 会话 ID

        Returns:
            全部消息对象列表
        """
        r = self._get_redis()
        key = self._make_key(user_id, session_id)
        raw_list = r.lrange(key, 0, -1)
        return [self._deserialize_message(json.loads(item)) for item in raw_list]

    def clear_session(self, user_id: str, session_id: str) -> None:
        """
        清空指定会话的所有短期记忆。

        Args:
            user_id: 用户 ID
            session_id: 会话 ID
        """
        r = self._get_redis()
        key = self._make_key(user_id, session_id)
        r.delete(key)
        logger.info(f"已清空短期记忆: {key}")

    def clear_user(self, user_id: str) -> None:
        """
        清空某用户所有会话的短期记忆。

        Args:
            user_id: 用户 ID
        """
        r = self._get_redis()
        pattern = f"short_term:{user_id}:*"
        keys = r.keys(pattern)
        if keys:
            r.delete(*keys)
            logger.info(f"已清空用户 {user_id} 的全部短期记忆，共 {len(keys)} 个会话")

    def session_exists(self, user_id: str, session_id: str) -> bool:
        """
        检查指定会话是否存在于短期记忆中。

        Args:
            user_id: 用户 ID
            session_id: 会话 ID

        Returns:
            是否存在
        """
        r = self._get_redis()
        key = self._make_key(user_id, session_id)
        return r.exists(key) > 0
