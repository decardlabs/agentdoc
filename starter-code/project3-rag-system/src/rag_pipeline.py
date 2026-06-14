"""
RAG Pipeline 主流程

本模块是 RAG 系统的主入口，提供：
1. 文档索引（离线）
2. 问答检索（在线）
3. CLI 交互界面
4. 评估功能

作者：智能体工程师培养计划
日期：2024
"""

import os
import sys
import logging
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 导入自定义模块
from document_loader import DocumentLoader
from vector_store import VectorStore
from retriever import Retriever
from prompt_builder import RAGPromptBuilder


class RAGPipeline:
    """
    RAG Pipeline 类
    
    封装完整的 RAG 流程：索引 + 检索 + 生成
    """
    
    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",
        embedding_model: str = "text-embedding-3-small",
        persist_directory: str = "./chroma_db"
    ):
        """
        初始化 RAG Pipeline
        
        Args:
            openai_api_key: OpenAI API Key
            model: LLM 模型名称
            embedding_model: Embedding 模型名称
            persist_directory: 向量数据库持久化目录
        """
        # API Key
        self.api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("未找到 OPENAI_API_KEY")
        
        self.model = model
        self.embedding_model_name = embedding_model
        
        # 初始化组件
        self.document_loader = DocumentLoader()
        self.vector_store = VectorStore(persist_directory=persist_directory)
        
        # 初始化 Embedding 模型
        self.embedding_model = self._init_embedding_model()
        
        # 初始化检索器
        self.retriever = Retriever(self.vector_store, self.embedding_model)
        
        # 初始化 Prompt 构建器
        self.prompt_builder = RAGPromptBuilder(use_citation=True)
        
        # 初始化 OpenAI 客户端
        from openai import OpenAI
        self.client = OpenAI(api_key=self.api_key)
        
        logger.info(f"RAGPipeline 初始化完成: model={model}")
    
    def _init_embedding_model(self):
        """
        初始化 Embedding 模型
        
        Returns:
            Embedding 模型对象
        """
        # 使用 OpenAI Embedding
        try:
            from openai import OpenAI
            
            class OpenAIEmbedding:
                def __init__(self, api_key: str, model: str = "text-embedding-3-small"):
                    self.client = OpenAI(api_key=api_key)
                    self.model = model
                
                def embed_query(self, text: str) -> List[float]:
                    response = self.client.embeddings.create(
                        model=self.model,
                        input=text
                    )
                    return response.data[0].embedding
                
                def embed_documents(self, texts: List[str]) -> List[List[float]]:
                    response = self.client.embeddings.create(
                        model=self.model,
                        input=texts
                    )
                    return [item.embedding for item in response.data]
            
            return OpenAIEmbedding(self.api_key, self.embedding_model_name)
            
        except Exception as e:
            logger.error(f"Embedding 模型初始化失败: {str(e)}")
            raise
    
    def index_documents(self, data_dir: str, chunk_size: int = 512) -> None:
        """
        索引文档（离线阶段）
        
        Args:
            data_dir: 文档目录
            chunk_size: Chunk 大小（字符数）
        """
        try:
            logger.info(f"开始索引文档: {data_dir}")
            
            # 1. 加载文档
            documents = self.document_loader.load_directory(data_dir)
            logger.info(f"加载了 {len(documents)} 个文档片段")
            
            # 2. 切分文档（简化版：按字符切分）
            # 注意：实际应该使用 LangChain 的 TextSplitter
            chunks = self._split_documents(documents, chunk_size)
            logger.info(f"切分后得到 {len(chunks)} 个 Chunks")
            
            # 3. 生成向量
            texts = [chunk["text"] for chunk in chunks]
            embeddings = self.embedding_model.embed_documents(texts)
            logger.info(f"生成了 {len(embeddings)} 个向量")
            
            # 4. 存储到向量数据库
            self.vector_store.add_documents(chunks, embeddings)
            logger.info(f"索引完成！")
            
        except Exception as e:
            logger.error(f"索引失败: {str(e)}")
            raise
    
    def _split_documents(
        self,
        documents: List[Dict[str, Any]],
        chunk_size: int = 512
    ) -> List[Dict[str, Any]]:
        """
        切分文档（简化版）
        
        Args:
            documents: 文档列表
            chunk_size: Chunk 大小
            
        Returns:
            Chunks 列表
        """
        chunks = []
        
        for doc in documents:
            text = doc["text"]
            
            # 按字符数切分
            for i in range(0, len(text), chunk_size):
                chunk_text = text[i:i + chunk_size]
                
                # 复制元数据
                chunk_metadata = doc["metadata"].copy()
                chunk_metadata["chunk_id"] = len(chunks)
                
                chunks.append({
                    "text": chunk_text,
                    "metadata": chunk_metadata
                })
        
        return chunks
    
    def query(self, question: str, top_k: int = 5) -> str:
        """
        查询（在线阶段）
        
        Args:
            question: 用户问题
            top_k: 检索的文档数
            
        Returns:
            生成的答案
        """
        try:
            logger.info(f"开始查询: {question}")
            
            # 1. 检索相关文档
            documents = self.retriever.retrieve(question, top_k=top_k)
            logger.info(f"检索到 {len(documents)} 个相关文档")
            
            if not documents:
                return "知识库中未找到相关信息。"
            
            # 2. 构建 Prompt
            messages = self.prompt_builder.build_prompt(question, documents)
            
            # 3. 调用 LLM 生成答案
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )
            
            answer = response.choices[0].message.content
            
            # 4. 添加引用
            answer_with_citation = self.prompt_builder.format_answer_with_citation(
                answer, documents
            )
            
            logger.info(f"查询完成")
            return answer_with_citation
            
        except Exception as e:
            logger.error(f"查询失败: {str(e)}")
            return f"查询失败：{str(e)}"
    
    def evaluate(self, test_cases: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        评估 RAG 系统
        
        Args:
            test_cases: 测试用例列表，每个元素是 {"question": "...", "expected_source": "..."}
            
        Returns:
            评估结果
        """
        try:
            logger.info(f"开始评估: {len(test_cases)} 个测试用例")
            
            correct = 0
            results = []
            
            for case in test_cases:
                question = case["question"]
                expected_source = case.get("expected_source", "")
                
                # 查询
                answer = self.query(question)
                
                # 检查是否包含预期来源
                is_correct = expected_source in answer if expected_source else True
                
                if is_correct:
                    correct += 1
                
                results.append({
                    "question": question,
                    "answer": answer,
                    "expected_source": expected_source,
                    "is_correct": is_correct
                })
            
            # 计算指标
            accuracy = correct / len(test_cases) if test_cases else 0
            
            evaluation = {
                "total_cases": len(test_cases),
                "correct": correct,
                "accuracy": accuracy,
                "results": results
            }
            
            logger.info(f"评估完成: 准确率 {accuracy:.2%}")
            return evaluation
            
        except Exception as e:
            logger.error(f"评估失败: {str(e)}")
            raise


def main():
    """
    主函数：CLI 交互界面
    """
    print("=" * 60)
    print("📚 RAG 系统")
    print("=" * 60)
    print("\n命令：")
    print("  index <数据目录>  - 索引文档")
    print("  query <问题>      - 查询")
    print("  eval             - 评估")
    print("  quit             - 退出")
    print("=" * 60)
    
    try:
        # 初始化 Pipeline
        pipeline = RAGPipeline()
        
        # 交互循环
        while True:
            command = input("\n>>> ").strip()
            
            if not command:
                continue
            
            if command == "quit":
                print("\n👋 再见！")
                break
            
            if command.startswith("index "):
                # 索引文档
                data_dir = command[6:].strip()
                pipeline.index_documents(data_dir)
            
            elif command.startswith("query "):
                # 查询
                question = command[6:].strip()
                answer = pipeline.query(question)
                print(f"\n🤖 答案：\n{answer}")
            
            elif command == "eval":
                # 评估（需要准备测试数据）
                print("评估功能需要准备测试数据，暂未实现")
            
            else:
                print(f"未知命令: {command}")
        
    except Exception as e:
        print(f"\n❌ 错误: {str(e)}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
