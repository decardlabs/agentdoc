"""
GitHub Webhook 处理器
处理 GitHub PR 事件，调用 Review Agent 进行代码审查
"""

import os
import logging
import aiohttp
from typing import Dict, Any, List, Optional

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)


class GitHubWebhookHandler:
    """处理 GitHub Webhook 事件"""

    def __init__(self):
        self.github_token = os.getenv("GITHUB_TOKEN", "")
        self.github_api_base = "https://api.github.com"

    async def process_pr_event(self, payload: Dict[str, Any]):
        """处理 PR Webhook 事件"""
        try:
            pr = payload.get("pull_request", {})
            repo = payload.get("repository", {})

            pr_number = pr.get("number")
            repo_full_name = repo.get("full_name")
            owner, repo_name = repo_full_name.split("/")

            logger.info(f"处理 PR 事件: {repo_full_name}#{pr_number}")

            from src.agent.review_agent import ReviewAgent
            agent = ReviewAgent()

            review_result = await agent.review_pr(
                repo_owner=owner,
                repo_name=repo_name,
                pr_number=pr_number,
                github_token=self.github_token
            )

            await self.post_review_comments(
                owner=owner,
                repo_name=repo_name,
                pr_number=pr_number,
                review_result=review_result
            )

            logger.info(f"PR {repo_full_name}#{pr_number} 审查完成")

        except Exception as e:
            logger.error(f"处理 PR 事件失败: {str(e)}")

    async def post_review_comments(
        self,
        owner: str,
        repo_name: str,
        pr_number: int,
        review_result: Dict[str, Any]
    ):
        """将审查意见发布到 GitHub PR"""
        if not self.github_token:
            logger.warning("未配置 GITHUB_TOKEN，无法发布审查意见")
            return

        headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json"
        }

        comments = review_result.get("comments", [])
        summary = review_result.get("summary", "")

        review_body = f"## 🤖 Code Review Agent 审查意见\n\n{summary}\n\n"

        if comments:
            review_body += "### 详细意见\n\n"
            for comment in comments[:20]:
                file_path = comment.get("file", "unknown")
                line = comment.get("line", 0)
                content = comment.get("comment", "")
                severity = comment.get("severity", "suggestion")

                emoji = "🔴" if severity == "error" else "🟡" if severity == "warning" else "💡"
                review_body += f"{emoji} **{file_path}:{line}**\n{content}\n\n"

        review_data = {
            "body": review_body,
            "event": "COMMENT"
        }

        url = f"{self.github_api_base}/repos/{owner}/{repo_name}/pulls/{pr_number}/reviews"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=review_data) as response:
                    if response.status == 200:
                        logger.info(f"审查意见已发布到 PR #{pr_number}")
                    else:
                        resp_text = await response.text()
                        logger.error(f"发布审查意见失败: {response.status} - {resp_text}")

        except Exception as e:
            logger.error(f"发布审查意见异常: {str(e)}")

    async def get_pr_diff(
        self,
        owner: str,
        repo_name: str,
        pr_number: int,
        github_token: Optional[str] = None
    ) -> str:
        """获取 PR 的 diff 内容"""
        token = github_token or self.github_token
        if not token:
            logger.error("未提供 GitHub Token")
            return ""

        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3.diff"
        }

        url = f"{self.github_api_base}/repos/{owner}/{repo_name}/pulls/{pr_number}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        diff_text = await response.text()
                        logger.info(f"成功获取 PR #{pr_number} 的 diff，长度: {len(diff_text)}")
                        return diff_text
                    else:
                        resp_text = await response.text()
                        logger.error(f"获取 PR diff 失败: {response.status} - {resp_text}")
                        return ""

        except Exception as e:
            logger.error(f"获取 PR diff 异常: {str(e)}")
            return ""

    async def get_pr_files(
        self,
        owner: str,
        repo_name: str,
        pr_number: int,
        github_token: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取 PR 修改的文件列表"""
        token = github_token or self.github_token
        if not token:
            return []

        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }

        url = f"{self.github_api_base}/repos/{owner}/{repo_name}/pulls/{pr_number}/files"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        files = await response.json()
                        logger.info(f"成功获取 PR #{pr_number} 的文件列表，共 {len(files)} 个文件")
                        return files
                    else:
                        resp_text = await response.text()
                        logger.error(f"获取 PR 文件列表失败: {response.status} - {resp_text}")
                        return []

        except Exception as e:
            logger.error(f"获取 PR 文件列表异常: {str(e)}")
            return []
