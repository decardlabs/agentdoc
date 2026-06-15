"""
Project 5 (Code Agent) 真实 P0 修复回归测试

针对 v0.5.0 中验证并修复的 P0 严重问题：
1. sandbox.py: typing 导入必须是 `List`（大写），不是 `list`（小写在 Python 3.9 之前错误）
2. sandbox.py: 兼容 E2B SDK 1.x（Sandbox.create()），同时保留 0.x 回退
3. requirements.txt: 锁定 e2b>=1.0.0,<2.0.0

注意：这些测试**不连接 E2B API**，完全离线运行。
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# 在 import 项目模块前 mock 外部依赖
for _mod in (
    "openai", "langchain", "langchain_openai", "e2b", "matplotlib",
    "seaborn", "pandas", "PIL", "fastapi", "uvicorn", "dotenv", "loguru",
):
    sys.modules.setdefault(_mod, MagicMock())

# 添加 src 到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class TestTypingImportFixed(unittest.TestCase):
    """测试 typing 导入修复：使用 List 而非 list"""

    def test_uses_typing_list_capital(self):
        """sandbox.py 必须用 List（来自 typing），不能直接用 list（小写在 type hint 中需要 3.9+）"""
        sandbox_path = os.path.join(os.path.dirname(__file__), "..", "src", "sandbox.py")
        with open(sandbox_path, "r", encoding="utf-8") as f:
            source = f.read()

        # 必须从 typing 导入 List
        self.assertIn("from typing import", source,
                      "sandbox.py 必须从 typing 导入类型")
        self.assertIn("List", source,
                      "sandbox.py 必须导入 List（用于类型注解）")

        # 不能有"from typing import list"（小写 list，错误）
        self.assertNotIn("from typing import list", source,
                         "sandbox.py 中不能有 'from typing import list'（大小写错误）")


class TestE2BSDKCompatibility(unittest.TestCase):
    """测试 E2B SDK 1.x 兼容性"""

    def test_sandbox_create_factory_used(self):
        """create_sandbox 必须优先用 Sandbox.create()（SDK 1.x 工厂方法）"""
        sandbox_path = os.path.join(os.path.dirname(__file__), "..", "src", "sandbox.py")
        with open(sandbox_path, "r", encoding="utf-8") as f:
            source = f.read()

        # 必须有 Sandbox.create 调用
        self.assertIn("Sandbox.create(", source,
                      "sandbox.py 必须用 Sandbox.create() 兼容 E2B SDK 1.x")

    def test_sandbox_legacy_fallback_exists(self):
        """必须保留 Sandbox() 0.x 旧版 API 回退"""
        sandbox_path = os.path.join(os.path.dirname(__file__), "..", "src", "sandbox.py")
        with open(sandbox_path, "r", encoding="utf-8") as f:
            source = f.read()

        # 0.x 回退：通过 except (AttributeError, TypeError) 捕获
        self.assertIn("AttributeError", source,
                      "sandbox.py 必须有 AttributeError 异常捕获（用于回退到 0.x API）")
        self.assertIn("TypeError", source,
                      "sandbox.py 必须有 TypeError 异常捕获（用于回退到 0.x API）")

    def test_create_sandbox_function_exists(self):
        """必须有 create_sandbox() 方法"""
        sandbox_path = os.path.join(os.path.dirname(__file__), "..", "src", "sandbox.py")
        with open(sandbox_path, "r", encoding="utf-8") as f:
            source = f.read()

        self.assertIn("def create_sandbox", source,
                      "sandbox.py 必须定义 create_sandbox() 方法")


class TestE2BVersionPin(unittest.TestCase):
    """测试 e2b 版本锁定"""

    def test_e2b_version_pinned(self):
        """requirements.txt 必须锁定 e2b>=1.0.0,<2.0.0"""
        req_path = os.path.join(os.path.dirname(__file__), "..", "requirements.txt")
        with open(req_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 必须有 e2b>=1.0.0（防止退回 0.x）
        import re
        match = re.search(r"^e2b\s*([><=!~,\.\d\s]+)$", content, re.MULTILINE)
        self.assertIsNotNone(match, "requirements.txt 必须包含 e2b 版本约束")

        version_spec = match.group(1).strip()
        # 至少包含 >=1.0.0
        self.assertIn(">=1.0.0", version_spec.replace(" ", "").replace(",", ""),
                      f"e2b 必须 >= 1.0.0（当前约束: {version_spec}）")
        # 必须有上限 <2.0.0
        self.assertIn("<2.0.0", version_spec.replace(" ", "").replace(",", ""),
                      f"e2b 必须 < 2.0.0（当前约束: {version_spec}）")


class TestSandboxManagerInit(unittest.TestCase):
    """测试 E2BSandboxManager 初始化行为（mock 掉 e2b 真实依赖）"""

    def test_init_checks_e2b_available(self):
        """E2BSandboxManager.__init__ 必须检查 e2b 是否可用"""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

        # mock e2b 模块让 _ensure_e2b_available 通过
        with patch.dict(sys.modules, {"e2b": MagicMock()}):
            from src.sandbox import E2BSandboxManager
            mgr = E2BSandboxManager(api_key="fake-key-for-test", template="python3", timeout=300)
            # 关键属性都应被设置
            self.assertEqual(mgr.api_key, "fake-key-for-test")
            self.assertEqual(mgr.template, "python3")
            self.assertEqual(mgr.timeout, 300)
            self.assertIsNone(mgr.sandbox)  # 尚未创建

    def test_init_raises_without_e2b(self):
        """未安装 e2b 时初始化应抛 ImportError"""
        # 让 e2b import 失败
        with patch.dict(sys.modules, {"e2b": None}):
            # 强制 ImportError
            import importlib
            with patch("importlib.import_module", side_effect=ImportError("no e2b")):
                # 重新 import sandbox 模块
                if "src.sandbox" in sys.modules:
                    del sys.modules["src.sandbox"]
                from src.sandbox import E2BSandboxManager
                with self.assertRaises(ImportError):
                    E2BSandboxManager(api_key="fake-key")


if __name__ == "__main__":
    unittest.main(verbosity=2)
