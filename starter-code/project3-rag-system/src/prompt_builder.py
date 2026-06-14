"""
Prompt 构建模块

本模块负责：
1. 定义 RAG 的 Prompt 模板
2. 构造最终的 Prompt
3. 处理引用和溯源

作者：智能体工程师培养计划
日期：2024
"""

from typing import List, Dict, Any, Optional
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# RAG System Prompt 模板
RAG_SYSTEM_PROMPT = """你是一个知识库问答助手。请严格基于以下 Context 回答用户的问题。

## 规则：
1. 只使用 Context 中明确出现的信息，不要编造
2. Context 中没有的内容，明确说"知识库中未找到相关信息"
3. 引用 Context 时，标注来源 (例如: [文档 1, 第 3 页])
4. 保持简洁，控制在 300 字以内
5. 使用中文回答
6. 回答时先给出结论，再引用原文支持

## Context：
{context}

## 注意：
- 请根据提供的 Context 回答，不要依赖外部知识
- 如果 Context 中有多个相关片段，综合它们回答
"""

# 带引用的 System Prompt（进阶版）
RAG_SYSTEM_PROMPT_WITH_CITATION = """你是一个知识库问答助手。请严格基于以下 Context 回答用户的问题。

## 规则：
1. 只使用 Context 中明确出现的信息，不要编造
2. Context 中没有的内容，明确说"知识库中未找到相关信息"
3. **必须引用来源**：每个信息都要标注 [来源 X]
4. 保持简洁，控制在 300 字以内
5. 使用中文回答
6. 回答时先给出结论，再引用原文支持

## Context：
{context}

## 引用格式示例：
- "根据文档，年假政策是..." [来源 1]
- "退款需要 3-5 个工作日" [来源 2, 第 3 页]

## 注意：
- 引用必须准确，不要错误归因
- 如果多个来源都支持同一个信息，列出所有来源
"""

# User Prompt 模板
RAG_USER_PROMPT = """用户问题：{question}

请根据上面的 Context 回答这个问题。"""


class RAGPromptBuilder:
    """
    RAG Prompt 构建器类
    
    负责构造 RAG 系统的 Prompt
    """
    
    def __init__(self, use_citation: bool = True):
        """
        初始化 Prompt 构建器
        
        Args:
            use_citation: 是否使用引用格式，默认 True
        """
        self.use_citation = use_citation
        logger.info(f"RAGPromptBuilder 初始化完成: use_citation={use_citation}")
    
    def build_context(self, documents: List[Dict[str, Any]]) -> str:
        """
        构建 Context 字符串
        
        Args:
            documents: 检索到的文档列表
            
        Returns:
            格式化的 Context 字符串
        """
        context_parts = []
        
        for i, doc in enumerate(documents, 1):
            # 提取信息
            text = doc.get("text", "")
            metadata = doc.get("metadata", {})
            
            # 构建来源信息
            source = metadata.get("file_name", "未知文档")
            page = metadata.get("page", "")
            
            source_info = f"[来源 {i}: {source}"
            if page:
                source_info += f", 第 {page} 页"
            source_info += "]"
            
            # 格式化
            context_part = f"{source_info}\n{text}\n"
            context_parts.append(context_part)
        
        # 合并
        context = "\n\n---\n\n".join(context_parts)
        
        return context
    
    def build_prompt(
        self,
        question: str,
        documents: List[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        """
        构建完整的 messages
        
        Args:
            question: 用户问题
            documents: 检索到的文档列表
            
        Returns:
            messages 列表
        """
        # 构建 Context
        context = self.build_context(documents)
        
        # 选择 System Prompt
        if self.use_citation:
            system_prompt = RAG_SYSTEM_PROMPT_WITH_CITATION.format(context=context)
        else:
            system_prompt = RAG_SYSTEM_PROMPT.format(context=context)
        
        # 构建 User Prompt
        user_prompt = RAG_USER_PROMPT.format(question=question)
        
        # 构造 messages
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        logger.info(f"构建 Prompt 完成: {len(documents)} 个文档")
        return messages
    
    def format_answer_with_citation(
        self,
        answer: str,
        documents: List[Dict[str, Any]]
    ) -> str:
        """
        为答案添加引用（后处理）
        
        Args:
            answer: 生成的答案
            documents: 检索到的文档列表
            
        Returns:
            带引用的答案
        """
        # 简化版：在答案末尾添加参考文档列表
        references = "\n\n## 参考文档：\n"
        for i, doc in enumerate(documents, 1):
            metadata = doc.get("metadata", {})
            source = metadata.get("file_name", "未知文档")
            page = metadata.get("page", "")
            
            ref = f"[{i}] {source}"
            if page:
                ref += f", 第 {page} 页"
            references += ref + "\n"
        
        return answer + references


if __name__ == "__main__":
    # 测试代码
    builder = RAGPromptBuilder(use_citation=True)
    
    # 模拟检索结果
    documents = [
        {
            "text": "公司年假政策：入职满 1 年可享受 5 天年假，满 3 年可享受 10 天年假。",
            "metadata": {
                "file_name": "员工手册.pdf",
                "page": 3
            }
        },
        {
            "text": "年假需要提前 3 天向 HR 申请，批准后可以休假。",
            "metadata": {
                "file_name": "员工手册.pdf",
                "page": 4
            }
        }
    ]
    
    # 测试构建 Prompt
    question = "年假怎么申请？"
    messages = builder.build_prompt(question, documents)
    
    print("构建的 messages:")
    for msg in messages:
        print(f"\n[{msg['role']}]:")
        print(msg['content'][:300] + "...")
    
    print("\n\nRAGPromptBuilder 模块测试完成！")
