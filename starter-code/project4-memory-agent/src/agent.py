"""
有记忆的对话 Agent 主模块

使用 LangGraph 构建具备短期记忆（Redis）和长期记忆（Chroma 向量库）的
对话 Agent，支持流式输出、用户画像和对话摘要。
"""

import os
import json
import asyncio
from typing import TypedDict, Annotated, Sequence, Literal
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.redis import RedisSaver

from src.memory.short_term import ShortTermMemory
from src.memory.long_term import LongTermMemory
from src.memory.summarizer import ConversationSummarizer
from src.tools.profile import UserProfileTool


# ============ 状态定义 ============

class AgentState(TypedDict):
    """Agent 状态，在 LangGraph 节点之间传递。"""
    messages: Annotated[Sequence[BaseMessage], "对话消息列表"]
    user_id: str
    session_id: str
    long_term_context: str  # 从长期记忆检索到的上下文
    summary: str  # 对话摘要
    user_profile: dict  # 用户画像
    next_action: Literal["chat", "update_profile", "summarize", "end"]


# ============ 节点函数 ============

def retrieve_memory(state: AgentState, long_term_mem: LongTermMemory) -> AgentState:
    """
    从长期记忆（Chroma）检索与当前用户输入相关的历史上下文。

    Args:
        state: 当前 Agent 状态
        long_term_mem: 长期记忆实例

    Returns:
        更新了 long_term_context 的状态
    """
    messages = state["messages"]
    user_input = messages[-1].content if messages else ""

    # 从 Chroma 向量库检索相关历史记忆
    relevant_memories = long_term_mem.retrieve(
        user_id=state["user_id"],
        query=user_input,
        top_k=3
    )

    context_str = ""
    if relevant_memories:
        context_str = "以下是与用户当前问题相关的历史对话：\n"
        for i, mem in enumerate(relevant_memories, 1):
            context_str += f"{i}. {mem['content']}\n"

    state["long_term_context"] = context_str
    return state


def generate_response(state: AgentState, llm: ChatOpenAI, short_term_mem: ShortTermMemory) -> AgentState:
    """
    调用 LLM 生成回复，注入长期记忆上下文和用户画像。

    Args:
        state: 当前 Agent 状态
        llm: 语言模型实例
        short_term_mem: 短期记忆实例（用于获取最近对话）

    Returns:
        更新了 messages 的状态
    """
    user_id = state["user_id"]
    session_id = state["session_id"]

    # 获取最近 N 轮对话作为短期上下文
    recent_messages = short_term_mem.get_recent(user_id, session_id, limit=10)

    # 构建系统提示词，注入记忆上下文和用户画像
    system_prompt = """你是一个有记忆能力的智能对话助手。
{profile_section}
{long_term_section}
请根据以上上下文，结合用户当前问题，给出 thoughtful 且个性化的回复。
如果历史对话中有相关信息，请合理引用。""".format(
        profile_section=_build_profile_section(state.get("user_profile", {})),
        long_term_section=state.get("long_term_context", ""),
    )

    # 拼接消息列表
    messages_for_llm = [SystemMessage(content=system_prompt)]
    messages_for_llm.extend(recent_messages)
    messages_for_llm.append(state["messages"][-1])  # 当前用户输入

    # 调用 LLM
    response = llm.invoke(messages_for_llm)
    state["messages"].append(response)

    # 将新对话存入短期记忆（Redis）
    short_term_mem.add_message(user_id, session_id, state["messages"][-2])  # 用户消息
    short_term_mem.add_message(user_id, session_id, response)  # AI 回复

    # 决定下一步动作：每 10 轮触发一次摘要；含个人信息时更新画像
    msg_count = len(state["messages"])
    last_user_msg = state["messages"][-2].content if len(state["messages"]) >= 2 else ""
    personal_keywords = ["我叫", "我是", "我的", "我叫", "my name is", "i am", "i'm"]
    if any(kw in last_user_msg.lower() for kw in personal_keywords):
        state["next_action"] = "update_profile"
    elif msg_count > 0 and msg_count % 20 == 0:
        state["next_action"] = "summarize"
    else:
        state["next_action"] = "chat"

    return state


def update_user_profile(state: AgentState, profile_tool: UserProfileTool) -> AgentState:
    """
    根据对话内容更新用户画像。

    Args:
        state: 当前 Agent 状态
        profile_tool: 用户画像工具实例

    Returns:
        更新了 user_profile 的状态
    """
    messages = state["messages"]
    user_id = state["user_id"]

    # 调用 LLM 提取用户画像信息
    profile_tool.update_from_conversation(
        user_id=user_id,
        messages=messages
    )

    state["user_profile"] = profile_tool.get_profile(user_id)
    return state


def summarize_conversation(state: AgentState, summarizer: ConversationSummarizer, long_term_mem: LongTermMemory, user_id: str, session_id: str) -> AgentState:
    """
    对当前对话进行摘要，并将摘要存入长期记忆（Chroma）。

    Args:
        state: 当前 Agent 状态
        summarizer: 对话摘要器实例
        long_term_mem: 长期记忆实例
        user_id: 用户 ID
        session_id: 会话 ID

    Returns:
        更新了 summary 的状态
    """
    messages = state["messages"]
    summary = summarizer.summarize(messages)
    state["summary"] = summary

    # 将摘要存入 Chroma 长期记忆
    long_term_mem.store(
        user_id=user_id,
        session_id=session_id,
        content=summary,
        metadata={"type": "summary", "session_id": session_id}
    )

    return state


