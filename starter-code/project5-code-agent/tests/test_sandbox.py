"""
E2B 沙箱测试模块

测试沙箱的创建、代码执行、文件上传下载等功能。
注意：运行测试需要有效的 E2B_API_KEY。

设置环境变量 SKIP_E2B_TESTS=1 可跳过需要 E2B 的测试。
"""

import os
import pytest
import tempfile

from src.sandbox import E2BSandboxManager
from src.executor import CodeExecutor
from src.code_generator import CodeGenerator

# 如果设置了跳过标志，则跳过所有测试
SKIP_E2B = os.getenv("SKIP_E2B_TESTS", "0") == "1"

# 测试用的简单 Python 代码
SIMPLE_CODE = """
import sys
print(f"Python 版本: {sys.version}")
print("Hello from E2B Sandbox!")
print("RESULT: 执行成功")
"""

PLOT_CODE = """
import matplotlib
matplotlib.use('Agg')  # 非交互式后端
import matplotlib.pyplot as plt
import os

os.makedirs("/home/user/output", exist_ok=True)

plt.figure(figsize=(6, 4))
plt.plot([1, 2, 3], [1, 4, 9])
plt.title("测试图表")
plt.savefig("/home/user/output/plot.png")
print("PLOT_SAVED:/home/user/output/plot.png")
print("RESULT: 图表生成成功")
"""


# ============ 沙箱管理器测试 ============

@pytest.mark.skipif(SKIP_E2B, reason="E2B 测试已跳过（设置 SKIP_E2B_TESTS=1）")
class TestE2BSandboxManager:
    """E2B 沙箱管理器测试用例。"""

    @pytest.fixture
    def sandbox_manager(self):
        """创建沙箱管理器，测试后自动关闭。"""
        api_key = os.getenv("E2B_API_KEY", "dummy")
        manager = E2BSandboxManager(api_key=api_key, timeout=60)
        yield manager
        manager.close()

    def test_create_sandbox(self, sandbox_manager):
        """测试创建沙箱。"""
        sandbox_manager.create_sandbox()
        assert sandbox_manager.sandbox is not None
        assert sandbox_manager.sandbox.sandbox_id != ""

    def test_execute_simple_code(self, sandbox_manager):
        """测试执行简单 Python 代码。"""
        result = sandbox_manager.execute_code(SIMPLE_CODE)
        assert result["exit_code"] == 0
        assert "Hello from E2B Sandbox" in result["stdout"]

    def test_execute_code_with_error(self, sandbox_manager):
        """测试执行有错误的代码。"""
        error_code = "print(undefined_variable)"
        result = sandbox_manager.execute_code(error_code)
        assert result["exit_code"] != 0
        assert "NameError" in result["stderr"] or "not defined" in result["stderr"]

    def test_upload_and_execute(self, sandbox_manager):
        """测试上传文件后执行代码。"""
        # 创建临时 CSV 文件
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("name,value\nAlice,100\nBob,200\n")
            temp_path = f.name

        try:
            sandbox_manager.upload_files([temp_path])
            code = """
import pandas as pd
df = pd.read_csv("/home/user/data/" + "__temp__.csv".split("/")[-1].replace(".csv", "") + ".csv")
# 实际文件名需要获取
print("文件上传成功")
print("RESULT: OK")
"""
            # 简化：直接列出 /home/user/data/ 目录
            code2 = """
import os
files = os.listdir("/home/user/data")
print(f"上传的文件: {files}")
print("RESULT: 文件上传成功")
"""
            result = sandbox_manager.execute_code(code2)
            assert result["exit_code"] == 0
        finally:
            os.unlink(temp_path)

    def test_download_file(self, sandbox_manager):
        """测试从沙箱下载文件。"""
        # 先在沙箱中创建一个文件
        setup_code = """
with open("/home/user/output/test.txt", "w") as f:
    f.write("Hello from sandbox!")
"""
        sandbox_manager.execute_code(setup_code)

        # 下载文件
        content = sandbox_manager.download_file("/home/user/output/test.txt")
        assert content.decode("utf-8") == "Hello from sandbox!"


