"""
向量数据库模块

本模块负责：
1. 连接 Chroma 向量数据库
2. 存储文档向量
3. 相似度检索

作者：智能体工程师培养计划
日期：2024
"""

from typing import List, Dict, Any, Optional, Tuple
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VectorStore:
    """
    向量数据库类
    
    封装 Chroma 向量数据库的操作
    """
    
    def __init__(
        self,
        persist_directory: str = "./chroma_db",
        collection_name: str = "documents"
    ):
        """
        初始化向量数据库
        
        Args:
            persist_directory: 向量数据库持久化目录
            collection_name: 集合名称
        """
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        
        # 初始化 Chroma 客户端
        try:
            import chromadb
            from chromadb.config import Settings
            
            self.client = chromadb.PersistentClient(
                path=persist_directory,
                settings=Settings(allow_reset=True)
            )
            
            # 获取或创建集合
            self.collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"}  # 使用余弦相似度
            )
            
            logger.info(f"VectorStore 初始化完成: {persist_directory}, 集合: {collection_name}")
            logger.info(f"当前集合中有 {self.collection.count()} 个文档")
            
        except ImportError:
            logger.error("未安装 chromadb，请运行: pip install chromadb")
            raise
        except Exception as e:
            logger.error(f"VectorStore 初始化失败: {str(e)}")
            raise
    
    def add_documents(
        self,
        documents: List[Dict[str, Any]],
        embeddings: List[List[float]],
        ids: Optional[List[str]] = None
    ) -> None:
        """
        添加文档到向量数据库
        
        Args:
            documents: 文档列表，每个元素是 {"text": "...", "metadata": {...}}
            embeddings: 文档向量列表
            ids: 文档 ID 列表（可选，自动生成）
        """
        try:
            # 生成 ID（如果没有提供）
            if ids is None:
                ids = [f"doc_{i}" for i in range(len(documents))]
            
            # 准备数据
            texts = [doc["text"] for doc in documents]
            metadatas = [doc["metadata"] for doc in documents]
            
            # 添加到集合
            self.collection.add(
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )
            
            logger.info(f"已添加 {len(documents)} 个文档到向量数据库")
            
        except Exception as e:
            logger.error(f"添加文档失败: {str(e)}")
            raise
    
    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        向量检索
        
        Args:
            query_embedding: 查询向量
            top_k: 返回最相似的 K 个结果
            filter: 过滤条件（可选）
            
        Returns:
            检索结果列表，每个元素是 (文档, 相似度分数)
        """
        try:
            # 执行检索
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=filter
            )
            
            # 解析结果
            documents = []
            for i in range(len(results["ids"][0])):
                doc = {
                    "id": results["ids"][0][i],
                    "text": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i]
                }
                documents.append((doc, results["distances"][0][i]))
            
            logger.info(f"检索完成: 找到 {len(documents)} 个结果")
            return documents
            
        except Exception as e:
            logger.error(f"检索失败: {str(e)}")
            raise
    
    def delete_collection(self) -> None:
        """
        删除集合（慎用）
        """
        try:
            self.client.delete_collection(self.collection_name)
            logger.info(f"已删除集合: {self.collection_name}")
        except Exception as e:
            logger.error(f"删除集合失败: {str(e)}")
            raise
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """
        获取集合统计信息
        
        Returns:
            统计信息字典
        """
        try:
            count = self.collection.count()
            
            stats = {
                "collection_name": self.collection_name,
                "document_count": count,
                "persist_directory": self.persist_directory
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"获取统计信息失败: {str(e)}")
            raise
    
    def reset(self) -> None:
        """
        重置向量数据库（删除所有数据）
        """
        try:
            self.client.reset()
            logger.info("向量数据库已重置")
        except Exception as e:
            logger.error(f"重置失败: {str(e)}")
            raise


if __name__ == "__main__":
    # 测试代码
    try:
        vector_store = VectorStore()
        
        # 测试统计信息
        stats = vector_store.get_collection_stats()
        print(f"集合统计: {stats}")
        
        print("VectorStore 模块测试完成！")
        
    except Exception as e:
        print(f"测试失败: {str(e)}")
