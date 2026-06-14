"""
Knowledge Agent - 知识检索 Agent 核心逻辑
使用 LLM 和向量检索实现知识问答
"""

import os
import logging
from typing import Dict, List, Any, Optional
from pydantic import BaseModel
import json

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)


class SearchResult(BaseModel):
    """搜索结果"""
    file_path: str
    title: str
    snippet: str
    score: float
    tags: List[str] = []


class AnswerResult(BaseModel):
    """回答结果"""
    answer: str
    sources: List[Dict]
    confidence: float


class KnowledgeAgent:
    """知识检索 Agent"""

    def __init__(self):
        self.llm_model = os.getenv("LLM_MODEL", "gpt-4o-mini")
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.vault_path = os.getenv("OBSIDIAN_VAULT_PATH", "/vault")
        self.embedding_model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

        from src.tools.obsidian_tools import ObsidianTools
        self.tools = ObsidianTools(vault_path=self.vault_path)

    async def search(self, query: str, top_k: int = 5, folder: Optional[str] = None) -> List[Dict]:
        """
        搜索笔记

        Args:
            query: 搜索查询
            top_k: 返回 top-k 结果
            folder: 限制搜索文件夹

        Returns:
            搜索结果列表
        """
        logger.info(f"搜索笔记: query={query}, top_k={top_k}")

        try:
            keyword_results = self._keyword_search(query, folder)

            if len(keyword_results) >= top_k:
                return keyword_results[:top_k]

            semantic_results = await self._semantic_search(query, folder)

            combined = self._merge_results(keyword_results, semantic_results)
            return combined[:top_k]

        except Exception as e:
            logger.error(f"搜索失败: {str(e)}")
            return []

    async def answer_question(
        self,
        question: str,
        context_files: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        基于知识库回答问题

        Args:
            question: 问题
            context_files: 指定上下文文件（可选）

        Returns:
            回答结果字典
        """
        logger.info(f"回答问题: {question[:50]}...")

        if not context_files:
            search_results = await self.search(question, top_k=5)
            context_files = [r["file_path"] for r in search_results]

        context = ""
        sources = []

        for file_path in context_files[:5]:
            content = self.tools.read_note(file_path)
            if not content:
                continue

            metadata = self.tools.get_note_metadata(file_path)

            context += f"\n\n## {metadata.get('title', file_path)}\n"
            context += content[:2000]

            sources.append({
                "file_path": file_path,
                "title": metadata.get("title", file_path),
                "tags": metadata.get("tags", [])
            })

        if not context:
            return {
                "answer": "抱歉，知识库中没有找到相关内容。请尝试其他问题或添加相关笔记。",
                "sources": [],
                "confidence": 0.0
            }

        prompt = f"""你是知识库助手。请根据以下上下文回答用户问题。

## 上下文
{context}

## 用户问题
{question}

## 要求
1. 基于上下文回答，不要编造信息
2. 如果上下文没有相关信息，请明确说明
3. 引用来源文件名
4. 回答要简洁、准确
5. 使用 Markdown 格式

请回答：
"""

        try:
            import openai
            openai.api_key = self.openai_api_key

            response = openai.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {"role": "system", "content": "你是知识库助手，基于提供的上下文回答问题。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2000
            )

            answer = response.choices[0].message.content

            confidence = self._calculate_confidence(answer, context)

            return {
                "answer": answer,
                "sources": sources,
                "confidence": confidence
            }

        except Exception as e:
            logger.error(f"LLM 回答失败: {str(e)}")
            return {
                "answer": "抱歉，系统暂时无法处理您的问题。请稍后再试。",
                "sources": sources,
                "confidence": 0.0
            }

    async def summarize_note(self, file_path: str) -> str:
        """
        总结笔记

        Args:
            file_path: 文件路径

        Returns:
            总结文本
        """
        logger.info(f"总结笔记: {file_path}")

        content = self.tools.read_note(file_path)
        if not content:
            return "笔记不存在或无法读取"

        prompt = f"""请总结以下笔记内容：

{content[:5000]}

要求：
1. 提取核心观点
2. 列出关键要点
3. 简洁明了
"""

        try:
            import openai
            openai.api_key = self.openai_api_key

            response = openai.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {"role": "system", "content": "你是笔记总结助手。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"总结失败: {str(e)}")
            return "总结失败，请稍后再试"

    def _keyword_search(self, query: str, folder: Optional[str] = None) -> List[Dict]:
        """关键词搜索"""
        results = self.tools.search_in_file(query, folder)

        formatted = []
        for r in results:
            content = self.tools.read_note(r["file_path"])
            if content:
                lines = content.split('\n')
                snippet_start = max(0, r["line_number"] - 2)
                snippet_end = min(len(lines), r["line_number"] + 3)
                snippet = '\n'.join(lines[snippet_start:snippet_end])

                formatted.append({
                    "file_path": r["file_path"],
                    "title": r["title"],
                    "snippet": snippet,
                    "score": 0.8,
                    "tags": self.tools.get_note_metadata(r["file_path"]).get("tags", [])
                })

        return formatted

    async def _semantic_search(self, query: str, folder: Optional[str] = None) -> List[Dict]:
        """语义搜索（使用向量嵌入）"""
        if not self.openai_api_key:
            logger.warning("未配置 OPENAI_API_KEY，跳过语义搜索")
            return []

        try:
            import openai

            response = openai.embeddings.create(
                model=self.embedding_model,
                input=query
            )

            query_embedding = response.data[0].embedding

            notes = self.tools.list_notes(folder)
            results = []

            for note in notes[:100]:
                content = self.tools.read_note(note["file_path"])
                if not content:
                    continue

                note_embedding_response = openai.embeddings.create(
                    model=self.embedding_model,
                    input=content[:8000]
                )

                note_embedding = note_embedding_response.data[0].embedding

                similarity = self._cosine_similarity(query_embedding, note_embedding)

                if similarity > 0.7:
                    results.append({
                        "file_path": note["file_path"],
                        "title": note["title"],
                        "snippet": content[:200],
                        "score": similarity,
                        "tags": self.tools.get_note_metadata(note["file_path"]).get("tags", [])
                    })

            results.sort(key=lambda x: x["score"], reverse=True)
            return results[:10]

        except Exception as e:
            logger.error(f"语义搜索失败: {str(e)}")
            return []

    def _merge_results(self, keyword_results: List[Dict], semantic_results: List[Dict]) -> List[Dict]:
        """合并搜索结果"""
        merged = []
        seen = set()

        for r in keyword_results:
            merged.append(r)
            seen.add(r["file_path"])

        for r in semantic_results:
            if r["file_path"] not in seen:
                merged.append(r)
                seen.add(r["file_path"])

        merged.sort(key=lambda x: x["score"], reverse=True)
        return merged

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度"""
        import math

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))

        if magnitude1 == 0 or magnitude2 == 0:
            return 0

        return dot_product / (magnitude1 * magnitude2)

    def _calculate_confidence(self, answer: str, context: str) -> float:
        """计算回答置信度"""
        if "无法" in answer or "没有" in answer or "不知道" in answer:
            return 0.3
        elif len(answer) < 50:
            return 0.5
        else:
            return 0.85
