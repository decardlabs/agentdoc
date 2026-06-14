"""
PDF 加载和切分模块

本模块负责：
1. 加载 PDF 文件并提取纯文本
2. 将长文本切分成合适的 Chunks
3. 支持多文件管理

作者：智能体工程师培养计划
日期：2024
"""

import pdfplumber
from langchain_text_splitters import RecursiveCharacterTextSplitter
from typing import List, Dict, Optional
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PDFLoader:
    """
    PDF 加载器类
    
    负责从 PDF 文件中提取文本，并进行智能切分
    """
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        初始化 PDF 加载器
        
        Args:
            chunk_size: 每个 Chunk 的字符数，默认 1000
            chunk_overlap: Chunk 之间的重叠字符数，默认 200
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # 初始化文本切分器
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", "。", "，", " ", ""],  # 中文友好的分隔符
            length_function=len,
        )
        
        logger.info(f"PDFLoader 初始化完成: chunk_size={chunk_size}, chunk_overlap={chunk_overlap}")
    
    def load_pdf(self, file_path: str) -> str:
        """
        加载单个 PDF 文件并提取纯文本
        
        Args:
            file_path: PDF 文件的路径
            
        Returns:
            提取的纯文本内容
            
        Raises:
            FileNotFoundError: 文件不存在
            Exception: PDF 解析失败
        """
        try:
            logger.info(f"开始加载 PDF: {file_path}")
            
            full_text = ""
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    page_text = page.extract_text()
                    if page_text:
                        full_text += f"\n--- 第 {page_num} 页 ---\n{page_text}\n"
                    
                    # 尝试提取表格
                    tables = page.extract_tables()
                    if tables:
                        for table in tables:
                            full_text += self._format_table(table)
            
            logger.info(f"PDF 加载完成: 共 {len(pdf.pages)} 页, {len(full_text)} 字符")
            return full_text
            
        except FileNotFoundError:
            logger.error(f"文件不存在: {file_path}")
            raise
        except Exception as e:
            logger.error(f"PDF 加载失败: {str(e)}")
            raise
    
    def _format_table(self, table: List[List[str]]) -> str:
        """
        格式化表格为文本
        
        Args:
            table: 表格数据
            
        Returns:
            格式化后的表格文本
        """
        if not table:
            return ""
        
        table_text = "\n[表格开始]\n"
        for row in table:
            table_text += " | ".join([str(cell) if cell else "" for cell in row]) + "\n"
        table_text += "[表格结束]\n\n"
        
        return table_text
    
    def split_text(self, text: str) -> List[str]:
        """
        将长文本切分成 Chunks
        
        Args:
            text: 待切分的文本
            
        Returns:
            Chunk 列表
        """
        try:
            chunks = self.text_splitter.split_text(text)
            logger.info(f"文本切分完成: {len(chunks)} 个 Chunks")
            return chunks
        except Exception as e:
            logger.error(f"文本切分失败: {str(e)}")
            raise
    
    def load_and_split(self, file_path: str) -> List[str]:
        """
        加载 PDF 并切分成 Chunks（一步到位）
        
        Args:
            file_path: PDF 文件路径
            
        Returns:
            Chunk 列表
        """
        text = self.load_pdf(file_path)
        chunks = self.split_text(text)
        return chunks
    
    def load_multiple_pdfs(self, file_paths: List[str]) -> Dict[str, List[str]]:
        """
        加载多个 PDF 文件
        
        Args:
            file_paths: PDF 文件路径列表
            
        Returns:
            字典: {文件名: Chunks}
        """
        results = {}
        
        for file_path in file_paths:
            try:
                chunks = self.load_and_split(file_path)
                file_name = file_path.split("/")[-1]
                results[file_name] = chunks
                logger.info(f"文件 {file_name} 处理完成: {len(chunks)} 个 Chunks")
            except Exception as e:
                logger.error(f"文件 {file_path} 处理失败: {str(e)}")
                continue
        
        return results


def count_tokens(text: str, model: str = "gpt-4o-mini") -> int:
    """
    计算文本的 Token 数量
    
    Args:
        text: 待计算的文本
        model: 模型名称
        
    Returns:
        Token 数量
    """
    try:
        import tiktoken
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except Exception as e:
        logger.warning(f"Token 计算失败: {str(e)}, 使用字符数估算")
        # 粗略估算：1 Token ≈ 4 字符（中文约 1.5 字符）
        return len(text) // 2


if __name__ == "__main__":
    # 测试代码
    loader = PDFLoader()
    
    # 测试 PDF 加载（需要实际的 PDF 文件）
    # chunks = loader.load_and_split("test.pdf")
    # print(f"生成 {len(chunks)} 个 Chunks")
    # print(f"第一个 Chunk: {chunks[0][:100]}...")
    
    print("PDFLoader 模块加载成功！")
