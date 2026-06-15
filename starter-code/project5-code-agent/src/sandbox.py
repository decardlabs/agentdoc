"""
E2B 沙箱封装模块

封装 E2B Sandbox 的创建、文件上传、代码执行和结果下载等功能，
提供简单易用的接口给上层模块调用。

E2B 是一个安全的云端代码执行环境，支持：
- 运行 Python、JavaScript 等多种语言
- 文件系统操作
- 网络访问（可配置）
- 超时和资源限制

文档：https://e2b.dev/docs
"""

import os
import logging
from typing import Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)


class E2BSandboxManager:
    """
    E2B 沙箱管理器，负责生命周期管理和文件操作。

    Attributes:
        api_key: E2B API 密钥
        sandbox: 当前活跃的 Sandbox 实例
        template: 使用的 E2B 模板名（默认 python3）
    """

    def __init__(
        self,
        api_key: str,
        template: str = "python3",
        timeout: int = 300,
    ):
        """
        初始化沙箱管理器。

        Args:
            api_key: E2B API 密钥（在 https://e2b.dev 获取）
            template: E2B 模板名，默认 python3
            timeout: 沙箱最长运行时间（秒），默认 300
        """
        self.api_key = api_key
        self.template = template
        self.timeout = timeout
        self.sandbox = None
        self._ensure_e2b_available()

    def _ensure_e2b_available(self):
        """检查 E2B SDK 是否已安装。"""
        try:
            import e2b
        except ImportError:
            raise ImportError(
                "E2B SDK 未安装，请运行：pip install e2b\n"
                "然后在 https://e2b.dev 注册获取 API Key（免费版每月 100 小时）"
            )

    def create_sandbox(self):
        """创建或重用 E2B 沙箱实例。"""
        if self.sandbox is not None:
            logger.debug("沙箱已存在，重用当前实例")
            return

        from e2b import Sandbox

        logger.info(f"创建 E2B 沙箱，模板={self.template}，超时={self.timeout}s")
        # 兼容 e2b SDK 1.x：使用 Sandbox.create() 工厂方法
        try:
            self.sandbox = Sandbox.create(
                api_key=self.api_key,
                template=self.template,
                timeout=self.timeout,
            )
        except (AttributeError, TypeError):
            # 回退到 0.x 旧版 API
            self.sandbox = Sandbox(
                api_key=self.api_key,
                template=self.template,
                timeout=self.timeout,
            )

        # 确保输出目录存在
        self.sandbox.files.make_dir("/home/user/output")

        logger.info(f"沙箱创建成功，ID={self.sandbox.sandbox_id}")

    def upload_files(self, file_paths: list[str]) -> None:
        """
        上传本地文件到沙箱。

        Args:
            file_paths: 本地文件路径列表
        """
        self.create_sandbox()

        for file_path in file_paths:
            path_obj = Path(file_path)
            if not path_obj.exists():
                logger.warning(f"文件不存在，跳过: {file_path}")
                continue

            # 目标路径：/home/user/data/filename
            dest_path = f"/home/user/data/{path_obj.name}"

            logger.info(f"上传文件: {file_path} → {dest_path}")
            self.sandbox.upload_file(
                local_path=str(path_obj),
                remote_path=dest_path,
            )

    def upload_data(self, data: bytes, remote_path: str) -> None:
        """
        上传二进制数据到沙箱指定路径。

        Args:
            data: 二进制数据
            remote_path: 沙箱中的目标路径
        """
        self.create_sandbox()
        self.sandbox.upload_file(
            data=data,
            remote_path=remote_path,
        )

    def execute_code(self, code: str) -> dict:
        """
        在沙箱中执行 Python 代码。

        Args:
            code: 要执行的 Python 代码字符串

        Returns:
            包含 stdout、stderr、exit_code 的字典
        """
        self.create_sandbox()

        logger.debug(f"执行代码，长度={len(code)}")

        # 将代码写入沙箱临时文件，然后执行
        # 这样可以避免命令行转义问题
        remote_code_path = "/home/user/__temp_code.py"
        self.sandbox.upload_file(
            data=code.encode("utf-8"),
            remote_path=remote_code_path,
        )

        # 执行代码
        execution = self.sandbox.run_command(f"python {remote_code_path}")

        result = {
            "stdout": execution.stdout or "",
            "stderr": execution.stderr or "",
            "exit_code": execution.exit_code,
        }

        logger.debug(f"执行完成，exit_code={result['exit_code']}")
        if result["stderr"]:
            logger.warning(f"stderr: {result['stderr'][:200]}")

        return result

    def download_file(self, remote_path: str) -> bytes:
        """
        从沙箱下载文件。

        Args:
            remote_path: 沙箱中的文件路径

        Returns:
            文件内容的二进制数据
        """
        if self.sandbox is None:
            raise RuntimeError("沙箱未创建，无法下载文件")

        logger.info(f"下载文件: {remote_path}")
        return self.sandbox.download_file(remote_path)

    def list_files(self, remote_dir: str) -> list[str]:
        """
        列出沙箱中指定目录的文件。

        Args:
            remote_dir: 沙箱中的目录路径

        Returns:
            文件名列表
        """
        if self.sandbox is None:
            raise RuntimeError("沙箱未创建")

        entries = self.sandbox.files.list(remote_dir)
        return [entry.name for entry in entries]

    def close(self) -> None:
        """关闭并释放沙箱资源。"""
        if self.sandbox is not None:
            logger.info(f"关闭沙箱，ID={self.sandbox.sandbox_id}")
            self.sandbox.close()
            self.sandbox = None

    def __enter__(self):
        """上下文管理器入口。"""
        self.create_sandbox()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口，自动关闭沙箱。"""
        self.close()
