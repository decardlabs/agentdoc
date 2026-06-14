"""
Review Agent - 核心审查逻辑
使用 LLM 分析代码变更，生成审查意见
"""

import os
import logging
from typing import Dict, List, Any, Optional
from pydantic import BaseModel

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)


class ReviewComment(BaseModel):
    """审查意见"""
    file: str
    line: int
    severity: str  # error, warning, suggestion
    category: str  # security, performance, style, logic, best_practice
    comment: str
    suggestion: Optional[str] = None


class ReviewResult(BaseModel):
    """审查结果"""
    pr_number: int
    repo_owner: str
    repo_name: str
    comments: List[ReviewComment]
    summary: str
    stats: Dict[str, int]


class ReviewAgent:
    """代码审查 Agent"""

    def __init__(self):
        self.llm_model = os.getenv("LLM_MODEL", "gpt-4o-mini")
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")

    async def review_pr(
        self,
        repo_owner: str,
        repo_name: str,
        pr_number: int,
        github_token: Optional[str] = None,
        review_level: str = "normal"
    ) -> Dict[str, Any]:
        """
        审查 PR 代码

        Args:
            repo_owner: 仓库所有者
            repo_name: 仓库名称
            pr_number: PR 编号
            github_token: GitHub Token
            review_level: 审查级别 (basic, normal, strict)

        Returns:
            审查结果字典
        """
        logger.info(f"开始审查 PR: {repo_owner}/{repo_name}#{pr_number}")

        from src.github_webhook import GitHubWebhookHandler
        webhook_handler = GitHubWebhookHandler()

        diff_text = await webhook_handler.get_pr_diff(
            owner=repo_owner,
            repo_name=repo_name,
            pr_number=pr_number,
            github_token=github_token
        )

        if not diff_text:
            logger.warning("未获取到 diff 内容")
            return {
                "pr_number": pr_number,
                "comments": [],
                "summary": "无法获取 PR diff 内容，请检查权限。",
                "stats": {}
            }

        files = await webhook_handler.get_pr_files(
            owner=repo_owner,
            repo_name=repo_name,
            pr_number=pr_number,
            github_token=github_token
        )

        file_list = "\n".join([
            f"- {f['filename']} ({f['status']}, +{f['additions']} -{f['deletions']})"
            for f in files[:50]
        ])

        stats = {
            "files_changed": len(files),
            "additions": sum(f.get("additions", 0) for f in files),
            "deletions": sum(f.get("deletions", 0) for f in files)
        }

        review_comments = await self._analyze_diff_with_llm(
            diff_text=diff_text,
            file_list=file_list,
            review_level=review_level
        )

        summary = await self._generate_summary(review_comments, stats)

        result = {
            "pr_number": pr_number,
            "comments": [c.dict() for c in review_comments],
            "summary": summary,
            "stats": stats
        }

        logger.info(f"PR 审查完成: {len(review_comments)} 条意见")
        return result

    async def _analyze_diff_with_llm(
        self,
        diff_text: str,
        file_list: str,
        review_level: str = "normal"
    ) -> List[ReviewComment]:
        """使用 LLM 分析 diff 内容"""
        if not self.openai_api_key:
            logger.warning("未配置 OPENAI_API_KEY，使用模拟审查意见")
            return self._generate_mock_comments(diff_text)

        level_instructions = {
            "basic": "只检查明显的 bug 和安全问题。",
            "normal": "检查 bug、安全问题、代码风格和最佳实践。",
            "strict": "严格检查所有问题，包括性能、可维护性和设计模式。"
        }

        prompt = f"""你是一个高级代码审查工程师。请审查以下 Pull Request 的代码变更。

审查级别：{review_level}
{level_instructions.get(review_level, "")}

## 修改的文件
{file_list}

## Diff 内容
```
{diff_text[:8000]}
```

请按以下格式输出审查意见（JSON 数组）：
```json
[
  {{
    "file": "文件路径",
    "line": 行号,
    "severity": "error|warning|suggestion",
    "category": "security|performance|style|logic|best_practice",
    "comment": "审查意见描述",
    "suggestion": "改进建议（可选）"
  }}
]
```

只输出 JSON，不要有其他内容。最多输出 20 条意见。
"""

        try:
            import openai

            openai.api_key = self.openai_api_key

            response = openai.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {"role": "system", "content": "你是高级代码审查工程师，擅长发现代码中的问题。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2000
            )

            content = response.choices[0].message.content
            import json
            json_start = content.find("[")
            json_end = content.rfind("]") + 1

            if json_start >= 0 and json_end > json_start:
                json_str = content[json_start:json_end]
                comments_data = json.loads(json_str)

                comments = []
                for c in comments_data:
                    comments.append(ReviewComment(
                        file=c.get("file", "unknown"),
                        line=c.get("line", 0),
                        severity=c.get("severity", "suggestion"),
                        category=c.get("category", "best_practice"),
                        comment=c.get("comment", ""),
                        suggestion=c.get("suggestion")
                    ))
                return comments

            logger.warning("LLM 返回格式异常，使用模拟意见")
            return self._generate_mock_comments(diff_text)

        except Exception as e:
            logger.error(f"LLM 分析失败: {str(e)}")
            return self._generate_mock_comments(diff_text)

    async def _generate_summary(self, comments: List[ReviewComment], stats: Dict) -> str:
        """生成审查摘要"""
        error_count = sum(1 for c in comments if c.severity == "error")
        warning_count = sum(1 for c in comments if c.severity == "warning")
        suggestion_count = sum(1 for c in comments if c.severity == "suggestion")

        summary = f"""## 审查摘要

- 修改文件数: {stats.get('files_changed', 0)}
- 新增行数: +{stats.get('additions', 0)}
- 删除行数: -{stats.get('deletions', 0)}

### 审查意见统计
- 🔴 错误: {error_count}
- 🟡 警告: {warning_count}
- 💡 建议: {suggestion_count}

"""

        if error_count > 0:
            summary += "\n⚠️ **发现严重问题，建议修复后再合并。**\n"
        elif warning_count > 0:
            summary += "\n⚠️ **发现一些警告，请酌情修复。**\n"
        else:
            summary += "\n✅ **代码质量良好，可以继续。**\n"

        return summary

    def _generate_mock_comments(self, diff_text: str) -> List[ReviewComment]:
        """生成模拟审查意见（用于测试）"""
        return [
            ReviewComment(
                file="example.py",
                line=10,
                severity="warning",
                category="best_practice",
                comment="建议使用类型注解以提高代码可读性。",
                suggestion="def function(param: str) -> None:"
            ),
            ReviewComment(
                file="example.py",
                line=25,
                severity="suggestion",
                category="style",
                comment="建议使用 f-string 替代 .format()。",
                suggestion="print(f'Hello, {name}')"
            )
        ]
