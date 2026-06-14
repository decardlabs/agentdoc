"""
文档加载模块

本模块负责：
1. 加载多种格式的文档（PDF、TXT、MD）
2. 提取文本和元数据
3. 统一文档格式

作者：智能体工程师培养计划
日期：2024
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DocumentLoader:
    """
    文档加载器类
    
    支持加载 PDF、TXT、Markdown 等格式的文档
    """
    
    def __init__(self):
        """
        初始化文档加载器
        """
        logger.info("DocumentLoader 初始化完成")
    
    def load_pdf(self, file_path: str) -> List[Dict[str, Any]]:
        """
        加载 PDF 文件
        
        Args:
            file_path: PDF 文件路径
            
        Returns:
            文档列表，每个元素是一个字典：{"text": "...", "metadata": {...}}
        """
        try:
            import pypdf
            
            documents = []
            with open(file_path, "rb") as file:
                pdf_reader = pypdf.PdfReader(file)
                
                for page_num, page in enumerate(pdf_reader.pages, 1):
                    text = page.extract_text()
                    
                    if text.strip():  # 只保留非空页面
                        documents.append({
                            "text": text,
                            "metadata": {
                                "source": file_path,
                                "file_name": Path(file_path).name,
                                "page": page_num,
                                "total_pages": len(pdf_reader.pages)
                            }
                        })
            
            logger.info(f"PDF 加载完成: {file_path}, 共 {len(documents)} 页")
            return documents
            
        except Exception as e:
            logger.error(f"PDF 加载失败: {file_path}, 错误: {str(e)}")
            raise
    
    def load_txt(self, file_path: str) -> List[Dict[str, Any]]:
        """
        加载 TXT 文件
        
        Args:
            file_path: TXT 文件路径
            
        Returns:
            文档列表
        """
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                text = file.read()
            
            documents = [{
                "text": text,
                "metadata": {
                    "source": file_path,
                    "file_name": Path(file_path).name,
                    "file_type": "txt"
                }
            }]
            
            logger.info(f"TXT 加载完成: {file_path}, 共 {len(text)} 字符")
            return documents
            
        except UnicodeDecodeError:
            # 尝试其他编码
            try:
                with open(file_path, "r", encoding="gbk") as file:
                    text = file.read()
                
                documents = [{
                    "text": text,
                    "metadata": {
                        "source": file_path,
                        "file_name": Path(file_path).name,
                        "file_type": "txt",
                        "encoding": "gbk"
                    }
                }]
                
                logger.info(f"TXT 加载完成 (GBK): {file_path}")
                return documents
                
            except Exception as e:
                logger.error(f"TXT 加载失败: {file_path}, 错误: {str(e)}")
                raise
        except Exception as e:
            logger.error(f"TXT 加载失败: {file_path}, 错误: {str(e)}")
            raise
    
    def load_markdown(self, file_path: str) -> List[Dict[str, Any]]:
        """
        加载 Markdown 文件
        
        Args:
            file_path: Markdown 文件路径
            
        Returns:
            文档列表
        """
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                text = file.read()
            
            # 可以尝试解析 Markdown 结构（可选）
            # 这里简单处理：按标题切分
            documents = [{
                "text": text,
                "metadata": {
                    "source": file_path,
                    "file_name": Path(file_path).name,
                    "file_type": "markdown"
                }
            }]
            
            logger.info(f"Markdown 加载完成: {file_path}, 共 {len(text)} 字符")
            return documents
            
        except Exception as e:
            logger.error(f"Markdown 加载失败: {file_path}, 错误: {str(e)}")
            raise
    
    def load_file(self, file_path: str) -> List[Dict[str, Any]]:
        """
        自动识别文件类型并加载
        
        Args:
            file_path: 文件路径
            
        Returns:
            文档列表
        """
        file_path = str(file_path)
        extension = Path(file_path).suffix.lower()
        
        if extension == ".pdf":
            return self.load_pdf(file_path)
        elif extension == ".txt":
            return self.load_txt(file_path)
        elif extension in [".md", ".markdown"]:
            return self.load_markdown(file_path)
        else:
            raise ValueError(f"不支持的文件格式: {extension}")
    
    def load_directory(self, dir_path: str) -> List[Dict[str, Any]]:
        """
        加载目录下的所有支持的文档
        
        Args:
            dir_path: 目录路径
            
        Returns:
            文档列表
        """
        documents = []
        dir_path = Path(dir_path)
        
        if not dir_path.exists():
            raise FileNotFoundError(f"目录不存在: {dir_path}")
        
        # 支持的文件扩展名
        supported_extensions = [".pdf", ".txt", ".md", ".markdown"]
        
        # 遍历目录
        for file_path in dir_path.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                try:
                    docs = self.load_file(str(file_path))
                    documents.extend(docs)
                    logger.info(f"已加载: {file_path}")
                except Exception as e:
                    logger.warning(f"跳过文件 {file_path}: {str(e)}")
                    continue
        
        logger.info(f"目录加载完成: {dir_path}, 共 {len(documents)} 个文档片段")
        return documents


if __name__ == "__main__":
    # 测试代码
    loader = DocumentLoader()
    
    # 测试加载单个文件
    # docs = loader.load_file("test.pdf")
    # print(f"加载了 {len(docs)} 个文档片段")
    
    # 测试加载目录
    # docs = loader.load_directory("data/")
    # print(f"加载了 {len(docs)} 个文档片段")
    
    print("DocumentLoader 模块加载成功！")
