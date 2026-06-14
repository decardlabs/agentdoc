"""
检索器模块

本模块负责：
1. 向量检索（基于 Chroma）
2. Rerank（重排序）
3. 混合检索（可选）

作者：智能体工程师培养计划
日期：2024
"""

from typing import List, Dict, Any, Tuple, Optional
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Retriever:
    """
    检索器类
    
    封装向量检索和 Rerank 功能
    """
    
    def __init__(
        self,
        vector_store,
        embedding_model,
        rerank_model: Optional[str] = None
    ):
        """
        初始化检索器
        
        Args:
            vector_store: 向量数据库对象
            embedding_model: Embedding 模型对象
            rerank_model: Rerank 模型名称（可选）
        """
        self.vector_store = vector_store
        self.embedding_model = embedding_model
        self.rerank_model = None
        
        # 初始化 Rerank 模型（如果提供）
        if rerank_model:
            try:
                from sentence_transformers import CrossEncoder
                self.rerank_model = CrossEncoder(rerank_model)
                logger.info(f"Rerank 模型加载成功: {rerank_model}")
            except Exception as e:
                logger.warning(f"Rerank 模型加载失败: {str(e)}")
        
        logger.info("Retriever 初始化完成")
    
    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        rerank_top_n: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        检索相关文档
        
        Args:
            query: 查询文本
            top_k: 检索返回的文档数
            rerank_top_n: Rerank 后保留的文档数（可选）
            
        Returns:
            相关文档列表
        """
        try:
            # 1. 生成查询向量
            query_embedding = self.embedding_model.embed_query(query)
            
            # 2. 向量检索
            results = self.vector_store.search(query_embedding, top_k=top_k)
            
            logger.info(f"向量检索完成: {len(results)} 个结果")
            
            # 3. Rerank（如果启用）
            if self.rerank_model and rerank_top_n:
                results = self._rerank(query, results, rerank_top_n)
                logger.info(f"Rerank 完成: 保留 {rerank_top_n} 个结果")
            
            # 4. 格式化结果
            documents = [result[0] for result in results]
            
            return documents
            
        except Exception as e:
            logger.error(f"检索失败: {str(e)}")
            raise
    
    def _rerank(
        self,
        query: str,
        results: List[Tuple[Dict[str, Any], float]],
        top_n: int
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        Rerank（重排序）
        
        Args:
            query: 查询文本
            results: 检索结果
            top_n: 保留的文档数
            
        Returns:
            重排序后的结果
        """
        try:
            # 准备输入
            pairs = [[query, doc[0]["text"]] for doc in results]
            
            # 计算相关性分数
            rerank_scores = self.rerank_model.predict(pairs)
            
            # 重新排序
            reranked_results = []
            for i, score in enumerate(rerank_scores):
                reranked_results.append((results[i][0], float(score)))
            
            reranked_results.sort(key=lambda x: x[1], reverse=True)
            
            # 保留 top_n
            return reranked_results[:top_n]
            
        except Exception as e:
            logger.error(f"Rerank 失败: {str(e)}")
            return results  # 失败时返回原始结果
    
    def hybrid_retrieve(
        self,
        query: str,
        top_k: int = 5,
        weight: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        混合检索（向量检索 + 关键词检索）
        
        Args:
            query: 查询文本
            top_k: 返回的文档数
            weight: 向量检索的权重（0-1）
            
        Returns:
            相关文档列表
        """
        # 注意：这是一个简化版本，完整实现需要集成 BM25 等关键词检索
        logger.warning("混合检索功能尚未完全实现，使用向量检索替代")
        return self.retrieve(query, top_k=top_k)


if __name__ == "__main__":
    # 测试代码
    print("Retriever 模块加载成功！")
    print("注意：需要配合实际的向量数据库和 Embedding 模型使用")
