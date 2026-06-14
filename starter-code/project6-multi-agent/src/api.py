"""
FastAPI 服务模块

为多 Agent 系统提供 HTTP API 接口，支持：
- 提交文章写作任务
- 查询任务状态和结果
- 人工审核接口
- 获取各 Agent 的输出
"""

import os
import json
import uuid
import logging
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel

from src.orchestrator import MultiAgentOrchestrator

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============ 全局初始化 ============

openai_api_key = os.getenv("OPENAI_API_KEY", "")
openai_base_url = os.getenv("OPENAI_BASE_URL", None)

orchestrator = MultiAgentOrchestrator(
    max_revisions=int(os.getenv("MAX_REVISIONS", "2")),
    enable_critic=os.getenv("ENABLE_CRITIC", "true").lower() == "true",
    enable_human_review=os.getenv("ENABLE_HUMAN_REVIEW", "false").lower() == "true",
)

# 任务存储（简单内存存储，生产环境应使用 Redis 或数据库）
tasks_db = {}

# ============ FastAPI 应用 ============

app = FastAPI(
    title="多 Agent 系统 API",
    description="基于 LangGraph 的 4 Agent 协作写作系统",
    version="1.0.0",
)

# ============ 请求/响应模型 ============

class WriteRequest(BaseModel):
    """写作任务请求体。"""
    topic: str
    user_id: Optional[str] = "default"
    style: Optional[str] = "科普"
    enable_critic: Optional[bool] = True
    enable_human_review: Optional[bool] = False


class WriteResponse(BaseModel):
    """写作任务响应体。"""
    task_id: str
    topic: str
    status: str


class TaskStatusResponse(BaseModel):
    """任务状态响应体。"""
    task_id: str
    topic: str
    status: str
    revision_count: int
    progress: list[str]


class TaskResultResponse(BaseModel):
    """任务结果响应体。"""
    task_id: str
    topic: str
    status: str
    research_result: str
    draft: str
    review_result: dict
    critic_result: dict
    final_article: str


# ============ API 路由 ============

@app.get("/health")
async def health_check():
    """健康检查接口。"""
    return {"status": "ok", "service": "multi-agent-system"}


@app.post("/write", response_model=WriteResponse)
async def submit_write_task(request: WriteRequest, background_tasks: BackgroundTasks):
    """
    提交文章写作任务（异步执行）。

    返回 task_id，可用于查询任务状态和结果。
    """
    if not request.topic.strip():
        raise HTTPException(status_code=400, detail="文章主题不能为空")

    task_id = str(uuid.uuid4())

    # 初始化任务状态
    tasks_db[task_id] = {
        "task_id": task_id,
        "topic": request.topic,
        "user_id": request.user_id,
        "status": "pending",
        "revision_count": 0,
        "progress": [],
        "result": None,
        "error": None,
    }

    # 添加后台任务
    background_tasks.add_task(
        _run_write_task,
        task_id=task_id,
        topic=request.topic,
        user_id=request.user_id,
        enable_critic=request.enable_critic,
        enable_human_review=request.enable_human_review,
    )

    logger.info(f"提交写作任务，task_id={task_id}，topic={request.topic}")

    return WriteResponse(
        task_id=task_id,
        topic=request.topic,
        status="pending",
    )


@app.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """查询任务状态。"""
    if task_id not in tasks_db:
        raise HTTPException(status_code=404, detail="任务不存在")

    task = tasks_db[task_id]
    return TaskStatusResponse(
        task_id=task_id,
        topic=task["topic"],
        status=task["status"],
        revision_count=task["revision_count"],
        progress=task["progress"],
    )


@app.get("/tasks/{task_id}/result", response_model=TaskResultResponse)
async def get_task_result(task_id: str):
    """获取任务结果（任务完成后可用）。"""
    if task_id not in tasks_db:
        raise HTTPException(status_code=404, detail="任务不存在")

    task = tasks_db[task_id]

    if task["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"任务尚未完成，当前状态：{task['status']}",
        )

    result = task.get("result", {})
    return TaskResultResponse(
        task_id=task_id,
        topic=task["topic"],
        status=task["status"],
        research_result=result.get("research_result", ""),
        draft=result.get("draft", ""),
        review_result=result.get("review_result", {}),
        critic_result=result.get("critic_result", {}),
        final_article=result.get("final_article", ""),
    )


@app.get("/tasks/{task_id}/article")
async def download_article(task_id: str):
    """下载最终文章（Markdown 格式）。"""
    if task_id not in tasks_db:
        raise HTTPException(status_code=404, detail="任务不存在")

    task = tasks_db[task_id]

    if task["status"] != "completed":
        raise HTTPException(status_code=400, detail="任务尚未完成")

    article = task.get("result", {}).get("final_article", "")

    return JSONResponse(
        content={"article": article},
        headers={
            "Content-Disposition": f'attachment; filename="article_{task_id}.md"',
        },
    )


@app.post("/tasks/{task_id}/approve")
async def approve_task(task_id: str, approved: bool = True):
    """
    人工审核接口（启用人工审核节点时使用）。

    当 enable_human_review=True 时，审校通过后会等待人工审核。
    调用此接口通过或拒绝审核。
    """
    if task_id not in tasks_db:
        raise HTTPException(status_code=404, detail="任务不存在")

    task = tasks_db[task_id]
    task["human_approved"] = approved
    task["progress"].append(f"人工审核：{'通过' if approved else '拒绝'}")

    logger.info(f"任务 {task_id} 人工审核结果：{approved}")
    return {"status": "ok", "approved": approved}


@app.get("/tasks")
async def list_tasks(limit: int = 20, status: Optional[str] = None):
    """列出所有任务（支持按状态过滤）。"""
    tasks = list(tasks_db.values())

    if status:
        tasks = [t for t in tasks if t["status"] == status]

    tasks = sorted(tasks, key=lambda x: x.get("created_at", ""), reverse=True)
    return {"total": len(tasks), "tasks": tasks[:limit]}


# ============ 后台任务函数 ============

def _run_write_task(
    task_id: str,
    topic: str,
    user_id: str,
    enable_critic: bool,
    enable_human_review: bool,
):
    """
    后台执行写作任务。

    Args:
        task_id: 任务 ID
        topic: 文章主题
        user_id: 用户 ID
        enable_critic: 是否启用批评者
        enable_human_review: 是否启用人工审核
    """
    task = tasks_db[task_id]
    task["status"] = "running"
    task["progress"].append("任务开始执行")

    try:
        # 更新编排器配置
        orchestrator.enable_critic = enable_critic
        orchestrator.enable_human_review = enable_human_review

        # 执行工作流
        task["progress"].append("研究员采集中...")
        result = orchestrator.run(topic, user_id)

        # 保存结果
        task["status"] = "completed"
        task["result"] = result
        task["revision_count"] = result.get("revision_count", 0)
        task["progress"].append(f"任务完成，修订次数：{result.get('revision_count', 0)}")

        logger.info(f"任务 {task_id} 完成")

    except Exception as e:
        task["status"] = "failed"
        task["error"] = str(e)
        task["progress"].append(f"任务失败：{e}")
        logger.error(f"任务 {task_id} 失败：{e}")


# ============ 启动入口 ============

if __name__ == "__main__":
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    logger.info(f"启动 API 服务，地址 http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)
