"""
FastAPI 应用 - 智能体工程师培养计划 项目7
提供简单的 Agent API 服务，用于演示 Docker 部署
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict
import uvicorn
import logging
import asyncio
import os
from datetime import datetime

# ============================================================
# 日志配置
# ============================================================
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================
# FastAPI 应用初始化
# ============================================================
app = FastAPI(
    title="Agent API Service",
    description="智能体工程师培养计划 - 项目7：容器化与部署",
    version="1.0.0"
)

# ============================================================
# 数据模型
# ============================================================
class ChatMessage(BaseModel):
    """聊天消息模型"""
    role: str
    content: str

class ChatRequest(BaseModel):
    """聊天请求模型"""
    messages: List[ChatMessage]
    model: Optional[str] = "gpt-4o-mini"
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 1000

class ChatResponse(BaseModel):
    """聊天响应模型"""
    message: str
    model: str
    tokens_used: int
    latency_ms: int

class HealthResponse(BaseModel):
    """健康检查响应模型"""
    status: str
    timestamp: str
    version: str

# ============================================================
# 路由
# ============================================================
@app.get("/")
async def root():
    """根路径 - 返回 API 信息"""
    return {
        "service": "Agent API Service",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "chat": "/api/v1/chat",
            "docs": "/docs",
            "openapi": "/openapi.json"
        }
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查端点
    
    用于 Docker 健康检查、负载均衡器健康检查
    返回服务状态和基本信息
    """
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat() + "Z",
        version="1.0.0"
    )

@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """聊天 API 端点
    
    接收用户消息，调用 LLM 生成回复
    
    Args:
        request: 聊天请求，包含消息列表和参数
        
    Returns:
        聊天响应，包含回复消息和元数据
    """
    start_time = time.time()
    
    try:
        # 这里只是演示，实际应该调用 OpenAI API
        # 为了演示部署，这里返回模拟响应
        logger.info(f"Received chat request with {len(request.messages)} messages")
        
        # 模拟 LLM 调用延迟
        await asyncio.sleep(0.5)
        
        # 构造模拟响应
        response_message = f"这是一个模拟回复。您发送了 {len(request.messages)} 条消息。实际部署时应调用 OpenAI API。"
        
        latency_ms = int((time.time() - start_time) * 1000)
        
        logger.info(f"Chat request completed in {latency_ms}ms")
        
        return ChatResponse(
            message=response_message,
            model=request.model,
            tokens_used=150,  # 模拟 Token 使用
            latency_ms=latency_ms
        )
        
        except Exception as e:
            logger.error(f"Chat request failed: {str(e)}")
            # 生产环境不暴露内部错误信息
            if os.getenv("ENVIRONMENT", "development") == "production":
                raise HTTPException(status_code=500, detail="Internal server error")
            else:
                raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/models")
async def list_models():
    """列出可用模型
    
    Returns:
        可用模型列表
    """
    return {
        "models": [
            {"id": "gpt-4o-mini", "provider": "openai", "context_window": 128000},
            {"id": "gpt-4o", "provider": "openai", "context_window": 128000},
            {"id": "claude-3.5-sonnet", "provider": "anthropic", "context_window": 200000}
        ]
    }

# ============================================================
# 启动入口
# ============================================================
if __name__ == "__main__":
    """主入口 - 启动 FastAPI 应用"""
    port = int(os.getenv("PORT", 8000))
    
    logger.info(f"Starting Agent API Service on port {port}")
    
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=port,
        workers=2,
        log_level="info"
    )
