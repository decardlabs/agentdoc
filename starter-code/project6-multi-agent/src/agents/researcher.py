"""
研究员 Agent

负责根据文章主题搜集相关资料和事实，调用搜索工具获取数据，
并将结果整理为结构化的研究材料，供写作者使用。
"""

import json
import logging
from typing import Optional

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from src.tools.search import SearchTool
from src.tools.crawler import CrawlerTool

logger = logging.getLogger(__name__)


class ResearcherAgent:
    """
    研究员 Agent，负责资料搜集和事实核查。

    工作流程：
    1. 分析主题，确定需要搜集的关键信息点
    2. 调用搜索工具获取相关资料
    3. 整理和结构化资料
    4. 返回研究材料（供写作者使用）

    Attributes:
        llm: 语言模型实例
        search_tool: 搜索工具实例
        crawler_tool: 爬虫工具实例（模拟）
        max_sources: 最多搜集的资料来源数
    """

    SYSTEM_PROMPT = """你是一个专业的研究员，擅长快速搜集和整理信息。

你的任务：
1. 根据用户提供的主题，确定需要搜集的关键信息点
2. 模拟搜索过程（描述你会找到哪些类型的信息）
3. 将搜集到的信息整理为结构化的研究材料

输出格式（JSON）：
{
  "key_points": ["要点1", "要点2", ...],
  "facts": [{"claim": "事实描述", "source": "来源"}],
  "statistics": [{"data": "数据描述", "value": "数值"}],
  "references": ["参考链接或文献"],
  "outline": "建议的文章大纲"
}

注意：由于无法真实访问互联网，你需要基于已知知识生成合理的研究材料。
标注 [知识截止日期] 如有需要。"""

    def __init__(
        self,
        llm: Optional[ChatOpenAI] = None,
        max_sources: int = 5,
    ):
        """
        初始化研究员 Agent。

        Args:
            llm: 语言模型实例；为 None 时从环境变量初始化
            max_sources: 最多搜集的资料来源数
        """
        import os
        if llm is None:
            self.llm = ChatOpenAI(
                model=os.getenv("MODEL_NAME", "gpt-4o-mini"),
                api_key=os.getenv("OPENAI_API_KEY", ""),
                base_url=os.getenv("OPENAI_BASE_URL", None),
                temperature=0.3,
            )
        else:
            self.llm = llm

        self.search_tool = SearchTool()
        self.crawler_tool = CrawlerTool()
        self.max_sources = max_sources

        logger.info(f"研究员 Agent 初始化完成，max_sources={max_sources}")

    def research(self, topic: str) -> str:
        """
        对指定主题进行研究，返回结构化的研究材料。

        Args:
            topic: 文章主题

        Returns:
            结构化的研究材料文本（包含要点、事实、数据、大纲等）
        """
        logger.info(f"研究员开始研究主题: {topic}")

        # 第 1 步：调用搜索工具（模拟）获取初步信息
        search_results = self.search_tool.search(topic, num_results=self.max_sources)
        logger.debug(f"搜索到 {len(search_results)} 条结果")

        # 第 2 步：对搜索结果进行"爬取"（模拟）
        crawled_contents = []
        for result in search_results[:3]:  # 只爬取前 3 条
            content = self.crawler_tool.crawl(result["url"])
            crawled_contents.append(content)

        # 第 3 步：调用 LLM 整理研究材料
        research_material = self._synthesize(topic, search_results, crawled_contents)

        logger.info(f"研究完成，材料长度={len(research_material)}")
        return research_material

    def _synthesize(
        self,
        topic: str,
        search_results: list[dict],
        crawled_contents: list[str],
    ) -> str:
        """
        调用 LLM 将搜索结果和爬取内容整理为结构化研究材料。

        Args:
            topic: 文章主题
            search_results: 搜索结果列表
            crawled_contents: 爬取的页面内容列表

        Returns:
            结构化的研究材料文本
        """
        # 构造输入提示
        search_summary = "\n".join([
            f"- {r['title']}: {r['snippet']}"
            for r in search_results
        ])

        prompt = f"""{self.SYSTEM_PROMPT}

## 研究主题
{topic}

## 搜索结果（模拟）
{search_summary}

## 爬取内容摘要（模拟）
{" | ".join([c[:200] for c in crawled_contents])}

请基于以上信息，生成结构化的研究材料（JSON 格式）："""

        try:
            response = self.llm.invoke(prompt)
            material = response.content
            return material
        except Exception as e:
            logger.error(f"研究材料整理失败: {e}")
            # 返回基础结构
            return json.dumps({
                "key_points": [f"关于{topic}的关键要点1", f"关于{topic}的关键要点2"],
                "facts": [],
                "statistics": [],
                "references": [],
                "outline": f"1. 引言\n2. {topic}的背景\n3. 核心内容\n4. 总结",
            }, ensure_ascii=False, indent=2)

    def extract_outline(self, research_material: str) -> str:
        """
        从研究材料中提取文章大纲。

        Args:
            research_material: 研究材料文本（JSON 或纯文本）

        Returns:
            文章大纲字符串
        """
        try:
            data = json.loads(research_material)
            return data.get("outline", "未生成大纲")
        except json.JSONDecodeError:
            # 若不是 JSON，尝试从文本中提取大纲
            lines = research_material.split("\n")
            outline_lines = [
                l.strip() for l in lines
                if l.strip().startswith("outline") or l.strip().startswith("大纲")
            ]
            return outline_lines[0] if outline_lines else "未找到大纲"

    def fact_check(self, text: str) -> dict:
        """
        对文本中的事实陈述进行核查（可选功能）。

        Args:
            text: 待核查的文本

        Returns:
            核查结果字典
        """
        prompt = f"""请对以下文本中的事实陈述进行核查，标注可能不准确的信息。

文本：
{text}

输出 JSON：
{{
  "verified": ["已核实的事实1", ...],
  "questionable": ["存疑的陈述1", ...],
  "suggestions": ["建议修改1", ...]
}}"""

        try:
            response = self.llm.invoke(prompt)
            return json.loads(response.content)
        except Exception:
            return {"verified": [], "questionable": [], "suggestions": []}
