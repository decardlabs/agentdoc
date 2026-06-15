"""
Project 6 (Multi-Agent) 真实 P0 修复回归测试

针对 v0.5.0 中验证并修复的 P0 严重问题：
1. orchestrator.py: enable_critic=False 时，路由不能引用 "critic" 边
2. orchestrator.py: TypedDict / Annotated 改从 typing_extensions 导入
   （LangGraph 0.2.x 把 langgraph.graph.END 等依赖从 typing 移到 typing_extensions）
3. orchestrator.py: 移除未使用的 SqliteSaver 死代码
4. requirements.txt: langgraph>=0.2.0, typing-extensions>=4.0.0

注意：这些测试**不调用真实 LLM**，完全离线运行。
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# 在 import 项目模块前 mock 外部依赖
for _mod in (
    "openai", "langchain", "langchain_core", "langchain_core.messages",
    "langchain_openai", "langgraph", "langgraph.graph", "fastapi",
    "uvicorn", "dotenv", "loguru", "pytest", "pytest_asyncio",
):
    sys.modules.setdefault(_mod, MagicMock())

# 添加 src 到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class TestCriticConditionalFix(unittest.TestCase):
    """测试 enable_critic=False 时 critic 路由不崩溃"""

    def test_no_critic_routes_to_publish_not_critic(self):
        """enable_critic=False 时，reviewer 后的路由必须直接到 publish，不能有 critic 边"""
        orch_path = os.path.join(os.path.dirname(__file__), "..", "src", "orchestrator.py")
        with open(orch_path, "r", encoding="utf-8") as f:
            source = f.read()

        # 必须有 if self.enable_critic / else 分支处理 critic 边
        # 检查 _route_after_review 在 critic 禁用时返回 "publish"
        self.assertIn("self.enable_critic", source,
                      "orchestrator.py 中 _route_after_review 必须检查 self.enable_critic")

        # 不能有 _route_after_review 永远返回 "critic" 而没看 enable_critic
        # 简单方法：搜 'return "critic" if self.enable_critic'
        self.assertIn('return \"critic\" if self.enable_critic',
                      source,
                      "_route_after_review 必须根据 enable_critic 决定返回 critic 或 publish")

    def test_conditional_edges_handles_both_branches(self):
        """add_conditional_edges 必须有 enable_critic 条件分支"""
        orch_path = os.path.join(os.path.dirname(__file__), "..", "src", "orchestrator.py")
        with open(orch_path, "r", encoding="utf-8") as f:
            source = f.read()

        # 至少有 2 个 add_conditional_edges 调用（reviewer 后, critic 后, human_review 后）
        cond_edge_count = source.count("add_conditional_edges")
        self.assertGreaterEqual(cond_edge_count, 2,
                                 f"应有 >=2 个 add_conditional_edges，实际 {cond_edge_count}")


class TestTypingExtensionsImport(unittest.TestCase):
    """测试 TypedDict / Annotated 改从 typing_extensions 导入"""

    def test_typed_dict_from_typing_extensions(self):
        """TypedDict 必须从 typing_extensions 导入（不是 typing）"""
        orch_path = os.path.join(os.path.dirname(__file__), "..", "src", "orchestrator.py")
        with open(orch_path, "r", encoding="utf-8") as f:
            source = f.read()

        # 必须有 from typing_extensions import
        self.assertIn("from typing_extensions import", source,
                      "orchestrator.py 必须从 typing_extensions 导入 TypedDict/Annotated")

        # 不能从 typing 直接导入 TypedDict（旧版 langgraph 不兼容）
        # 排除 "from typing import Sequence, Literal, Optional"（这些 OK）
        import re
        bad_imports = re.findall(r"from typing import.*TypedDict.*", source)
        self.assertEqual(bad_imports, [],
                         f"不能从 typing 直接导入 TypedDict: {bad_imports}")

    def test_annotated_from_typing_extensions(self):
        """Annotated 也应从 typing_extensions 导入（与 TypedDict 配对）"""
        orch_path = os.path.join(os.path.dirname(__file__), "..", "src", "orchestrator.py")
        with open(orch_path, "r", encoding="utf-8") as f:
            source = f.read()

        # Annotated 出现在 typing_extensions 导入行
        if "Annotated" in source:
            # 必须从 typing_extensions 导入
            self.assertIn("from typing_extensions import", source,
                          "Annotated 必须从 typing_extensions 导入")
            # 不能从 typing import Annotated
            bad = re.findall(r"from typing import.*Annotated.*", source) if 're' in dir() else []
            import re as _re
            bad = _re.findall(r"from typing import.*Annotated.*", source)
            self.assertEqual(bad, [],
                             f"不能从 typing 直接导入 Annotated: {bad}")


class TestDeadCodeRemoved(unittest.TestCase):
    """测试 SqliteSaver 死代码已删除"""

    def test_no_sqlite_saver_in_orchestrator(self):
        """orchestrator.py 中不应有 SqliteSaver 引用（死代码）"""
        orch_path = os.path.join(os.path.dirname(__file__), "..", "src", "orchestrator.py")
        with open(orch_path, "r", encoding="utf-8") as f:
            source = f.read()

        self.assertNotIn("SqliteSaver", source,
                         "orchestrator.py 中不应有 SqliteSaver（死代码）")
        self.assertNotIn("sqlite_saver", source,
                         "orchestrator.py 中不应有 sqlite_saver 引用")


class TestLangGraphVersionPin(unittest.TestCase):
    """测试 langgraph 版本锁定 >=0.2.0"""

    def test_langgraph_pinned_to_2x(self):
        """requirements.txt 必须 langgraph>=0.2.0"""
        req_path = os.path.join(os.path.dirname(__file__), "..", "requirements.txt")
        with open(req_path, "r", encoding="utf-8") as f:
            content = f.read()

        import re
        match = re.search(r"^langgraph\s*([><=!~,\.\d\s]+)$", content, re.MULTILINE)
        self.assertIsNotNone(match, "requirements.txt 必须包含 langgraph 版本约束")

        version_spec = match.group(1).strip()
        # 至少 >=0.2.0
        self.assertIn(">=0.2.0", version_spec.replace(" ", "").replace(",", ""),
                      f"langgraph 必须 >= 0.2.0（当前约束: {version_spec}）")

    def test_typing_extensions_pinned(self):
        """requirements.txt 必须包含 typing-extensions>=4.0.0"""
        req_path = os.path.join(os.path.dirname(__file__), "..", "requirements.txt")
        with open(req_path, "r", encoding="utf-8") as f:
            content = f.read()

        import re
        match = re.search(r"^typing-extensions\s*([><=!~,\.\d\s]+)$",
                          content, re.MULTILINE)
        self.assertIsNotNone(match,
                             "requirements.txt 必须包含 typing-extensions 依赖")

        version_spec = match.group(1).strip()
        self.assertIn(">=4.0.0", version_spec.replace(" ", "").replace(",", ""),
                      f"typing-extensions 必须 >= 4.0.0（当前约束: {version_spec}）")


class TestCriticAgentOptional(unittest.TestCase):
    """测试 CriticAgent 在 enable_critic=False 时为 None"""

    def test_critic_set_to_none_when_disabled(self):
        """orchestrator.py 中 critic 应在 enable_critic=False 时为 None"""
        orch_path = os.path.join(os.path.dirname(__file__), "..", "src", "orchestrator.py")
        with open(orch_path, "r", encoding="utf-8") as f:
            source = f.read()

        # 查 self.critic = CriticAgent(llm=self.llm) if enable_critic else None
        self.assertIn("if enable_critic", source,
                      "orchestrator.py 中 critic 必须条件初始化")
        # 必须有 None 分支
        self.assertIn("else None", source,
                      "orchestrator.py 中 critic 关闭时必须设为 None")


if __name__ == "__main__":
    unittest.main(verbosity=2)
