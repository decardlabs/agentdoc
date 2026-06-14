"""
长期记忆模块

使用 Chroma 向量数据库存储对话摘要和历史信息，
支持语义检索，实现跨会话的记忆召回。

存储内容：
- 对话摘要（定期生成）
- 用户关键偏好信息
- 重要历史事件
"""

import logging
from typing import Optional

from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma

logger = logging.getLogger(__name__)


class LongTermMemory:
    """
    长期记忆管理器，基于 Chroma 向量数据库实现。

    使用 OpenAI Embeddings 将文本转换为向量，存储到 Chroma 集合中。
    支持按语义相似度检索历史记忆。

    Attributes:
        embeddings: 向量化模型（OpenAI Embeddings）
        vector_store: Chroma 向量库实例
        collection_name: Chroma 集合名称
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8000,
        collection_name: str = "conversation_memory",
        embedding_model: str = "text-embedding-3-small",
        persist_directory: Optional[str] = None,
    ):
        """
        初始化长期记忆管理器。

        Args:
            host: Chroma HTTP 服务主机地址（使用 HTTP 模式时）
            port: Chroma HTTP 服务端口
            collection_name: Chroma 集合名称
            embedding_model: 使用的 Embedding 模型名
            persist_directory: 本地持久化目录（为 None 时使用 HTTP 客户端）
        """
        import os
        api_key = os.getenv("OPENAI_API_KEY", "")
        base_url = os.getenv("OPENAI_BASE_URL", None)

        self.embeddings = OpenAIEmbeddings(
            model=embedding_model,
            api_key=api_key,
            base_url=base_url,
        )
        self.collection_name = collection_name

        if persist_directory:
            # 本地持久化模式（无需启动 Chroma 服务）
            self.vector_store = Chroma(
                collection_name=collection_name,
                embedding_function=self.embeddings,
                persist_directory=persist_directory,
            )
            self._using_http = False
        else:
            # HTTP 客户端模式（需要 Chroma 服务运行）
            try:
                self.vector_store = Chroma(
                    collection_name=collection_name,
                    embedding_function=self.embeddings,
                    host=host,
                    port=port,
                )
                self._using_http = True
            except Exception as e:
                logger.warning(f"Chroma HTTP 连接失败: {e}，切换为本地持久化模式")
                # 回退到本地模式
                local_dir = f"./chroma_db/{collection_name}"
                self.vector_store = Chroma(
                    collection_name=collection_name,
                    embedding_function=self.embeddings,
                    persist_directory=local_dir,
                )
                self._using_http = False

        logger.info(f"长期记忆初始化完成，集合={collection_name}，HTTP模式={self._using_http}")

    def store(
        self,
        user_id: str,
        session_id: str,
        content: str,
        metadata: Optional[dict] = None,
    ) -> None:
        """
        将内容存入长期记忆。

        Args:
            user_id: 用户 ID（用于隔离不同用户的数据）
            session_id: 会话 ID
            content: 要存储的文本内容（对话摘要或关键记忆）
            metadata: 额外元数据（如类型、时间戳等）
        """
        if not content.strip():
            logger.warning("存储内容为空，跳过")
            return

        base_metadata = {
            "user_id": user_id,
            "session_id": session_id,
        }
        if metadata:
            base_metadata.update(metadata)

        self.vector_store.add_texts(
            texts=[content],
            metadatas=[base_metadata],
        )
        logger.debug(f"已存入长期记忆: user_id={user_id}, content={content[:50]}...")

    def retrieve(
        self,
        user_id: str,
        query: str,
        top_k: int = 3,
    ) -> list[dict]:
        """
        根据用户查询检索相关长期记忆。

        使用向量相似度搜索，只返回属于该用户的记忆。

        Args:
            user_id: 用户 ID（用于过滤）
            query: 检索查询文本
            top_k: 最多返回的结果数

        Returns:
            记忆列表，每项包含 'content' 和 'metadata'
        """
        if not query.strip():
            return []

        # 使用相似度搜索，并附加过滤条件
        try:
            results = self.vector_store.similarity_search(
                query=query,
                k=top_k,
                filter={"user_id": user_id},
            )
        except Exception as e:
            logger.error(f"检索长期记忆失败: {e}")
            return []

        memories = []
        for doc in results:
            memories.append({
                "content": doc.page_content,
                "metadata": doc.metadata,
            })

        logger.debug(f"检索到 {len(memories)} 条长期记忆")
        return memories

    def delete_user_memory(self, user_id: str) -> None:
        """
        删除某用户的所有长期记忆。

        Args:
            user_id: 用户 ID
        """
        try:
            # Chroma 支持按 metadata 过滤删除
            self.vector_store.delete(where={"user_id": user_id})
            logger.info(f"已删除用户 {user_id} 的全部长期记忆")
        except Exception as e:
            logger.error(f"删除用户长期记忆失败: {e}")

    def get_all_for_user(self, user_id: str) -> list[dict]:
        """
        获取某用户的全部长期记忆（用于调试）。

        Args:
            user_id: 用户 ID

        Returns:
            该用户的全部记忆列表
        """
        try:
            # 通过 Chroma 的 where 过滤获取
            results = self.vector_store.similarity_search(
                query=" ",  # 空格作为通配查询
                k=100,
                filter={"user_id": user_id},
            )
            return [{"content": d.page_content, "metadata": d.metadata} for d in results]
        except Exception as e:
            logger.error(f"获取用户全部记忆失败: {e}")
            return []
