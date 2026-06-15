"""
FastAPI 服务模块

提供 HTTP API 接口，支持：
- 流式对话（Server-Sent Events）
- 用户画像查询与更新
- 记忆管理（清空、查询）
- 健康检查
"""

import os
import json
import uuid
import logging
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.agent import build_graph, AgentState
from src.memory.short_term import ShortTermMemory
from src.memory.long_term import LongTermMemory
from src.memory.summarizer import ConversationSummarizer
from src.tools.profile import UserProfileTool
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============ 全局初始化 ============

# 在应用启动时初始化一次，避免重复连接
openai_api_key = os.getenv("OPENAI_API_KEY", "")
openai_base_url = os.getenv("OPENAI_BASE_URL", None)
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
chroma_host = os.getenv("CHROMA_HOST", "localhost")
chroma_port = int(os.getenv("CHROMA_PORT", "8000"))

llm = ChatOpenAI(
    model=os.getenv("MODEL_NAME", "gpt-4o-mini"),
    api_key=openai_api_key,
    base_url=openai_base_url,
    temperature=0.7,
    streaming=True,
)

short_term_mem = ShortTermMemory(redis_url=redis_url)
long_term_mem = LongTermMemory(host=chroma_host, port=chroma_port)
summarizer = ConversationSummarizer(llm=llm)
profile_tool = UserProfileTool(llm=llm)

app_graph = build_graph(llm, short_term_mem, long_term_mem, summarizer, profile_tool)

# ============ FastAPI 应用 ============

app = FastAPI(
    title="有记忆的对话 Agent API",
    description="基于 LangGraph 的有记忆对话 Agent，支持短期（Redis）和长期（Chroma）记忆",
    version="1.0.0",
)

# ============ 请求/响应模型 ============


class ChatRequest(BaseModel):
    """对话请求体。"""
    user_id: str
    session_id: Optional[str] = None
    message: str
    stream: bool = True  # 是否使用流式输出


class ChatResponse(BaseModel):
    """非流式对话响应体。"""
    user_id: str
    session_id: str
    reply: str
    user_profile: dict


class ProfileResponse(BaseModel):
    """用户画像响应体。"""
    user_id: str
    profile: dict


# ============ API 路由 ============


@app.get("/health")
async def health_check():
    """健康检查接口。"""
    return {"status": "ok", "service": "memory-agent"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    非流式对话接口。

    发送一条消息并获取完整回复。
    """
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="消息内容不能为空")

    session_id = request.session_id or str(uuid.uuid4())
    messages = short_term_mem.get_all(request.user_id, session_id)
    messages.append(HumanMessage(content=request.message))

    initial_state: AgentState = {
        "messages": messages,
        "user_id": request.user_id,
        "session_id": session_id,
        "long_term_context": "",
        "summary": "",
        "user_profile": profile_tool.get_profile(request.user_id),
        "next_action": "chat",
    }

    final_state = await app_graph.ainvoke(initial_state)
    ai_reply = final_state["messages"][-1].content

    return ChatResponse(
        user_id=request.user_id,
        session_id=session_id,
        reply=ai_reply,
        user_profile=final_state.get("user_profile", {}),
    )


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    流式对话接口（Server-Sent Events）。

    返回 text/event-stream，逐 token 推送 AI 回复。
    """
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="消息内容不能为空")

    session_id = request.session_id or str(uuid.uuid4())

    async def event_generator():
        """生成 SSE 事件流。"""
        # 先检索长期记忆上下文
        relevant = long_term_mem.retrieve(
            user_id=request.user_id,
            query=request.message,
            top_k=3,
        )
        long_term_context = ""
        if relevant:
            long_term_context = "历史相关记忆：\n"
            for i, mem in enumerate(relevant, 1):
                long_term_context += f"{i}. {mem['content']}\n"

        # 获取短期记忆
        recent = short_term_mem.get_recent(request.user_id, session_id, limit=10)

        # 构造消息
        from langchain_core.messages import SystemMessage
        system_prompt = f"你是一个有记忆能力的智能助手。\n{long_term_context}"
        messages_for_llm = [SystemMessage(content=system_prompt)] + recent + [
            HumanMessage(content=request.message)
        ]

        # 流式调用 LLM
        full_reply = ""
        async for chunk in llm.astream(messages_for_llm):
            token = chunk.content
            if token:
                full_reply += token
                yield f"data: {json.dumps({'token': token}, ensure_ascii=False)}\n\n"

        # 存储消息到短期记忆
        short_term_mem.add_message(request.user_id, session_id, HumanMessage(content=request.message))
        short_term_mem.add_message(request.user_id, session_id, AIMessage(content=full_reply))

        # 结束事件
        yield f"data: {json.dumps({'done': True, 'session_id': session_id}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@app.get("/profile/{user_id}", response_model=ProfileResponse)
async def get_profile(user_id: str):
    """获取指定用户的画像。"""
    profile = profile_tool.get_profile(user_id)
    return ProfileResponse(user_id=user_id, profile=profile)


@app.post("/profile/{user_id}/reset")
async def reset_profile(user_id: str):
    """重置指定用户的画像。"""
    profile_tool.reset_profile(user_id)
    return {"status": "ok", "message": f"用户 {user_id} 的画像已重置"}


@app.delete("/memory/short/{user_id}/{session_id}")
async def clear_short_term(user_id: str, session_id: str):
    """清空指定会话的短期记忆。"""
    short_term_mem.clear_session(user_id, session_id)
    return {"status": "ok", "message": f"会话 {session_id} 的短期记忆已清空"}


@app.delete("/memory/long/{user_id}")
async def clear_long_term(user_id: str):
    """清空指定用户的长期记忆。"""
    long_term_mem.delete_user_memory(user_id)
    return {"status": "ok", "message": f"用户 {user_id} 的长期记忆已清空"}


@app.get("/memory/long/{user_id}")
async def get_long_term(user_id: str, query: str = "", top_k: int = 3):
    """检索用户的长期记忆（用于调试）。"""
    if query:
        results = long_term_mem.retrieve(user_id=user_id, query=query, top_k=top_k)
    else:
        results = long_term_mem.get_all_for_user(user_id)
    return {"user_id": user_id, "memories": results}


# ============ 启动入口 ============

if __name__ == "__main__":
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    logger.info(f"启动 API 服务，地址 http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)
