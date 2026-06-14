"""
多 Agent 系统编排器

使用 LangGraph 编排 4 个专业 Agent（研究员、写作者、审校者、批评者），
实现顺序执行 + 条件分支（审校不通过时打回给写作者）。

支持人工审核节点（HIL: Human-in-the-Loop）。
"""

import os
import json
import logging
from typing import TypedDict, Annotated, Sequence, Literal, Optional
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver

from src.agents.researcher import ResearcherAgent
from src.agents.writer import WriterAgent
from src.agents.reviewer import ReviewerAgent
from src.agents.critic import CriticAgent

logger = logging.getLogger(__name__)


# ============ 状态定义 ============

class MultiAgentState(TypedDict):
    """
    多 Agent 系统的共享状态。

    Attributes:
        messages: 对话消息列表
        topic: 文章主题
        user_id: 用户 ID
        research_result: 研究员收集的资料
        draft: 写作者生成的草稿
        review_result: 审校者的审校意见
        critic_result: 批评者的评价
        final_article: 最终文章（审校通过后生成）
        revision_count: 已修订次数
        max_revisions: 最大修订次数
        human_approved: 人工审核是否通过
        next_action: 下一步动作（条件分支用）
    """
    messages: Annotated[Sequence[BaseMessage], "对话消息"]
    topic: str
    user_id: str
    research_result: str
    draft: str
    review_result: dict  # {"approved": bool, "feedback": str}
    critic_result: dict  # {"score": int, "comments": str}
    final_article: str
    revision_count: int
    max_revisions: int
    human_approved: Optional[bool]
    next_action: Literal[
        "research", "write", "review", "critic", "revise", "human_review", "publish", "end"
    ]


# ============ 编排器主类 ============

