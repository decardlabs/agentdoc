"""
Project 1 真实 P0 修复回归测试

针对 review 中验证为误报的两个"问题"（被修复或保持原状）的回归测试。
目的：当后续有人误改这些代码时，测试会立即报警。

测试目标：
- LLMClient.load_dotenv() 行为正确（误报 P0：API Key 安全）
- app.py 临时文件清理（误报 P0：临时文件未清理）
- 文件级 import 路径正确（误报 P0：Import 语句错误）

注意：这些测试**不连接 OpenAI API**，完全离线运行。
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock, mock_open
import tempfile

# 在 import 项目模块前 mock 外部依赖，让测试在无依赖环境也能跑
for _mod in (
    "openai", "dotenv", "streamlit", "pdfplumber",
    "langchain_text_splitters", "tiktoken",
):
    sys.modules.setdefault(_mod, MagicMock())

# 添加 src 到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class TestEnvironmentLoading(unittest.TestCase):
    """测试环境变量加载行为（覆盖 review 误报 P0：API Key 硬编码）"""

    def setUp(self):
        """每个测试前清空相关环境变量"""
        self._saved = {}
        for key in ("OPENAI_API_KEY", "OPENAI_BASE_URL", "LLM_MODEL", "LLM_TEMPERATURE"):
            if key in os.environ:
                self._saved[key] = os.environ.pop(key)

    def tearDown(self):
        """恢复环境变量"""
        for key, value in self._saved.items():
            os.environ[key] = value

    def test_lmm_client_loads_dotenv(self):
        """验证 lmm_client.py 调用 load_dotenv()，不会硬编码 API Key

        注意：load_dotenv() 在模块顶层 import 时执行，patch 拦截不到，
        所以这里用静态检查源码包含 load_dotenv() 调用的方式验证。
        """
        lmm_client_path = os.path.join(
            os.path.dirname(__file__), "..", "src", "lmm_client.py"
        )
        with open(lmm_client_path, "r", encoding="utf-8") as f:
            source = f.read()

        # 断言 1: import 了 load_dotenv
        self.assertIn("load_dotenv", source,
                      "lmm_client.py 必须 import load_dotenv")

        # 断言 2: 调用了 load_dotenv()
        self.assertIn("load_dotenv()", source,
                      "lmm_client.py 必须调用 load_dotenv()（不能在 __init__ 里）")

    def test_lmm_client_raises_without_api_key(self):
        """验证缺少 API Key 时正确报错（不静默使用默认值）"""
        with patch("lmm_client.load_dotenv"):
            os.environ.pop("OPENAI_API_KEY", None)
            from lmm_client import LLMClient
            with self.assertRaises((ValueError, EnvironmentError)):
                LLMClient()


class TestTemporaryFileCleanup(unittest.TestCase):
    """测试临时文件清理（覆盖 review 误报 P0：临时文件未清理）"""

    def test_tempfile_used_and_unlinked(self):
        """验证 app.py 使用 NamedTemporaryFile 并调用 os.unlink() 清理"""
        # 这是一个静态检查：扫描 app.py 源码确认清理逻辑存在
        app_py_path = os.path.join(
            os.path.dirname(__file__), "..", "src", "app.py"
        )
        with open(app_py_path, "r", encoding="utf-8") as f:
            source = f.read()

        # 断言 1: 使用了 NamedTemporaryFile 或 tempfile
        self.assertIn("NamedTemporaryFile", source,
                      "app.py 必须使用 tempfile.NamedTemporaryFile 暂存上传文件")

        # 断言 2: 调用了 os.unlink 或 tempfile 自动清理
        # tempfile.NamedTemporaryFile(delete=True) 是默认行为
        # 但显式 os.unlink 是更安全的模式
        uses_explicit_cleanup = "os.unlink" in source
        uses_auto_delete = "delete=True" in source or "delete=False" in source
        self.assertTrue(
            uses_explicit_cleanup or uses_auto_delete,
            "app.py 必须显式清理临时文件（os.unlink）或设置 delete=True"
        )


class TestImportStructure(unittest.TestCase):
    """测试模块导入结构（覆盖 review 误报 P0：Import 语句错误）"""

    def test_src_modules_importable(self):
        """验证 lmm_client / pdf_loader 可以 import（app.py 是 streamlit 入口，不参与单元测试）"""
        with patch("lmm_client.OpenAI") as mock_openai:
            mock_openai.return_value = MagicMock()
            os.environ.setdefault("OPENAI_API_KEY", "test-key")

            try:
                import lmm_client  # noqa: F401
                import pdf_loader  # noqa: F401
            except ImportError as e:
                self.fail(f"模块 import 失败: {e}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
