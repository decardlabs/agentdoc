"""
代码执行器模块

协调沙箱管理器执行代码，并解析执行结果。
负责将代码发送到 E2B 沙箱、收集输出、处理超时等。
"""

import logging
from typing import Optional

from src.sandbox import E2BSandboxManager

logger = logging.getLogger(__name__)


class CodeExecutor:
    """
    代码执行器，负责在沙箱中执行 Python 代码并收集结果。

    Attributes:
        timeout: 单次代码执行超时时间（秒）
    """

    def __init__(self, timeout: int = 60):
        """
        初始化执行器。

        Args:
            timeout: 代码执行超时时间（秒），默认 60
        """
        self.timeout = timeout

    def execute(self, sandbox_manager: E2BSandboxManager, code: str) -> dict:
        """
        在指定的沙箱实例中执行代码。

        Args:
            sandbox_manager: E2B 沙箱管理器实例
            code: 要执行的 Python 代码字符串

        Returns:
            执行结果字典，包含：
            - stdout: 标准输出字符串
            - stderr: 标准错误字符串
            - exit_code: 进程退出码（0 表示成功）

        Raises:
            RuntimeError: 当代码执行失败且 stderr 非空时抛出
            TimeoutError: 当执行超时时抛出
        """
        logger.info(f"开始在沙箱中执行代码，代码长度={len(code)}")

        # 在沙箱中执行代码
        result = sandbox_manager.execute_code(code)

        stdout = result.get("stdout", "")
        stderr = result.get("stderr", "")
        exit_code = result.get("exit_code", -1)

        logger.info(f"执行完成，exit_code={exit_code}，stdout长度={len(stdout)}，stderr长度={len(stderr)}")

        # 如果退出码非零且有 stderr 输出，视为执行失败
        if exit_code != 0 and stderr.strip():
            error_msg = f"代码执行失败 (exit_code={exit_code}):\n{stderr}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        return {
            "stdout": stdout,
            "stderr": stderr,
            "exit_code": exit_code,
        }

    def execute_with_timeout(self, sandbox_manager: E2BSandboxManager, code: str) -> dict:
        """
        带超时控制的代码执行。

        Args:
            sandbox_manager: E2B 沙箱管理器实例
            code: 要执行的 Python 代码字符串

        Returns:
            执行结果字典

        Raises:
            TimeoutError: 执行超时时抛出
        """
        import signal

        def handler(signum, frame):
            raise TimeoutError(f"代码执行超时（{self.timeout} 秒）")

        # 设置超时信号（仅在主线程中有效）
        old_handler = signal.signal(signal.SIGALRM, handler)
        signal.alarm(self.timeout)

        try:
            result = self.execute(sandbox_manager, code)
            signal.alarm(0)  # 取消超时
            return result
        except TimeoutError:
            raise
        finally:
            signal.signal(signal.SIGALRM, old_handler)

    def check_syntax(self, code: str) -> tuple[bool, Optional[str]]:
        """
        检查 Python 代码的语法是否正确（不实际执行）。

        Args:
            code: Python 代码字符串

        Returns:
            (is_valid, error_message) 元组
        """
        try:
            compile(code, "<string>", "exec")
            return True, None
        except SyntaxError as e:
            error_msg = f"语法错误 (第 {e.lineno} 行): {e.msg}"
            logger.warning(error_msg)
            return False, error_msg

    def extract_plot_path(self, stdout: str) -> Optional[str]:
        """
        从标准输出中提取图表保存路径。

        Agent 代码约定用 print("PLOT_SAVED:/path/to/plot.png") 标记图表位置。

        Args:
            stdout: 代码的标准输出

        Returns:
            图表路径；若未找到则返回 None
        """
        for line in stdout.split("\n"):
            if line.startswith("PLOT_SAVED:"):
                return line.replace("PLOT_SAVED:", "").strip()
        return None

    def extract_result_summary(self, stdout: str) -> str:
        """
        从标准输出中提取结果摘要。

        Agent 代码约定用 print("RESULT: ...") 输出结果摘要。

        Args:
            stdout: 代码的标准输出

        Returns:
            结果摘要字符串；若未找到则返回 stdout 的最后几行
        """
        for line in stdout.split("\n"):
            if line.startswith("RESULT:"):
                return line.replace("RESULT:", "").strip()

        # 未找到 RESULT 标记，返回最后 3 行非空输出
        non_empty_lines = [l for l in stdout.strip().split("\n") if l.strip()]
        return "\n".join(non_empty_lines[-3:]) if non_empty_lines else ""