class MultiAgentOrchestrator:
    """
    多 Agent 系统编排器。

    负责协调 4 个专业 Agent 的工作流程，支持条件分支和人工审核。

    工作流程：
    1. Researcher（研究员）：搜集资料和事实
    2. Writer（写作者）：根据资料撰写文章草稿
    3. Reviewer（审校者）：审校草稿，决定是否通过
       - 不通过 → 打回 Writer 修订（最多 max_revisions 次）
       - 通过 → 进入下一步
    4. Critic（批评者）：对文章进行评价打分
    5. Human Review（可选）：人工审核节点
    6. Publish：输出最终文章
    """

    def __init__(
        self,
        llm: Optional[ChatOpenAI] = None,
        max_revisions: int = 2,
        enable_critic: bool = True,
        enable_human_review: bool = False,
    ):
        """
        初始化编排器。

        Args:
            llm: 共享的语言模型实例；为 None 时从环境变量初始化
            max_revisions: 最大修订次数（审校不通过时打回给写作者）
            enable_critic: 是否启用批评者 Agent
            enable_human_review: 是否启用人工审核节点
        """
        import os
        if llm is None:
            llm = ChatOpenAI(
                model=os.getenv("MODEL_NAME", "gpt-4o-mini"),
                api_key=os.getenv("OPENAI_API_KEY", ""),
                base_url=os.getenv("OPENAI_BASE_URL", None),
                temperature=0.7,
            )

        self.llm = llm
        self.max_revisions = max_revisions
        self.enable_critic = enable_critic
        self.enable_human_review = enable_human_review

        # 初始化各 Agent
        self.researcher = ResearcherAgent(llm=self.llm)
        self.writer = WriterAgent(llm=self.llm)
        self.reviewer = ReviewerAgent(llm=self.llm)
        self.critic = CriticAgent(llm=self.llm) if enable_critic else None

        # 构建工作流图
        self.graph = self._build_graph()

        logger.info(
            f"多 Agent 编排器初始化完成，"
            f"max_revisions={max_revisions}，"
            f"critic={'启用' if enable_critic else '禁用'}，"
            f"human_review={'启用' if enable_human_review else '禁用'}"
        )

    def _build_graph(self) -> StateGraph:
        """构建 LangGraph 工作流图。"""

        graph = StateGraph(MultiAgentState)

        # ---------- 添加节点 ----------
        graph.add_node("researcher", self._researcher_node)
        graph.add_node("writer", self._writer_node)
        graph.add_node("reviewer", self._reviewer_node)
        graph.add_node("revise", self._revise_node)

        if self.enable_critic:
            graph.add_node("critic", self._critic_node)

        if self.enable_human_review:
            graph.add_node("human_review", self._human_review_node)

        graph.add_node("publish", self._publish_node)

        # ---------- 设置入口 ----------
        graph.set_entry_point("researcher")

        # ---------- 添加边 ----------
        # 研究员 → 写作者
        graph.add_edge("researcher", "writer")

        # 写作者 → 审校者
        graph.add_edge("writer", "reviewer")

        # 审校者 → 条件分支
        if self.enable_critic:
            graph.add_conditional_edges(
                "reviewer",
                self._route_after_review,
                {
                    "revise": "revise",
                    "critic": "critic",
                }
            )
        else:
            graph.add_conditional_edges(
                "reviewer",
                self._route_after_review,
                {
                    "revise": "revise",
                    "publish": "publish",
                }
            )

        # 修订 → 审校者（打回重新审校）
        graph.add_edge("revise", "reviewer")

        # 批评者 → 条件分支
        if self.enable_human_review:
            graph.add_conditional_edges(
                "critic",
                self._route_after_critic,
                {
                    "human_review": "human_review",
                    "publish": "publish",
                }
            )
        else:
            graph.add_edge("critic", "publish")

        # 人工审核 → 条件分支
        if self.enable_human_review:
            graph.add_conditional_edges(
                "human_review",
                self._route_after_human_review,
                {
                    "revise": "revise",
                    "publish": "publish",
                }
            )

        # 发布 → 结束
        graph.add_edge("publish", END)

        return graph.compile()

    # ============ 节点函数 ============

    def _researcher_node(self, state: MultiAgentState) -> MultiAgentState:
        """研究员节点：搜集资料。"""
        logger.info(f"[Researcher] 开始研究主题: {state['topic']}")
        result = self.researcher.research(state["topic"])
        state["research_result"] = result
        state["messages"] = list(state["messages"]) + [
            AIMessage(content=f"[研究员] 资料收集完成，共 {len(result)} 字")
        ]
        logger.info(f"[Researcher] 资料收集完成，长度={len(result)}")
        return state

    def _writer_node(self, state: MultiAgentState) -> MultiAgentState:
        """写作者节点：撰写文章。"""
        logger.info(f"[Writer] 开始撰写文章，主题: {state['topic']}")
        draft = self.writer.write(
            topic=state["topic"],
            research_material=state["research_result"],
            revision_feedback=state.get("review_result", {}).get("feedback", ""),
            is_revision=state.get("revision_count", 0) > 0,
        )
        state["draft"] = draft
        state["messages"] = list(state["messages"]) + [
            AIMessage(content=f"[写作者] 草稿完成，共 {len(draft)} 字")
        ]
        logger.info(f"[Writer] 草稿完成，长度={len(draft)}")
        return state

    def _reviewer_node(self, state: MultiAgentState) -> MultiAgentState:
        """审校者节点：审校草稿。"""
        logger.info(f"[Reviewer] 开始审校草稿")
        review = self.reviewer.review(
            topic=state["topic"],
            draft=state["draft"],
        )
        state["review_result"] = review
        state["messages"] = list(state["messages"]) + [
            AIMessage(
                content=f"[审校者] {'通过' if review['approved'] else '不通过'}，"
                f"意见: {review.get('feedback', '')[:50]}..."
            )
        ]
        logger.info(f"[Reviewer] 审校完成，通过={review['approved']}")
        return state

    def _revise_node(self, state: MultiAgentState) -> MultiAgentState:
        """修订节点：根据审校意见修订草稿。"""
        state["revision_count"] = state.get("revision_count", 0) + 1
        logger.info(f"[Revise] 开始第 {state['revision_count']} 次修订")
        state["messages"] = list(state["messages"]) + [
            AIMessage(content=f"[修订] 第 {state['revision_count']} 次修订中...")
        ]
        # 修订逻辑在 writer_node 中处理（通过 revision_feedback 参数）
        return state

    def _critic_node(self, state: MultiAgentState) -> MultiAgentState:
        """批评者节点：评价文章质量。"""
        logger.info(f"[Critic] 开始评价文章")
        result = self.critic.evaluate(
            topic=state["topic"],
            article=state["draft"],
        )
        state["critic_result"] = result
        state["messages"] = list(state["messages"]) + [
            AIMessage(
                content=f"[批评者] 评分={result.get('score', 'N/A')}，"
                f"评价: {result.get('comments', '')[:50]}..."
            )
        ]
        logger.info(f"[Critic] 评价完成，评分={result.get('score', 'N/A')}")
        return state

    def _human_review_node(self, state: MultiAgentState) -> MultiAgentState:
        """
        人工审核节点。

        在实际部署中，这里会暂停工作流，等待人工审核结果。
        本实现中，默认自动通过（可通过配置改为交互式）。
        """
        logger.info("[Human Review] 等待人工审核...")
        print("\n" + "=" * 60)
        print("📝 人工审核节点")
        print(f"主题: {state['topic']}")
        print(f"文章长度: {len(state['draft'])} 字")
        print(f"审校意见: {state.get('review_result', {}).get('feedback', '无')}")
        if self.critic and state.get("critic_result"):
            print(f"批评者评分: {state['critic_result'].get('score', 'N/A')}")
        print("=" * 60)

        # 默认自动通过；若需要交互式审核，取消下面注释
        # approval = input("是否通过？(y/n): ").strip().lower()
        # state["human_approved"] = approval == "y"
        state["human_approved"] = True  # 默认通过

        logger.info(f"[Human Review] 审核结果: {state['human_approved']}")
        return state

    def _publish_node(self, state: MultiAgentState) -> MultiAgentState:
        """发布节点：生成最终文章。"""
        logger.info("[Publish] 生成最终文章")
        state["final_article"] = state["draft"]
        state["messages"] = list(state["messages"]) + [
            AIMessage(content=f"[发布] 最终文章已生成，共 {len(state['draft'])} 字")
        ]
        return state

    # ============ 条件路由函数 ============

    def _route_after_review(self, state: MultiAgentState) -> str:
        """
        审校后的路由逻辑。

        决策规则：
        1. 审校通过 → 进入 critic（若启用）或直接 publish
        2. 审校不通过且未达最大修订次数 → revise
        3. 审校不通过且已达最大修订次数 → 强制 publish（接受当前版本）
        """
        review = state.get("review_result", {})
        revision_count = state.get("revision_count", 0)

        if review.get("approved", False):
            logger.info("[Route] 审校通过，进入下一环节")
            return "critic" if self.enable_critic else "publish"

        if revision_count < self.max_revisions:
            logger.info(f"[Route] 审校不通过，打回修订（第 {revision_count + 1} 次）")
            return "revise"
        else:
            logger.warning(
                f"[Route] 已达最大修订次数 ({self.max_revisions})，强制发布当前版本"
            )
            return "critic" if self.enable_critic else "publish"

    def _route_after_critic(self, state: MultiAgentState) -> str:
        """批评者评价后的路由逻辑。"""
        if self.enable_human_review:
            return "human_review"
        return "publish"

    def _route_after_human_review(self, state: MultiAgentState) -> str:
        """人工审核后的路由逻辑。"""
        if state.get("human_approved", True):
            return "publish"
        elif state.get("revision_count", 0) < self.max_revisions:
            return "revise"
        else:
            return "publish"

    # ============ 对外接口 ============

    def run(self, topic: str, user_id: str = "default") -> dict:
        """
        运行完整的多 Agent 工作流。

        Args:
            topic: 文章主题
            user_id: 用户 ID

        Returns:
            结果字典，包含最终文章和各 Agent 的输出
        """
        initial_state: MultiAgentState = {
            "messages": [HumanMessage(content=f"请撰写一篇关于「{topic}」的文章")],
            "topic": topic,
            "user_id": user_id,
            "research_result": "",
            "draft": "",
            "review_result": {},
            "critic_result": {},
            "final_article": "",
            "revision_count": 0,
            "max_revisions": self.max_revisions,
            "human_approved": None,
            "next_action": "research",
        }

        logger.info(f"开始运行多 Agent 工作流，主题: {topic}")
        final_state = self.graph.invoke(initial_state)

        return {
            "topic": topic,
            "research_result": final_state.get("research_result", ""),
            "draft": final_state.get("draft", ""),
            "review_result": final_state.get("review_result", {}),
            "critic_result": final_state.get("critic_result", {}),
            "final_article": final_state.get("final_article", ""),
            "revision_count": final_state.get("revision_count", 0),
            "messages": [m.content for m in final_state.get("messages", [])],
        }


