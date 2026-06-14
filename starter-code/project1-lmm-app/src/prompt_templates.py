"""
Prompt 模板模块

本模块负责：
1. 定义 System Prompt 和 User Prompt 模板
2. 构造最终的 Prompt
3. 支持 Few-shot 示例
4. 防幻觉规则

作者：智能体工程师培养计划
日期：2024
"""

from typing import List, Dict, Optional
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# System Prompt 模板
SYSTEM_PROMPT_TEMPLATE = """你是一个专业的文档问答助手。请严格基于以下文档内容回答问题。

## 规则：
1. 只使用文档中明确出现的信息，不要编造
2. 文档里没有的内容，明确说"文档未提及"
3. 引用具体信息时，标注所在的段落或页码
4. 保持简洁，控制在 300 字以内
5. 使用中文回答

## 文档内容：
{doc_content}

## 额外说明：
- 如果文档内容过长，我会提供最相关的部分
- 请基于提供的文档片段回答，不要依赖外部知识
"""

# 挑战版：带 Few-shot 的 System Prompt
SYSTEM_PROMPT_WITH_FEWSHOT = """你是一个专业的文档问答助手。请严格基于以下文档内容回答问题。

## 规则：
1. 只使用文档中明确出现的信息，不要编造
2. 文档里没有的内容，明确说"文档未提及"
3. 引用具体信息时，标注所在的段落或页码（例如：[第3页]、[章节2.1]）
4. 保持简洁，控制在 300 字以内
5. 使用中文回答
6. 回答时先给出结论，再引用原文支持

## 示例：

**示例 1：**
用户问："公司的年假政策是什么？"
文档内容："员工入职满一年可享受 5 天年假，满 3 年可享受 10 天年假。"
回答："根据文档，公司年假政策如下：
- 入职满 1 年：5 天年假
- 入职满 3 年：10 天年假
[文档第 1 段]"

**示例 2：**
用户问："退款需要多长时间？"
文档内容："退款将在 3-5 个工作日内原路返回。"
回答："根据文档，退款需要 3-5 个工作日原路返回。[文档第 1 段]"

**示例 3：**
用户问："产品有哪些颜色？"
文档内容："产品可选颜色：黑色、白色、蓝色。"
回答："根据文档，产品有以下颜色可选：黑色、白色、蓝色。[文档第 1 段]"

## 文档内容：
{doc_content}
"""

# User Prompt 模板
USER_PROMPT_TEMPLATE = "{question}"

# 对比两个文档的 Prompt 模板（挑战版）
COMPARE_PROMPT_TEMPLATE = """你是一个文档对比分析助手。请对比以下两个文档的内容，回答用户的问题。

## 规则：
1. 分别指出两个文档中的相关信息
2. 对比差异，用表格或列表形式展示
3. 如果某个文档没有相关信息，明确说明
4. 引用时标注来源文档

## 文档 1：{doc1_name}
{doc1_content}

## 文档 2：{doc2_name}
{doc2_content}

## 用户问题：
{question}
"""


class PromptBuilder:
    """
    Prompt 构建器类
    
    负责构造各种类型的 Prompt
    """
    
    def __init__(self, use_fewshot: bool = False):
        """
        初始化 Prompt 构建器
        
        Args:
            use_fewshot: 是否使用 Few-shot 示例，默认 False
        """
        self.use_fewshot = use_fewshot
        logger.info(f"PromptBuilder 初始化完成: use_fewshot={use_fewshot}")
    
    def build_system_prompt(self, doc_content: str) -> str:
        """
        构建 System Prompt
        
        Args:
            doc_content: 文档内容
            
        Returns:
            完整的 System Prompt
        """
        if self.use_fewshot:
            return SYSTEM_PROMPT_WITH_FEWSHOT.format(doc_content=doc_content)
        else:
            return SYSTEM_PROMPT_TEMPLATE.format(doc_content=doc_content)
    
    def build_user_prompt(self, question: str) -> str:
        """
        构建 User Prompt
        
        Args:
            question: 用户问题
            
        Returns:
            User Prompt
        """
        return USER_PROMPT_TEMPLATE.format(question=question)
    
    def build_messages(
        self,
        doc_content: str,
        question: str,
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> List[Dict[str, str]]:
        """
        构建完整的 messages 列表（用于 OpenAI API）
        
        Args:
            doc_content: 文档内容
            question: 用户问题
            chat_history: 聊天历史（可选）
            
        Returns:
            messages 列表
        """
        messages = []
        
        # 添加 System Prompt
        system_prompt = self.build_system_prompt(doc_content)
        messages.append({"role": "system", "content": system_prompt})
        
        # 添加聊天历史（如果有）
        if chat_history:
            # 只保留最近 5 轮对话（控制 Token 成本）
            recent_history = chat_history[-5:] if len(chat_history) > 5 else chat_history
            messages.extend(recent_history)
        
        # 添加当前问题
        user_prompt = self.build_user_prompt(question)
        messages.append({"role": "user", "content": user_prompt})
        
        logger.info(f"构建 messages 完成: {len(messages)} 条消息")
        return messages
    
    def build_compare_messages(
        self,
        doc1_name: str,
        doc1_content: str,
        doc2_name: str,
        doc2_content: str,
        question: str
    ) -> List[Dict[str, str]]:
        """
        构建对比两个文档的 messages（挑战版功能）
        
        Args:
            doc1_name: 文档 1 名称
            doc1_content: 文档 1 内容
            doc2_name: 文档 2 名称
            doc2_content: 文档 2 内容
            question: 用户问题
            
        Returns:
            messages 列表
        """
        messages = []
        
        # 构建对比 Prompt
        compare_prompt = COMPARE_PROMPT_TEMPLATE.format(
            doc1_name=doc1_name,
            doc1_content=doc1_content,
            doc2_name=doc2_name,
            doc2_content=doc2_content,
            question=question
        )
        
        messages.append({"role": "system", "content": "你是一个文档对比分析助手。"})
        messages.append({"role": "user", "content": compare_prompt})
        
        logger.info(f"构建对比 messages 完成")
        return messages
    
    def truncate_doc_content(self, doc_content: str, max_chars: int = 50000) -> str:
        """
        截断文档内容（防止 Prompt 过长）
        
        Args:
            doc_content: 文档内容
            max_chars: 最大字符数，默认 50000
            
        Returns:
            截断后的文档内容
        """
        if len(doc_content) <= max_chars:
            return doc_content
        
        # 截断并提示
        truncated = doc_content[:max_chars]
        truncated += f"\n\n[文档过长，已截断。原文共 {len(doc_content)} 字符，仅显示前 {max_chars} 字符]"
        
        logger.warning(f"文档内容已截断: {len(doc_content)} -> {max_chars} 字符")
        return truncated


if __name__ == "__main__":
    # 测试代码
    builder = PromptBuilder(use_fewshot=True)
    
    # 测试构建 messages
    doc_content = "这是一篇测试文档。公司年假政策：入职满 1 年 5 天，满 3 年 10 天。"
    question = "年假怎么算？"
    
    messages = builder.build_messages(doc_content, question)
    
    print("构建的 messages:")
    for msg in messages:
        print(f"\n[{msg['role']}]:")
        print(msg['content'][:200] + "..." if len(msg['content']) > 200 else msg['content'])
    
    print("\n\nPromptBuilder 模块测试完成！")
