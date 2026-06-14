"""
多 Agent 系统编排器测试模块

测试 LangGraph 工作流的节点执行、条件分支和状态传递。
由于需要调用 LLM，部分测试默认跳过（需设置 RUN_LLM_TESTS=1）。
"""

import os
import pytest
import json

from src.orchestrator import MultiAgentOrchestrator, MultiAgentState
from src.agents.researcher import ResearcherAgent
from src.agents.writer import WriterAgent
from src.agents.reviewer import ReviewerAgent
from src.agents.critic import CriticAgent

# 是否运行需要 LLM 的测试（需要 OPENAI_API_KEY）
RUN_LLM_TESTS = os.getenv("RUN_LLM_TESTS", "0") == "1"
SKIP_REASON = "需要 OPENAI_API_KEY 且 RUN_LLM_TESTS=1"


# ============ 研究员 Agent 测试 ============

class TestResearcherAgent:
    """研究员 Agent 测试用例。"""

    @pytest.fixture
    def researcher(self):
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(
            model=os.getenv("MODEL_NAME", "gpt-4o-mini"),
            api_key=os.getenv("OPENAI_API_KEY", "dummy"),
            temperature=0.3,
        )
        return ResearcherAgent(llm=llm)

    def test_search_tool_integration(self, researcher):
        """测试搜索工具集成（不需要 LLM）。"""
        results = researcher.search_tool.search("AI 发展", num_results=3)
        assert len(results) <= 3
        assert all("title" in r and "url" in r for r in results)

    def test_crawler_tool_integration(self, researcher):
        """测试爬虫工具集成（不需要 LLM）。"""
        content = researcher.crawler_tool.crawl("https://zh.wikipedia.org/wiki/AI")
        assert len(content) > 0
        assert "维基百科" in content or "模拟" in content

    @pytest.mark.skipif(not RUN_LLM_TESTS, reason=SKIP_REASON)
    def test_research(self, researcher):
        """测试完整研究流程（需要 LLM）。"""
        result = researcher.research("AI 大模型")
        assert len(result) > 100
        # 尝试解析 JSON
        try:
            data = json.loads(result)
            assert "key_points" in data or "outline" in data
        except json.JSONDecodeError:
            # 若不是 JSON，至少应有内容
            assert len(result) > 200


# ============ 写作者 Agent 测试 ============

class TestWriterAgent:
    """写作者 Agent 测试用例。"""

    @pytest.fixture
    def writer(self):
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(
            model=os.getenv("MODEL_NAME", "gpt-4o-mini"),
            api_key=os.getenv("OPENAI_API_KEY", "dummy"),
            temperature=0.7,
        )
        return WriterAgent(llm=llm, min_length=500)  # 测试时降低字数要求

    def test_count_words(self, writer):
        """测试字数统计。"""
        text = "这是一段测试文本，包含中文和 English words。"
        count = writer._count_words(text)
        assert count > 10  # 中文字符 + 英文单词

    def test_extract_outline_from_json(self, writer):
        """测试从 JSON 研究材料中提取大纲。"""
        material = json.dumps({
            "outline": "1. 引言\n2. 主体\n3. 结论"
        })
        outline = writer._extract_outline(material)
        assert "引言" in outline

    def test_extract_outline_from_text(self, writer):
        """测试从纯文本中提取大纲。"""
        material = "一些研究内容...\n大纲：\n1. 引言\n2. 主体"
        outline = writer._extract_outline(material)
        assert "大纲" in outline or "引言" in outline

    @pytest.mark.skipif(not RUN_LLM_TESTS, reason=SKIP_REASON)
    def test_write_first_draft(self, writer):
        """测试撰写初稿（需要 LLM）。"""
        material = json.dumps({
            "key_points": ["要点1", "要点2"],
            "outline": "1. 引言\n2. 主体\n3. 结论"
        })
        article = writer.write("测试主题", material)
        assert len(article) > 100
        assert "# " in article or "## " in article  # Markdown 标题