def main():
    """命令行交互式入口。"""
    import os

    if not os.getenv("OPENAI_API_KEY"):
        print("❌ 请设置环境变量 OPENAI_API_KEY")
        return

    orchestrator = MultiAgentOrchestrator(
        max_revisions=2,
        enable_critic=True,
        enable_human_review=False,  # 设为 True 启用人工审核
    )

    print("🤖 多 Agent 系统已启动！")
    print("输入文章主题，系统将自动完成研究 → 写作 → 审校 → 发布")
    print("输入 'exit' 退出\n")

    while True:
        topic = input("文章主题: ").strip()
        if topic.lower() == "exit":
            print("👋 再见！")
            break
        if not topic:
            continue

        print(f"\n⏳ 开始处理，主题: {topic}")
        print("（这可能需要 1-3 分钟，请耐心等待...）\n")

        result = orchestrator.run(topic)

        print("\n" + "=" * 60)
        print("✅ 处理完成！")
        print(f"主题: {result['topic']}")
        print(f"修订次数: {result['revision_count']}")
        print(f"最终文章长度: {len(result['final_article'])} 字")
        if result["critic_result"]:
            print(f"批评者评分: {result['critic_result'].get('score', 'N/A')}")
        print("=" * 60)

        # 保存文章到文件
        output_file = f"output/article_{topic[:20].replace(' ', '_')}.md"
        os.makedirs("output", exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(result["final_article"])
        print(f"📄 文章已保存到: {output_file}\n")


if __name__ == "__main__":
    main()
