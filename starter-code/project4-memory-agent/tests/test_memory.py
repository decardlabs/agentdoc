"""
记忆模块单元测试

测试短期记忆（Redis）和长期记忆（Chroma）的增删改查功能。
运行前请确保 Redis 和 Chroma 服务已启动。
"""

import os
import pytest
import uuid

from src.memory.short_term import ShortTermMemory
from src.memory.long_term import LongTermMemory
from src.tools.profile import UserProfileTool
from langchain_core.messages import HumanMessage, AIMessage


# ============ 测试配置 ============

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8000"))

# 测试用用户 ID（随机生成避免冲突）
TEST_USER_ID = f"test_user_{uuid.uuid4().hex[:8]}"
TEST_SESSION_ID = f"test_session_{uuid.uuid4().hex[:8]}"


# ============ 短期记忆测试 ============

class TestShortTermMemory:
    """短期记忆（Redis）测试用例。"""

    @pytest.fixture
    def memory(self):
        """创建短期记忆实例，测试后自动清理。"""
        mem = ShortTermMemory(redis_url=REDIS_URL, ttl_seconds=60)
        yield mem
        # 清理测试数据
        mem.clear_user(TEST_USER_ID)

    def test_add_and_get_message(self, memory):
        """测试添加消息和获取最近消息。"""
        # 添加一条用户消息
        memory.add_message(TEST_USER_ID, TEST_SESSION_ID, HumanMessage(content="你好"))
        # 添加一条 AI 回复
        memory.add_message(TEST_USER_ID, TEST_SESSION_ID, AIMessage(content="你好！有什么可以帮你？"))

        # 获取最近 10 条
        recent = memory.get_recent(TEST_USER_ID, TEST_SESSION_ID, limit=10)
        assert len(recent) == 2
        assert isinstance(recent[0], HumanMessage)
        assert recent[0].content == "你好"
        assert isinstance(recent[1], AIMessage)
        assert "你好" in recent[1].content

    def test_get_all_messages(self, memory):
        """测试获取全部消息。"""
        for i in range(5):
            memory.add_message(TEST_USER_ID, TEST_SESSION_ID, HumanMessage(content=f"消息 {i}"))

        all_msgs = memory.get_all(TEST_USER_ID, TEST_SESSION_ID)
        assert len(all_msgs) == 5

    def test_clear_session(self, memory):
        """测试清空指定会话。"""
        memory.add_message(TEST_USER_ID, TEST_SESSION_ID, HumanMessage(content="test"))
        memory.clear_session(TEST_USER_ID, TEST_SESSION_ID)
        recent = memory.get_recent(TEST_USER_ID, TEST_SESSION_ID, limit=10)
        assert len(recent) == 0

    def test_session_exists(self, memory):
        """测试会话存在性检查。"""
        assert memory.session_exists(TEST_USER_ID, TEST_SESSION_ID) is False
        memory.add_message(TEST_USER_ID, TEST_SESSION_ID, HumanMessage(content="hi"))
        assert memory.session_exists(TEST_USER_ID, TEST_SESSION_ID) is True

    def test_multiple_sessions_isolated(self, memory):
        """测试不同会话之间的数据隔离。"""
        session_a = "session_A"
        session_b = "session_B"
        memory.add_message(TEST_USER_ID, session_a, HumanMessage(content="A的消息"))
        memory.add_message(TEST_USER_ID, session_b, HumanMessage(content="B的消息"))

        recent_a = memory.get_recent(TEST_USER_ID, session_a, limit=10)
        recent_b = memory.get_recent(TEST_USER_ID, session_b, limit=10)

        assert len(recent_a) == 1
        assert recent_a[0].content == "A的消息"
        assert len(recent_b) == 1
        assert recent_b[0].content == "B的消息"


# ============ 长期记忆测试 ============