def _build_profile_section(profile: dict) -> str:
    """将用户画像字典格式化为提示词段落。"""
    if not profile:
        return ""
    section = "已知用户画像信息：\n"
    for key, value in profile.items():
        section += f"- {key}: {value}\n"
    return section


def _should_continue(state: AgentState) -> str:
    """路由函数：决定下一步执行哪个节点。"""
    if state.get("next_action") == "end":
        return END
    return state.get("next_action", "chat")


# ============ 图构建 ============

def build_graph(
    llm: ChatOpenAI,
    short_term_mem: ShortTermMemory,
    long_term_mem: LongTermMemory,
    summarizer: ConversationSummarizer,
    profile_tool: UserProfileTool,
) -> StateGraph:
    """
    构建 LangGraph 状态图。

    流程：
    1. retrieve_memory: 从长期记忆检索上下文
    2. generate_response: 生成 LLM 回复
    3. update_user_profile: 更新用户画像（条件执行）
    4. summarize_conversation: 定期摘要对话（条件执行）

    Args:
        llm: 语言模型
        short_term_mem: 短期记忆
        long_term_mem: 长期记忆
        summarizer: 摘要器
        profile_tool: 用户画像工具

    Returns:
        编译后的 LangGraph 应用
    """
    graph = StateGraph(AgentState)

    # 封装节点函数，注入外部依赖
    def retrieve_node(state: AgentState) -> AgentState:
        return retrieve_memory(state, long_term_mem)

    def generate_node(state: AgentState) -> AgentState:
        return generate_response(state, llm, short_term_mem)

    def profile_node(state: AgentState) -> AgentState:
        return update_user_profile(state, profile_tool)

    def summarize_node(state: AgentState) -> AgentState:
        return summarize_conversation(
            state, summarizer, long_term_mem,
            state["user_id"], state["session_id"]
        )

    # 添加节点
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("generate", generate_node)
    graph.add_node("update_profile", profile_node)
    graph.add_node("summarize", summarize_node)

    # 设置入口
    graph.set_entry_point("retrieve")

    # 添加边
    graph.add_edge("retrieve", "generate")

    # 条件路由：生成回复后是否更新画像 / 摘要
    graph.add_conditional_edges(
        "generate",
        _should_continue,
        {
            "update_profile": "update_profile",
            "summarize": "summarize",
            "chat": END,
            "end": END,
        }
    )

    graph.add_edge("update_profile", "generate")
    graph.add_edge("summarize", END)

    return graph.compile()


# ============ 主入口 ============

def main():
    """命令行交互式对话入口。"""
    import uuid

    # 从环境变量读取配置
    openai_api_key = os.getenv("OPENAI_API_KEY", "")
    openai_base_url = os.getenv("OPENAI_BASE_URL", None)
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    chroma_host = os.getenv("CHROMA_HOST", "localhost")
    chroma_port = int(os.getenv("CHROMA_PORT", "8000"))

    if not openai_api_key:
        print("❌ 请设置环境变量 OPENAI_API_KEY")
        return

    # 初始化 LLM
    llm = ChatOpenAI(
        model=os.getenv("MODEL_NAME", "gpt-4o-mini"),
        api_key=openai_api_key,
        base_url=openai_base_url,
        temperature=0.7,
        streaming=True,
    )

    # 初始化记忆模块
    short_term_mem = ShortTermMemory(redis_url=redis_url)
    long_term_mem = LongTermMemory(
        host=chroma_host,
        port=chroma_port,
        collection_name="conversation_memory"
    )
    summarizer = ConversationSummarizer(llm=llm)
    profile_tool = UserProfileTool(llm=llm)

    # 构建 LangGraph 应用
    app = build_graph(llm, short_term_mem, long_term_mem, summarizer, profile_tool)

    # 交互式对话循环
    user_id = input("请输入用户 ID（或按回车使用随机 ID）: ").strip() or str(uuid.uuid4())
    session_id = str(uuid.uuid4())

    print(f"\n✅ 对话开始！user_id={user_id}, session_id={session_id}")
    print("输入 'exit' 退出，输入 'profile' 查看用户画像，输入 'clear' 清空短期记忆\n")

    messages: list[BaseMessage] = []

    while True:
        user_input = input("你: ").strip()
        if user_input.lower() == "exit":
            print("👋 再见！")
            break
        if user_input.lower() == "profile":
            profile = profile_tool.get_profile(user_id)
            print(f"📋 用户画像: {json.dumps(profile, ensure_ascii=False, indent=2)}")
            continue
        if user_input.lower() == "clear":
            short_term_mem.clear_session(user_id, session_id)
            messages = []
            print("🧹 短期记忆已清空")
            continue

        # 构建初始状态
        messages.append(HumanMessage(content=user_input))
        initial_state: AgentState = {
            "messages": messages,
            "user_id": user_id,
            "session_id": session_id,
            "long_term_context": "",
            "summary": "",
            "user_profile": profile_tool.get_profile(user_id),
            "next_action": "chat",
        }

        # 执行图
        final_state = app.invoke(initial_state)
        messages = list(final_state["messages"])

        # 输出 AI 回复
        ai_reply = final_state["messages"][-1].content
        print(f"🤖: {ai_reply}\n")


if __name__ == "__main__":
    main()
