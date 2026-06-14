"""
Obsidian 知识助手 - FastAPI 主应用
提供笔记查询、知识检索、API 端点和健康检查
"""

from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uvicorn
import logging
import os
from datetime import datetime
from pathlib import Path

from src.agent.knowledge_agent import KnowledgeAgent
from src.tools.obsidian_tools import ObsidianTools

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Obsidian 知识助手",
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

knowledge_agent = KnowledgeAgent()
obsidian_tools = ObsidianTools(vault_path=os.getenv("OBSIDIAN_VAULT_PATH", "/vault"))


class SearchRequest(BaseModel):
    """搜索请求"""
    query: str
    top_k: Optional[int] = 5
    folder: Optional[str] = None


class SearchResult(BaseModel):
    """搜索结果"""
    file_path: str
    title: str
    content_snippet: str
    score: float
    tags: List[str]


class QuestionRequest(BaseModel):
    """提问请求"""
    question: str
    context_files: Optional[List[str]] = None


class QuestionResponse(BaseModel):
    """提问响应"""
    answer: str
    sources: List[Dict]
    confidence: float


class CreateNoteRequest(BaseModel):
    """创建笔记请求"""
    title: str
    content: str
    folder: Optional[str] = None
    tags: Optional[List[str]] = None


@app.get("/")
async def root():
    return {
        "service": "Obsidian 知识助手",
        "version": "1.0.0",
        "status": "running",
        "vault_path": os.getenv("OBSIDIAN_VAULT_PATH", "/vault"),
        "endpoints": {
            "search": "/api/v1/search",
            "ask": "/api/v1/ask",
            "create_note": "/api/v1/notes",
            "list_notes": "/api/v1/notes",
            "get_note": "/api/v1/notes/{file_path}",
            "health": "/health",
            "docs": "/docs"
        }
    }


@app.get("/health")
async def health_check():
    vault_path = os.getenv("OBSIDIAN_VAULT_PATH", "/vault")
    vault_exists = os.path.exists(vault_path)

    return {
        "status": "healthy" if vault_exists else "degraded",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "version": "1.0.0",
        "components": {
            "knowledge_agent": "ok",
            "obsidian_tools": "ok" if vault_exists else "vault_not_found",
            "llm": "ok"
        }
    }


@app.post("/api/v1/search", response_model=List[SearchResult])
async def search_notes(request: SearchRequest):
    """搜索笔记"""
    try:
        logger.info(f"搜索笔记: query={request.query}, top_k={request.top_k}")

        results = await knowledge_agent.search(
            query=request.query,
            top_k=request.top_k,
            folder=request.folder
        )

        return [
            SearchResult(
                file_path=r["file_path"],
                title=r["title"],
                content_snippet=r["snippet"],
                score=r["score"],
                tags=r.get("tags", [])
            ) for r in results
        ]

    except Exception as e:
        logger.error(f"搜索失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/ask", response_model=QuestionResponse)
async def ask_question(request: QuestionRequest):
    """基于知识库提问"""
    try:
        logger.info(f"提问: {request.question[:50]}...")

        result = await knowledge_agent.answer_question(
            question=request.question,
            context_files=request.context_files
        )

        return QuestionResponse(
            answer=result["answer"],
            sources=result["sources"],
            confidence=result["confidence"]
        )

    except Exception as e:
        logger.error(f"提问失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/notes")
async def list_notes(folder: Optional[str] = Query(None)):
    """列出笔记"""
    try:
        notes = obsidian_tools.list_notes(folder=folder)
        return {"notes": notes, "total": len(notes)}

    except Exception as e:
        logger.error(f"列出笔记失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/notes/{file_path:path}")
async def get_note(file_path: str):
    """获取笔记内容"""
    try:
        content = obsidian_tools.read_note(file_path)
        if content is None:
            raise HTTPException(status_code=404, detail="Note not found")

        metadata = obsidian_tools.get_note_metadata(file_path)

        return {
            "file_path": file_path,
            "content": content,
            "metadata": metadata
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取笔记失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/notes", status_code=201)
async def create_note(request: CreateNoteRequest):
    """创建笔记"""
    try:
        file_path = obsidian_tools.create_note(
            title=request.title,
            content=request.content,
            folder=request.folder,
            tags=request.tags
        )

        return {
            "status": "created",
            "file_path": file_path
        }

    except Exception as e:
        logger.error(f"创建笔记失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/v1/notes/{file_path:path}")
async def update_note(file_path: str, content: str = Body(..., media_type="text/plain")):
    """更新笔记内容"""
    try:
        success = obsidian_tools.update_note(file_path, content)
        if not success:
            raise HTTPException(status_code=404, detail="Note not found")

        return {"status": "updated", "file_path": file_path}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新笔记失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/tags")
async def list_tags():
    """列出所有标签"""
    try:
        tags = obsidian_tools.get_all_tags()
        return {"tags": tags, "total": len(tags)}

    except Exception as e:
        logger.error(f"列出标签失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    logger.info(f"启动 Obsidian 知识助手，端口: {port}")
    logger.info(f"Vault 路径: {os.getenv('OBSIDIAN_VAULT_PATH', '/vault')}")
    uvicorn.run("src.app:app", host="0.0.0.0", port=port, workers=2, log_level="info")