# ============ 代码执行器测试 ============

@pytest.mark.skipif(SKIP_E2B, reason="E2B 测试已跳过")
class TestCodeExecutor:
    """代码执行器测试用例。"""

    @pytest.fixture
    def executor(self):
        return CodeExecutor(timeout=30)

    @pytest.fixture
    def sandbox_manager(self):
        api_key = os.getenv("E2B_API_KEY", "dummy")
        manager = E2BSandboxManager(api_key=api_key, timeout=60)
        yield manager
        manager.close()

    def test_execute_success(self, executor, sandbox_manager):
        """测试成功执行代码。"""
        result = executor.execute(sandbox_manager, SIMPLE_CODE)
        assert result["exit_code"] == 0
        assert "Hello" in result["stdout"]

    def test_execute_failure_raises(self, executor, sandbox_manager):
        """测试执行失败时抛出 RuntimeError。"""
        bad_code = "raise ValueError('测试错误')"
        with pytest.raises(RuntimeError):
            executor.execute(sandbox_manager, bad_code)

    def test_check_syntax_valid(self, executor):
        """测试合法代码的语法检查。"""
        code = "print('hello')"
        is_valid, error = executor.check_syntax(code)
        assert is_valid is True
        assert error is None

    def test_check_syntax_invalid(self, executor):
        """测试非法代码的语法检查。"""
        code = "print('hello'"  # 缺少右括号
        is_valid, error = executor.check_syntax(code)
        assert is_valid is False
        assert error is not None
        assert "语法错误" in error or "SyntaxError" in error

    def test_extract_plot_path(self, executor):
        """测试从 stdout 提取图表路径。"""
        stdout = "训练完成\nPLOT_SAVED:/home/user/output/plot.png\nRESULT: 完成"
        path = executor.extract_plot_path(stdout)
        assert path == "/home/user/output/plot.png"

    def test_extract_plot_path_not_found(self, executor):
        """测试 stdout 中无图表路径时返回 None。"""
        stdout = "训练完成\nRESULT: 完成"
        path = executor.extract_plot_path(stdout)
        assert path is None

    def test_extract_result_summary(self, executor):
        """测试从 stdout 提取结果摘要。"""
        stdout = "epoch 1...\nRESULT: 模型准确率 95%"
        summary = executor.extract_result_summary(stdout)
        assert summary == "模型准确率 95%"


# ============ 代码生成器测试 ============

class TestCodeGenerator:
    """代码生成器测试用例（不需要 E2B，只需要 LLM）。"""

    @pytest.fixture
    def generator(self):
        from langchain_openai import ChatOpenAI
        # 使用 temperature=0 的模型，输出更稳定
        llm = ChatOpenAI(
            model=os.getenv("MODEL_NAME", "gpt-4o-mini"),
            api_key=os.getenv("OPENAI_API_KEY", "dummy"),
            base_url=os.getenv("OPENAI_BASE_URL", None),
            temperature=0,
        )
        return CodeGenerator(llm=llm)

    def test_extract_code_from_markdown(self, generator):
        """测试从 markdown 代码块中提取代码。"""
        text = "这是说明：\n```python\nprint('hello')\n```\n结束"
        code = generator._extract_code(text)
        assert code == "print('hello')"

    def test_extract_code_plain(self, generator):
        """测试从纯文本中提取代码（无 markdown 标记）。"""
        text = "print('hello')\nfor i in range(3):\n    print(i)"
        code = generator._extract_code(text)
        assert "print('hello')" in code

    @pytest.mark.skipif(
        os.getenv("OPENAI_API_KEY", "") == "" or os.getenv("OPENAI_API_KEY", "") == "dummy",
        reason="需要有效的 OPENAI_API_KEY"
    )
    def test_generate_code(self, generator):
        """测试实际调用 LLM 生成代码（需要 API Key）。"""
        code = generator.generate("用 Python 打印 'Hello World'")
        assert "print" in code
        assert "Hello World" in code


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