# ============ 审校者 Agent 测试 ============

class TestReviewerAgent:
    """审校者 Agent 测试用例。"""

    @pytest.fixture
    def reviewer(self):
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(
            model=os.getenv("MODEL_NAME", "gpt-4o-mini"),
            api_key=os.getenv("OPENAI_API_KEY", "dummy"),
            temperature=0.3,
        )
        return ReviewerAgent(llm=llm, min_score=6.0)

    def test_review_short_article(self, reviewer):
        """测试审校字数不足的文章（不需要 LLM，直接检查字数）。"""
        short_article = "这是一篇很短的文章。"
        result = reviewer.review("测试主题", short_article)
        # 字数不足应不通过
        assert result["approved"] is False
        assert "字数" in result["feedback"] or "length" in result.get("scores", {})

    def test_parse_result_valid_json(self, reviewer):
        """测试解析合法的 JSON 结果。"""
        text = '{"approved": true, "scores": {"completeness": 8}, "total_score": 8.0, "feedback": "很好", "strengths": [], "weaknesses": []}'
        result = reviewer._parse_result(text)
        assert result["approved"] is True
        assert result["total_score"] == 8.0

    def test_parse_result_invalid_json(self, reviewer):
        """测试解析不合法的 JSON 结果（应返回默认值）。"""
        text = "这不是 JSON 格式的结果，无法解析。"
        result = reviewer._parse_result(text)
        assert result["approved"] is False
        assert result["total_score"] == 0

    @pytest.mark.skipif(not RUN_LLM_TESTS, reason=SKIP_REASON)
    def test_review_real_article(self, reviewer):
        """测试审校真实文章（需要 LLM）。"""
        article = """# 人工智能发展现状

## 引言
人工智能（AI）是当今世界最重要的技术之一。

## 主体
近年来，大语言模型取得了重大突破...

## 结论
AI 技术将继续快速发展。"""
        result = reviewer.review("人工智能", article)
        assert "approved" in result
        assert "feedback" in result


# ============ 编排器测试 ============

class TestMultiAgentOrchestrator:
    """多 Agent 编排器测试用例。"""

    @pytest.fixture
    def orchestrator(self):
        return MultiAgentOrchestrator(
            max_revisions=1,
            enable_critic=False,  # 测试时禁用批评者
            enable_human_review=False,
        )

    def test_initialization(self, orchestrator):
        """测试编排器初始化。"""
        assert orchestrator.max_revisions == 1
        assert orchestrator.enable_critic is False
        assert orchestrator.graph is not None

    def test_route_after_review_approved(self, orchestrator):
        """测试审校通过后的路由。"""
        state = {
            "review_result": {"approved": True},
            "revision_count": 0,
        }
        route = orchestrator._route_after_review(state)
        assert route == "publish"

    def test_route_after_review_rejected_within_limit(self, orchestrator):
        """测试审校不通过且在修订次数限制内时的路由。"""
        state = {
            "review_result": {"approved": False},
            "revision_count": 0,
        }
        route = orchestrator._route_after_review(state)
        assert route == "revise"

    def test_route_after_review_rejected_exceeds_limit(self, orchestrator):
        """测试审校不通过且超过修订次数限制时的路由。"""
        state = {
            "review_result": {"approved": False},
            "revision_count": 1,  # 已达到 max_revisions
        }
        route = orchestrator._route_after_review(state)
        assert route == "publish"  # 强制发布

    @pytest.mark.skipif(not RUN_LLM_TESTS, reason=SKIP_REASON)
    def test_run_full_workflow(self, orchestrator):
        """测试完整工作流（需要 LLM，且耗时较长）。"""
        result = orchestrator.run("Python 编程基础", user_id="test_user")
        assert "final_article" in result
        assert len(result["final_article"]) > 100
        assert "research_result" in result
        assert "draft" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