class TestLongTermMemory:
    """长期记忆（Chroma 向量库）测试用例。"""

    @pytest.fixture
    def memory(self):
        """创建长期记忆实例，测试后自动清理。"""
        mem = LongTermMemory(
            host=CHROMA_HOST,
            port=CHROMA_PORT,
            collection_name=f"test_collection_{uuid.uuid4().hex[:8]}",
        )
        yield mem
        # Chroma 不支持按集合名删除，重启服务即可清理测试集合

    def test_store_and_retrieve(self, memory):
        """测试存储和语义检索。"""
        # 存储一条关于 Python 的记忆
        memory.store(
            user_id=TEST_USER_ID,
            session_id=TEST_SESSION_ID,
            content="用户喜欢使用 Python 进行数据分析，常用 pandas 和 matplotlib",
            metadata={"type": "preference"},
        )

        # 用相关查询检索
        results = memory.retrieve(
            user_id=TEST_USER_ID,
            query="Python 数据分析",
            top_k=3,
        )

        assert len(results) >= 1
        assert "Python" in results[0]["content"] or "pandas" in results[0]["content"]

    def test_retrieve_with_filter(self, memory):
        """测试检索时的用户过滤（不同用户的数据应隔离）。"""
        other_user = f"other_{uuid.uuid4().hex[:8]}"

        memory.store(TEST_USER_ID, TEST_SESSION_ID, "这是测试用户的记忆")
        memory.store(other_user, TEST_SESSION_ID, "这是其他用户的记忆")

        # 用 TEST_USER_ID 检索，不应返回其他用户的数据
        results = memory.retrieve(TEST_USER_ID, query="记忆", top_k=10)
        for r in results:
            assert r["metadata"]["user_id"] == TEST_USER_ID

    def test_delete_user_memory(self, memory):
        """测试删除用户的所有长期记忆。"""
        memory.store(TEST_USER_ID, TEST_SESSION_ID, "待删除的记忆")
        memory.delete_user_memory(TEST_USER_ID)

        results = memory.retrieve(TEST_USER_ID, query="记忆", top_k=10)
        assert len(results) == 0


# ============ 用户画像测试 ============

class TestUserProfile:
    """用户画像工具测试用例。"""

    @pytest.fixture
    def profile_tool(self):
        """创建用户画像工具实例。"""
        # 使用 temperature=0 确保输出稳定，便于测试
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(
            model=os.getenv("MODEL_NAME", "gpt-4o-mini"),
            api_key=os.getenv("OPENAI_API_KEY", "dummy"),
            base_url=os.getenv("OPENAI_BASE_URL", None),
            temperature=0,
        )
        tool = UserProfileTool(llm=llm, redis_url=REDIS_URL)
        yield tool
        tool.reset_profile(TEST_USER_ID)

    def test_get_default_profile(self, profile_tool):
        """测试获取默认画像（用户不存在时）。"""
        profile = profile_tool.get_profile("nonexistent_user")
        assert "name" in profile
        assert "interests" in profile
        assert profile["interests"] == []

    def test_save_and_get_profile(self, profile_tool):
        """测试保存和读取画像。"""
        test_profile = {
            "name": "Alice",
            "occupation": "工程师",
            "interests": ["AI", "编程"],
            "preferences": {"编程语言": "Python"},
        }
        profile_tool.save_profile(TEST_USER_ID, test_profile)
        retrieved = profile_tool.get_profile(TEST_USER_ID)
        assert retrieved["name"] == "Alice"
        assert retrieved["interests"] == ["AI", "编程"]

    def test_add_note(self, profile_tool):
        """测试添加备注。"""
        profile_tool.add_note(TEST_USER_ID, "用户喜欢详细解释")
        profile = profile_tool.get_profile(TEST_USER_ID)
        assert "用户喜欢详细解释" in profile["notes"]

    def test_reset_profile(self, profile_tool):
        """测试重置画像。"""
        profile_tool.save_profile(TEST_USER_ID, {"name": "Bob"})
        profile_tool.reset_profile(TEST_USER_ID)
        profile = profile_tool.get_profile(TEST_USER_ID)
        assert profile["name"] is None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
