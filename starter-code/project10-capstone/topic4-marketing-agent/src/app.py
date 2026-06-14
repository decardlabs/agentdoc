"""
营销内容生成 Agent - FastAPI 主应用
提供内容生成、API 端点和健康检查
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uvicorn
import logging
import os
from datetime import datetime
from pathlib import Path

from src.agent.content_agent import ContentAgent

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="营销内容生成 Agent",
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

content_agent = ContentAgent()


class ContentRequest(BaseModel):
    """内容生成请求"""
    topic: str
    content_type: str = "wechat"
    tone: Optional[str] = "professional"
    length: Optional[int] = 800
    keywords: Optional[List[str]] = None
    target_audience: Optional[str] = None
    brand_voice: Optional[str] = None


class ContentResponse(BaseModel):
    """内容生成响应"""
    content: str
    title: Optional[str] = None
    hashtags: Optional[List[str]] = None
    seo_keywords: Optional[List[str]] = None


class BatchRequest(BaseModel):
    """批量生成请求"""
    requests: List[ContentRequest]
    generate_images: Optional[bool] = False


class BatchResponse(BaseModel):
    """批量生成响应"""
    results: List[Dict]
    total: int
    failed: int


@app.get("/")
async def root():
    return {
        "service": "营销内容生成 Agent",
        "version": "1.0.0",
        "status": "running",
        "content_types": ["wechat", "xiaohongshu", "weibo", "email", "blog"],
        "endpoints": {
            "generate": "/api/v1/generate",
            "batch": "/api/v1/batch",
            "templates": "/api/v1/templates",
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
            "content_agent": "ok",
            "llm": "ok"
        }
    }


@app.post("/api/v1/generate", response_model=ContentResponse)
async def generate_content(request: ContentRequest, background_tasks: BackgroundTasks):
    """生成营销内容"""
    try:
        logger.info(f"生成内容: topic={request.topic}, type={request.content_type}")

        result = await content_agent.generate(
            topic=request.topic,
            content_type=request.content_type,
            tone=request.tone,
            length=request.length,
            keywords=request.keywords,
            target_audience=request.target_audience,
            brand_voice=request.brand_voice
        )

        return ContentResponse(
            content=result["content"],
            title=result.get("title"),
            hashtags=result.get("hashtags"),
            seo_keywords=result.get("seo_keywords")
        )

    except Exception as e:
        logger.error(f"生成内容失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/batch", response_model=BatchResponse)
async def batch_generate(request: BatchRequest, background_tasks: BackgroundTasks):
    """批量生成内容"""
    try:
        logger.info(f"批量生成: {len(request.requests)} 个任务")

        results = []
        failed = 0

        for req in request.requests:
            try:
                result = await content_agent.generate(
                    topic=req.topic,
                    content_type=req.content_type,
                    tone=req.tone,
                    length=req.length,
                    keywords=req.keywords,
                    target_audience=req.target_audience,
                    brand_voice=req.brand_voice
                )

                results.append({
                    "topic": req.topic,
                    "content_type": req.content_type,
                    "success": True,
                    "content": result["content"],
                    "title": result.get("title")
                })

            except Exception as e:
                logger.error(f"批量生成失败: {req.topic}, {str(e)}")
                failed += 1
                results.append({
                    "topic": req.topic,
                    "content_type": req.content_type,
                    "success": False,
                    "error": str(e)
                })

        return BatchResponse(
            results=results,
            total=len(request.requests),
            failed=failed
        )

    except Exception as e:
        logger.error(f"批量生成失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/templates")
async def get_templates(content_type: Optional[str] = None):
    """获取内容模板"""
    try:
        templates = content_agent.get_templates(content_type)
        return {"templates": templates, "total": len(templates)}

    except Exception as e:
        logger.error(f"获取模板失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/templates")
async def create_template(
    name: str,
    content_type: str,
    template: str,
    description: Optional[str] = None
):
    """创建内容模板"""
    try:
        content_agent.create_template(
            name=name,
            content_type=content_type,
            template=template,
            description=description
        )

        return {"status": "created", "name": name}

    except Exception as e:
        logger.error(f"创建模板失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/optimize")
async def optimize_content(content: str = Body(...), platform: str = "wechat"):
    """优化内容（SEO、可读性等）"""
    try:
        logger.info(f"优化内容: platform={platform}")

        result = await content_agent.optimize(content, platform)

        return {
            "original": content,
            "optimized": result["optimized"],
            "suggestions": result["suggestions"],
            "seo_score": result.get("seo_score")
        }

    except Exception as e:
        logger.error(f"优化内容失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/generate-image")
async def generate_image(prompt: str = Body(...), style: str = "photorealistic"):
    """生成配图（可选功能）"""
    try:
        logger.info(f"生成配图: prompt={prompt[:50]}...")

        result = await content_agent.generate_image(prompt, style)

        return {
            "status": "generated",
            "image_url": result.get("image_url"),
            "prompt": prompt
        }

    except Exception as e:
        logger.error(f"生成配图失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    logger.info(f"启动营销内容生成 Agent，端口: {port}")
    uvicorn.run("src.app:app", host="0.0.0.0", port=port, workers=2, log_level="info")
