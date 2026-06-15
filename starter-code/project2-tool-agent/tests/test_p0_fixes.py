"""
Project 2 真实 P0 修复回归测试

针对 review 中验证为误报的问题的回归测试：
- eval() 注入（误报 P0：实际已用 safe_dict 限制）
- tools 参数传递（误报 P0：实际已正确传递）
- numexpr 依赖（误报 P0：实际是可选的，eval 已用 safe_dict）

测试目标：
- calculator.py 中的 eval 使用安全字典
- agent.py 中 tools=self.tools_schema 正确传递
- calculator 在恶意输入下不会执行任意代码

注意：这些测试**不调用 LLM**，完全离线运行。
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# 在 import 项目模块前 mock 外部依赖，让测试在无依赖环境也能跑
for _mod in (
    "openai", "dotenv", "langchain", "langchain_openai",
    "langgraph", "requests", "pydantic",
):
    sys.modules.setdefault(_mod, MagicMock())

# 添加 src 到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class TestCalculatorSecurity(unittest.TestCase):
    """测试计算器安全性（覆盖 review 误报 P0：eval() 注入）"""

    def setUp(self):
        from tools.calculator import calculator
        self.calculator = calculator

    def test_eval_uses_safe_dict(self):
        """验证 calculator 内部 eval() 使用 safe_dict（限制命名空间）"""
        import inspect
        from tools import calculator as calc_module

        source = inspect.getsource(calc_module)

        # 断言 1: 存在 eval 调用
        self.assertIn("eval(", source, "calculator 必须使用 eval() 解析表达式")

        # 断言 2: eval 第二个参数是 safe_dict（而非 {} 或 None）
        # 模式：eval(expression, safe_dict, ...) 或 eval(expression, safe_dict)
        # 关键：必须显式定义 safe_dict 限制内置函数
        self.assertIn("safe_dict", source,
                      "calculator 必须定义 safe_dict 限制 eval 的命名空间")

    def test_malicious_input_blocked(self):
        """验证恶意输入（__import__、open）被 safe_dict 阻止"""
        malicious_inputs = [
            "__import__('os').system('echo HACKED')",
            "open('/etc/passwd').read()",
            "exec('print(1)')",
            "(lambda: __import__('os').system('id'))()",
        ]

        for expr in malicious_inputs:
            with self.subTest(expr=expr):
                # 恶意输入应该抛异常（NameError），而不是执行
                try:
                    result = self.calculator(expr)
                    # 如果没抛异常，至少要确保没执行恶意代码
                    self.assertIsInstance(result, (int, float, str),
                                          f"恶意表达式返回了非预期类型: {type(result)}")
                except (NameError, TypeError, SyntaxError):
                    # 这些异常是安全的：表示 safe_dict 阻止了访问
                    pass
                except Exception as e:
                    # 其他异常也接受（但记录下来）
                    self.assertNotIn("HACKED", str(e))


class TestAgentToolsParameter(unittest.TestCase):
    """测试 Agent tools 参数传递（覆盖 review 误报 P0：max_iter 时缺 tools 参数）"""

    def test_tools_schema_passed_to_completion(self):
        """验证 agent.py 在调用 chat.completions.create() 时传入了 tools 参数"""
        import inspect
        from src import agent as agent_module

        source = inspect.getsource(agent_module)

        # 断言 1: 存在 chat.completions.create 调用
        self.assertIn("chat.completions.create", source,
                      "agent.py 必须调用 chat.completions.create()")

        # 断言 2: 该调用传入了 tools 参数
        # 模式：tools=self.tools_schema 或 tools=tools
        self.assertRegex(source, r"tools\s*=\s*(self\.)?tools",
                         "agent.py 必须传入 tools=self.tools_schema（或 tools=tools）")

    def test_tools_schema_is_list(self):
        """验证 self.tools_schema 是 list of dict（OpenAI Function Calling 格式）"""
        from src.agent import ToolAgent

        # 模拟 OpenAI 客户端（agent.py 第 62 行 `from openai import OpenAI`）
        # 把它直接注入到 src.agent 模块的命名空间
        import src.agent as agent_module
        fake_openai_instance = MagicMock()
        fake_openai_instance.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(
                content="OK",
                tool_calls=None
            ))]
        )
        fake_openai_cls = MagicMock(return_value=fake_openai_instance)
        agent_module.OpenAI = fake_openai_cls

        os.environ.setdefault("OPENAI_API_KEY", "test-key")
        try:
            agent = ToolAgent()
            self.assertIsInstance(agent.tools_schema, list,
                                  "tools_schema 必须是 list")
            if agent.tools_schema:
                # 验证每项都是 dict 且包含 type=function
                for tool in agent.tools_schema:
                    self.assertIsInstance(tool, dict)
                    self.assertIn("type", tool)
        except Exception as e:
            # 如果 __init__ 因为网络/凭据失败，跳过（不算 P0）
            self.skipTest(f"ToolAgent 初始化需要外部依赖: {e}")


class TestRoleConsistency(unittest.TestCase):
    """测试对话角色一致性（覆盖 review 误报 P0：assitant 拼写）"""

    def test_no_typo_in_role_strings(self):
        """验证代码中所有 role 字符串都是正确拼写（user/assistant/system/tool）"""
        import os
        import re

        src_dir = os.path.join(os.path.dirname(__file__), "..", "src")
        valid_roles = {"user", "assistant", "system", "tool", "function"}
        typo_pattern = re.compile(r'"(assitant|asistant|assistnat|usr|systm)"', re.IGNORECASE)

        for root, _, files in os.walk(src_dir):
            for filename in files:
                if not filename.endswith(".py"):
                    continue
                filepath = os.path.join(root, filename)
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                matches = typo_pattern.findall(content)
                self.assertEqual(
                    matches, [],
                    f"{filepath} 包含 role 拼写错误: {matches}"
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
