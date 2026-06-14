"""
搜索工具（模拟）

模拟互联网搜索功能，返回与查询相关的模拟搜索结果。
在实际部署中，可替换为真实的搜索 API（如 SerpAPI、Bing Search 等）。
"""

import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class SearchTool:
    """
    搜索工具，模拟互联网搜索。

    返回模拟的搜索结果，包含标题、摘要和 URL。
    支持按查询关键词返回不同的模拟结果。

    Attributes:
        mock_database: 模拟的搜索数据库（按主题分类）
    """

    # 模拟搜索数据库（按主题关键词分类）
    MOCK_DATABASE = {
        "AI": [
            {
                "title": "人工智能 - 维基百科",
                "url": "https://zh.wikipedia.org/wiki/人工智能",
                "snippet": "人工智能（AI）是计算机科学的一个分支，旨在创建能够执行通常需要人类智能的任务的系统...",
            },
            {
                "title": "2024 年 AI 大模型发展报告",
                "url": "https://example.com/ai-report-2024",
                "snippet": "2024 年，大语言模型（LLM）在推理能力、多模态理解和 Agent 构建方面取得重大突破...",
            },
            {
                "title": "如何入门 AI 开发？- 知乎",
                "url": "https://zhuanlan.zhihu.com/p/example",
                "snippet": "AI 开发入门需要掌握 Python 编程、机器学习基础、深度学习框架（PyTorch/TensorFlow）...",
            },
        ],
        "Python": [
            {
                "title": "Python 官方文档",
                "url": "https://docs.python.org/zh-cn/3/",
                "snippet": "Python 是一种易于学习、功能强大的编程语言，具有高效的高级数据结构和简单而有效的面向对象编程方法...",
            },
            {
                "title": "Python 数据分析实战 - 教程",
                "url": "https://example.com/python-data-analysis",
                "snippet": "使用 Pandas、NumPy 和 Matplotlib 进行数据分析的完整实战教程，包含代码示例...",
            },
        ],
        "默认": [
            {
                "title": "相关主题综合介绍",
                "url": "https://example.com/general-topic",
                "snippet": "该主题涉及多个方面的知识，包括理论基础、实际应用和未来发展趋势...",
            },
            {
                "title": "深度解析：你需要知道的一切",
                "url": "https://example.com/deep-dive",
                "snippet": "从入门到精通，本文全面解析该主题的核心概念、最佳实践和常见误区...",
            },
            {
                "title": "最新研究报告（2024）",
                "url": "https://example.com/research-2024",
                "snippet": "根据 2024 年最新研究，该领域正在经历快速变革，主要趋势包括...",
            },
        ],
    }

    def __init__(self):
        """初始化搜索工具。"""
        logger.info("搜索工具（模拟）初始化完成")

    def search(self, query: str, num_results: int = 5) -> list[dict]:
        """
        执行搜索，返回相关结果。

        Args:
            query: 搜索查询词
            num_results: 返回的最大结果数

        Returns:
            搜索结果列表，每项包含 title、url、snippet
        """
        logger.info(f"执行搜索，查询: {query}，返回结果数: {num_results}")

        # 根据查询词匹配模拟数据库中的分类
        matched_key = "默认"
        for key in self.MOCK_DATABASE:
            if key.lower() in query.lower():
                matched_key = key
                break

        results = self.MOCK_DATABASE.get(matched_key, self.MOCK_DATABASE["默认"])

        # 若结果不足，用默认结果补充
        if len(results) < num_results:
            results = results + self.MOCK_DATABASE["默认"]

        return results[:num_results]

    def search_with_metadata(self, query: str, num_results: int = 5) -> dict:
        """
        执行搜索并返回带元数据的完整结果。

        Args:
            query: 搜索查询词
            num_results: 返回的最大结果数

        Returns:
            包含 results、query、timestamp 的字典
        """
        import datetime
        results = self.search(query, num_results)
        return {
            "query": query,
            "results": results,
            "timestamp": datetime.datetime.now().isoformat(),
            "total_results": len(results),
        }

    def add_mock_result(self, category: str, title: str, url: str, snippet: str) -> None:
        """
        向模拟数据库中添加自定义搜索结果。

        Args:
            category: 分类关键词
            title: 结果标题
            url: 结果 URL
            snippet: 结果摘要
        """
        if category not in self.MOCK_DATABASE:
            self.MOCK_DATABASE[category] = []
        self.MOCK_DATABASE[category].append({
            "title": title,
            "url": url,
            "snippet": snippet,
        })
        logger.info(f"已添加模拟搜索结果: {category} - {title}")

    def clear_mock_data(self) -> None:
        """清空模拟数据（恢复默认）。"""
        self.MOCK_DATABASE = self.MOCK_DATABASE.copy()
        logger.info("模拟搜索数据已重置为默认")

    def set_real_search(self, api_provider: str, api_key: str) -> None:
        """
        配置真实搜索 API（可选扩展）。

        Args:
            api_provider: API 提供商（"serpapi"、"bing"等）
            api_key: API 密钥
        """
        logger.warning(
            f"真实搜索 API 配置功能尚未实现，当前仍为模拟模式。"
            f"如需使用真实搜索，请直接修改 search() 方法，调用 {api_provider} API。"
        )
