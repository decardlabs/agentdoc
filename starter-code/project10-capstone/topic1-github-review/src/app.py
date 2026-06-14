"""
GitHub Code Review Agent - FastAPI 主应用
提供 Webhook 接收、API 端点和健康检查
"""

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uvicorn
import logging
import os
import hmac
import hashlib
from datetime import datetime

from src.github_webhook import GitHubWebhookHandler
from src.agent.review_agent import ReviewAgent

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="GitHub Code Review Agent",
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

webhook_handler = GitHubWebhookHandler()
review_agent = ReviewAgent()


class ReviewRequest(BaseModel):
    repo_owner: str
    repo_name: str
    pr_number: int
    github_token: Optional[str] = None
    review_level: Optional[str] = "normal"


class ManualReviewResponse(BaseModel):
    pr_number: int
    repo: str
    review_comments: List[Dict]
    summary: str
    generated_at: str


@app.get("/")
async def root():
    return {
        "service": "GitHub Code Review Agent",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "webhook": "/webhook/github",
            "manual_review": "/api/v1/review",
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
            "webhook_handler": "ok",
            "review_agent": "ok"
        }
    }


@app.post("/webhook/github")
async def github_webhook(request: Request, background_tasks: BackgroundTasks):
    """接收 GitHub Webhook 事件"""
    body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")
    event_type = request.headers.get("X-GitHub-Event", "")

    webhook_secret = os.getenv("GITHUB_WEBHOOK_SECRET", "")
    if webhook_secret:
        mac = hmac.new(webhook_secret.encode(), body, hashlib.sha256)
        expected_signature = "sha256=" + mac.hexdigest()
        if not hmac.compare_digest(signature, expected_signature):
            logger.warning("Webhook 签名验证失败")
            raise HTTPException(status_code=401, detail="Invalid signature")

    if event_type not in ["pull_request", "pull_request_review_comment"]:
        return JSONResponse(content={"message": "非 PR 事件，忽略"}, status_code=200)

    payload = await request.json()

    action = payload.get("action", "")
    if action not in ["opened", "synchronize", "reopened"]:
        return JSONResponse(content={"message": f"PR 动作 '{action}' 无需审查"}, status_code=200)

    background_tasks.add_task(webhook_handler.process_pr_event, payload)

    return JSONResponse(content={"message": "Webhook 已接收，正在处理"}, status_code=202)


@app.post("/api/v1/review", response_model=ManualReviewResponse)
async def manual_review(request: ReviewRequest):
    """手动触发 PR 代码审查"""
    try:
        logger.info(f"手动触发审查: {request.repo_owner}/{request.repo_name}#${request.pr_number}")

        result = await review_agent.review_pr(
            repo_owner=request.repo_owner,
            repo_name=request.repo_name,
            pr_number=request.pr_number,
            github_token=request.github_token,
            review_level=request.review_level
        )

        return ManualReviewResponse(
            pr_number=request.pr_number,
            repo=f"{request.repo_owner}/{request.repo_name}",
            review_comments=result["comments"],
            summary=result["summary"],
            generated_at=datetime.utcnow().isoformat() + "Z"
        )

    except Exception as e:
        logger.error(f"手动审查失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/reviews")
async def list_reviews(repo: Optional[str] = None, limit: int = 50):
    """查询历史审查记录"""
    return {
        "reviews": [],
        "total": 0,
        "message": "历史记录功能待实现"
    }


@app.get("/metrics")
async def metrics():
    """Prometheus 指标端点"""
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    from fastapi import Response

    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    logger.info(f"启动 GitHub Code Review Agent，端口: {port}")
    uvicorn.run("src.app:app", host="0.0.0.0", port=port, workers=2, log_level="info")
