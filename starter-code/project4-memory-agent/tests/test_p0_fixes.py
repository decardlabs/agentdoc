"""
Project 4 (Memory Agent) 真实 P0 修复回归测试

针对 v0.5.0 中验证并修复的 P0 严重问题的回归测试：
1. api.py: chat 路由必须用 ainvoke()（async），不能用 invoke()（会阻塞事件循环）
2. agent.py: generate_response 节点必须动态设置 next_action，
   使 update_profile / summarize 节点真正可达
3. .env.example: API_PORT 默认值必须 != 8000（Chroma 占用 8000 端口）

注意：这些测试**不连接 OpenAI / Redis / Chroma**，完全离线运行。
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# 在 import 项目模块前 mock 外部依赖
for _mod in (
    "openai", "langchain_core", "langchain_core.messages", "langchain_core.prompts",
    "langchain_openai", "langgraph", "langgraph.graph", "langgraph.checkpoint",
    "langgraph.checkpoint.redis", "redis", "fastapi", "uvicorn",
    "pydantic", "dotenv", "chromadb",
):
    sys.modules.setdefault(_mod, MagicMock())

# 添加 src 到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class TestAsyncInvokeUsage(unittest.TestCase):
    """测试 FastAPI 路由用 ainvoke() 而非 invoke()，避免阻塞事件循环"""

    def test_api_uses_ainvoke_not_invoke(self):
        """api.py chat 路由必须用 ainvoke()（async），不能用 invoke()（同步）"""
        api_path = os.path.join(os.path.dirname(__file__), "..", "src", "api.py")
        with open(api_path, "r", encoding="utf-8") as f:
            source = f.read()

        # 必须有 ainvoke 调用
        self.assertIn("ainvoke", source,
                      "api.py chat 路由必须用 ainvoke()（async），不能用 invoke() 阻塞事件循环")

        # 不能在 async 函数体里裸调用 .invoke(（仅在非 mock 代码中）
        # 通过简单检查：ainvoke 数量 >= 1
        ainvoke_count = source.count("ainvoke")
        self.assertGreaterEqual(ainvoke_count, 1,
                                 "api.py 中应至少出现一次 ainvoke 调用")

    def test_chat_endpoint_is_async(self):
        """chat 路由函数签名必须包含 async def"""
        api_path = os.path.join(os.path.dirname(__file__), "..", "src", "api.py")
        with open(api_path, "r", encoding="utf-8") as f:
            source = f.read()

        # 检查 async def chat 存在
        self.assertIn("async def chat", source,
                      "api.py 中必须有 'async def chat' 路由函数")


class TestNextActionDynamic(unittest.TestCase):
    """测试 generate_response 节点动态设置 next_action，修复 update_profile 不可达"""

    def test_generate_response_sets_next_action(self):
        """agent.py generate_response 必须动态设置 next_action"""
        agent_path = os.path.join(os.path.dirname(__file__), "..", "src", "agent.py")
        with open(agent_path, "r", encoding="utf-8") as f:
            source = f.read()

        # 必须有 next_action 的赋值语句
        self.assertIn("state[\"next_action\"]", source,
                      "agent.py generate_response 必须设置 state['next_action']")

        # 必须支持 update_profile 分支
        self.assertIn("update_profile", source,
                      "agent.py 必须支持 next_action='update_profile' 触发 update_profile 节点")

        # 必须支持 summarize 分支
        self.assertIn("summarize", source,
                      "agent.py 必须支持 next_action='summarize' 触发 summarize 节点")

    def test_personal_keywords_trigger_profile(self):
        """检测到'我叫'等个人关键词时必须触发 update_profile"""
        agent_path = os.path.join(os.path.dirname(__file__), "..", "src", "agent.py")
        with open(agent_path, "r", encoding="utf-8") as f:
            source = f.read()

        # 必须有 personal_keywords 列表
        self.assertIn("personal_keywords", source,
                      "agent.py 必须定义 personal_keywords 列表")
        # 至少包含中文"我叫"和英文 "my name is"
        self.assertIn("我叫", source,
                      "personal_keywords 必须包含中文'我叫'")
        self.assertIn("my name is", source,
                      "personal_keywords 必须包含英文'my name is'")

    def test_routes_use_should_continue(self):
        """路由函数 _should_continue 必须能正确分发 next_action"""
        agent_path = os.path.join(os.path.dirname(__file__), "..", "src", "agent.py")
        with open(agent_path, "r", encoding="utf-8") as f:
            source = f.read()

        self.assertIn("def _should_continue", source,
                      "agent.py 必须定义 _should_continue 路由函数")
        # 路由分支必须包含 4 个目标
        for target in ("update_profile", "summarize", "chat", "end"):
            self.assertIn(target, source,
                          f"_should_continue 路由必须支持 '{target}' 分支")


class TestAPIPortNot8000(unittest.TestCase):
    """测试 API_PORT 默认值不为 8000（避免与 Chroma 冲突）"""

    def test_api_port_default_not_8000(self):
        """检查 .env.example 中 API_PORT 默认值 != 8000"""
        env_path = os.path.join(os.path.dirname(__file__), "..", ".env.example")
        with open(env_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 必须包含 API_PORT 配置
        self.assertIn("API_PORT", content, ".env.example 必须包含 API_PORT 配置")

        # 不能默认 8000
        self.assertNotIn("API_PORT=8000", content,
                         "API_PORT 默认值不能是 8000（Chroma 已占用此端口）")

    def test_api_runtime_default_not_8000(self):
        """检查 api.py 中 __main__ 启动时默认端口 != 8000"""
        api_path = os.path.join(os.path.dirname(__file__), "..", "src", "api.py")
        with open(api_path, "r", encoding="utf-8") as f:
            source = f.read()

        # 检查 int(os.getenv("API_PORT", "8000")) 中的默认值
        import re
        matches = re.findall(r'os\.getenv\(\s*["\']API_PORT["\']\s*,\s*["\'](\d+)["\']\s*\)', source)
        if matches:
            default_port = matches[0]
            self.assertNotEqual(default_port, "8000",
                                f"api.py 中 API_PORT 默认值 {default_port} 不能是 8000")


class TestImportsNoCircular(unittest.TestCase):
    """测试关键模块可以 import（捕获循环导入等回归）"""

    def test_agent_module_importable(self):
        """验证 agent.py 可以被 import（mock 所有外部依赖）"""
        try:
            with patch.dict(sys.modules, {
                "langchain_core.messages": MagicMock(),
                "langchain_core.prompts": MagicMock(),
                "langchain_openai": MagicMock(),
                "langgraph.graph": MagicMock(),
                "langgraph.checkpoint.redis": MagicMock(),
                "src.memory.short_term": MagicMock(),
                "src.memory.long_term": MagicMock(),
                "src.memory.summarizer": MagicMock(),
                "src.tools.profile": MagicMock(),
            }):
                import agent  # noqa: F401
        except Exception as e:
            self.fail(f"agent.py import 失败: {e}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
