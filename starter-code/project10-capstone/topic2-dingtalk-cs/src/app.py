"""
钉钉客服 Agent - FastAPI 主应用
提供钉钉消息接收、API 端点和健康检查
"""

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uvicorn
import logging
import os
import hmac
import hashlib
import base64
import time
from datetime import datetime
from urllib.parse import unquote

from src.agent.cs_agent import CustomerServiceAgent

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="钉钉智能客服 Agent",
    description="智能体工程师培养计划 - 项目 10：端到端 Agent 应用（毕业设计）",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

cs_agent = CustomerServiceAgent()


class ChatMessage(BaseModel):
    """聊天消息"""
    user_id: str
    message: str
    session_id: Optional[str] = None
    msg_type: Optional[str] = "text"


class ChatResponse(BaseModel):
    """聊天响应"""
    reply: str
    session_id: str
    intent: Optional[str] = None
    confidence: Optional[float] = None


class WebhookEvent(BaseModel):
    """钉钉 Webhook 事件"""
    msgtype: Optional[str] = None
    text: Optional[Dict] = None
    at_users: Optional[List] = None


@app.get("/")
async def root():
    return {
        "service": "钉钉智能客服 Agent",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "webhook": "/webhook/dingtalk",
            "chat": "/api/v1/chat",
            "health": "/health",
            "docs": "/docs"
        }
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "version": "1.0.0",
        "components": {
            "cs_agent": "ok",
            "llm": "ok"
        }
    }


@app.post("/webhook/dingtalk")
async def dingtalk_webhook(request: Request, background_tasks: BackgroundTasks):
    """接收钉钉机器人 Webhook 消息"""
    try:

        body = await request.body()
        timestamp = request.headers.get("timestamp", "")
        sign = request.headers.get("sign", "")

        if not validate_dingtalk_signature(timestamp, sign, body):
            raise HTTPException(status_code=401, detail="Invalid signature")

        payload = await request.json()

        msg_type = payload.get("msgtype", "")
        if msg_type != "text":
            return JSONResponse(content={"msgtype": "text", "text": {"content": "暂不支持此消息类型"}}, status_code=200)

        text_content = payload.get("text", {}).get("content", "")
        sender_id = payload.get("senderId", "unknown")
        conversation_id = payload.get("conversationId", "default")

        background_tasks.add_task(
            process_dingtalk_message,
            sender_id=sender_id,
            conversation_id=conversation_id,
            message=text_content
        )

        return JSONResponse(
            content={"status": "received", "message": "消息已接收，正在处理"},
            status_code=200
        )

    except Exception as e:
        logger.error(f"处理钉钉 Webhook 失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat(request: ChatMessage):
    """主动聊天接口"""
    try:
        logger.info(f"收到聊天请求: user={request.user_id}, session={request.session_id}")

        result = await cs_agent.handle_message(
            user_id=request.user_id,
            message=request.message,
            session_id=request.session_id or f"session_{request.user_id}"
        )

        return ChatResponse(
            reply=result["reply"],
            session_id=result["session_id"],
            intent=result.get("intent"),
            confidence=result.get("confidence")
        )

    except Exception as e:
        logger.error(f"聊天处理失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/sessions/{session_id}")
async def get_session(session_id: str):
    """获取会话历史"""
    history = cs_agent.get_session_history(session_id)
    return {"session_id": session_id, "history": history}


@app.delete("/api/v1/sessions/{session_id}")
async def clear_session(session_id: str):
    """清除会话历史"""
    cs_agent.clear_session(session_id)
    return {"status": "cleared", "session_id": session_id}


def validate_dingtalk_signature(timestamp: str, sign: str, body: bytes) -> bool:
    """验证钉钉签名"""
    app_secret = os.getenv("DINGTALK_APP_SECRET", "")
    if not app_secret:
        logger.warning("未配置 DINGTALK_APP_SECRET，跳过签名验证")
        return True

    try:
        string_to_sign = f"{timestamp}\n{app_secret}"
        hmac_code = hmac.new(
            app_secret.encode(),
            string_to_sign.encode(),
            hashlib.sha256
        ).digest()

        computed_sign = base64.b64encode(hmac_code).decode()
        return computed_sign == sign

    except Exception as e:
        logger.error(f"签名验证异常: {str(e)}")
        return False


async def process_dingtalk_message(sender_id: str, conversation_id: str, message: str):
    """处理钉钉消息（后台任务）"""
    try:
        result = await cs_agent.handle_message(
            user_id=sender_id,
            message=message,
            session_id=conversation_id
        )

        reply_text = result["reply"]

        logger.info(f"生成回复: {reply_text[:100]}...")

    except Exception as e:
        logger.error(f"处理钉钉消息失败: {str(e)}")


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    logger.info(f"启动钉钉智能客服 Agent，端口: {port}")
    uvicorn.run("src.app:app", host="0.0.0.0", port=port, workers=2, log_level="info")
