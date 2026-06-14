"""
Git 工具集
提供 Git 操作相关的工具函数
"""

import os
import logging
import subprocess
from typing import Dict, List, Any, Optional
from pathlib import Path

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)


def clone_repository(repo_url: str, target_dir: str, token: Optional[str] = None) -> bool:
    """
    克隆仓库到本地

    Args:
        repo_url: 仓库 URL
        target_dir: 目标目录
        token: GitHub Token (用于认证)

    Returns:
        是否成功
    """
    try:
        if token:
            auth_url = repo_url.replace("https://", f"https://{token}@")
        else:
            auth_url = repo_url

        cmd = ["git", "clone", "--depth", "1", auth_url, target_dir]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300
        )

        if result.returncode == 0:
            logger.info(f"仓库克隆成功: {target_dir}")
            return True
        else:
            logger.error(f"仓库克隆失败: {result.stderr}")
            return False

    except Exception as e:
        logger.error(f"克隆仓库异常: {str(e)}")
        return False


def get_file_content(repo_dir: str, file_path: str, ref: str = "HEAD") -> Optional[str]:
    """
    获取指定文件的内容

    Args:
        repo_dir: 仓库目录
        file_path: 文件路径
        ref: Git 引用

    Returns:
        文件内容
    """
    try:
        cmd = ["git", "-C", repo_dir, "show", f"{ref}:{file_path}"]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            return result.stdout
        else:
            logger.warning(f"获取文件内容失败: {file_path}, {result.stderr}")
            return None

    except Exception as e:
        logger.error(f"获取文件内容异常: {str(e)}")
        return None


def get_diff_between_refs(repo_dir: str, base_ref: str, head_ref: str) -> Optional[str]:
    """
    获取两个引用之间的 diff

    Args:
        repo_dir: 仓库目录
        base_ref: 基础引用
        head_ref: 头部引用

    Returns:
        diff 文本
    """
    try:
        cmd = ["git", "-C", repo_dir, "diff", f"{base_ref}...{head_ref}"]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode == 0:
            return result.stdout
        else:
            logger.error(f"获取 diff 失败: {result.stderr}")
            return None

    except Exception as e:
        logger.error(f"获取 diff 异常: {str(e)}")
        return None


def get_changed_files(repo_dir: str, base_ref: str, head_ref: str) -> List[Dict[str, Any]]:
    """
    获取两个引用之间修改的文件列表

    Args:
        repo_dir: 仓库目录
        base_ref: 基础引用
        head_ref: 头部引用

    Returns:
        修改文件信息列表
    """
    try:
        cmd = [
            "git", "-C", repo_dir,
            "diff", "--name-status",
            f"{base_ref}...{head_ref}"
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            logger.error(f"获取修改文件列表失败: {result.stderr}")
            return []

        files = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split("\t", 1)
            if len(parts) == 2:
                status = parts[0]
                filepath = parts[1]

                status_map = {
                    "A": "added",
                    "M": "modified",
                    "D": "deleted",
                    "R": "renamed"
                }

                files.append({
                    "path": filepath,
                    "status": status_map.get(status, "unknown")
                })

        return files

    except Exception as e:
        logger.error(f"获取修改文件列表异常: {str(e)}")
        return []


def apply_patch(repo_dir: str, patch_content: str) -> bool:
    """
    应用补丁

    Args:
        repo_dir: 仓库目录
        patch_content: 补丁内容

    Returns:
        是否成功
    """
    try:
        patch_file = os.path.join(repo_dir, ".tmp_patch.diff")

        with open(patch_file, "w") as f:
            f.write(patch_content)

        cmd = ["git", "-C", repo_dir, "apply", "--check", patch_file]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            logger.warning(f"补丁检查失败: {result.stderr}")
            os.remove(patch_file)
            return False

        cmd = ["git", "-C", repo_dir, "apply", patch_file]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        os.remove(patch_file)

        if result.returncode == 0:
            logger.info("补丁应用成功")
            return True
        else:
            logger.error(f"补丁应用失败: {result.stderr}")
            return False

    except Exception as e:
        logger.error(f"应用补丁异常: {str(e)}")
        if os.path.exists(patch_file):
            os.remove(patch_file)
        return False


def get_blame_info(repo_dir: str, file_path: str, line_number: int) -> Optional[Dict[str, str]]:
    """
    获取指定行的最近提交信息

    Args:
        repo_dir: 仓库目录
        file_path: 文件路径
        line_number: 行号

    Returns:
        提交信息
    """
    try:
        cmd = [
            "git", "-C", repo_dir,
            "blame", "-L",
            f"{line_number},{line_number}",
            "--porcelain",
            file_path
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            return None

        info = {}
        for line in result.stdout.split("\n"):
            if line.startswith("author "):
                info["author"] = line[7:]
            elif line.startswith("author-time "):
                info["time"] = line[12:]
            elif line.startswith("summary "):
                info["summary"] = line[8:]

        return info if info else None

    except Exception as e:
        logger.error(f"获取 blame 信息异常: {str(e)}")
        return None


class GitToolkit:
    """Git 工具集类"""

    def __init__(self, repo_dir: str):
        self.repo_dir = repo_dir

    def get_file(self, file_path: str, ref: str = "HEAD") -> Optional[str]:
        """获取文件内容"""
        return get_file_content(self.repo_dir, file_path, ref)

    def get_diff(self, base: str, head: str) -> Optional[str]:
        """获取 diff"""
        return get_diff_between_refs(self.repo_dir, base, head)

    def get_changed_files(self, base: str, head: str) -> List[Dict[str, Any]]:
        """获取修改文件列表"""
        return get_changed_files(self.repo_dir, base, head)

    def blame(self, file_path: str, line_number: int) -> Optional[Dict[str, str]]:
        """获取 blame 信息"""
        return get_blame_info(self.repo_dir, file_path, line_number)
