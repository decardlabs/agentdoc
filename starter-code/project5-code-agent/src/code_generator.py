"""
代码生成器模块

调用 LLM 将用户的自然语言需求转化为可执行的 Python 代码。
支持上下文感知（前一轮错误可传入，用于修复代码）。
"""

import logging
import re
from typing import Optional

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)


class CodeGenerator:
    """
    代码生成器，负责将自然语言需求转化为 Python 代码。

    Attributes:
        llm: 用于代码生成的语言模型
        system_prompt: 系统提示词（指导代码风格和格式）
    """

    def __init__(self, llm: ChatOpenAI, system_prompt: Optional[str] = None):
        """
        初始化代码生成器。

        Args:
            llm: 语言模型实例
            system_prompt: 自定义系统提示词；为 None 时使用默认提示
        """
        self.llm = llm
        self.system_prompt = system_prompt or self._default_system_prompt()

    def generate(self, user_request: str) -> str:
        """
        根据用户需求生成 Python 代码。

        Args:
            user_request: 用户的自然语言需求描述

        Returns:
            生成的 Python 代码字符串（不含 markdown 标记）
        """
        logger.info(f"开始生成代码，需求: {user_request[:80]}...")

        prompt = f"""{self.system_prompt}

用户需求：
{user_request}

请生成完整的 Python 代码："""

        try:
            response = self.llm.invoke(prompt)
            code = self._extract_code(response.content)
            logger.info(f"代码生成成功，长度={len(code)}")
            return code
        except Exception as e:
            logger.error(f"代码生成失败: {e}")
            raise

    def generate_fix(self, broken_code: str, error_message: str, user_request: str) -> str:
        """
        根据错误信息和原始代码，生成修复后的代码。

        Args:
            broken_code: 执行失败的原始代码
            error_message: 完整的错误堆栈信息
            user_request: 原始用户需求（用于上下文）

        Returns:
            修复后的 Python 代码字符串
        """
        logger.info("开始生成修复代码...")

        prompt = f"""以下 Python 代码执行时出错，请根据错误信息修复代码。

原始用户需求：
{user_request}

出错的代码：
```python
{broken_code}
```

错误信息：
{error_message}

修复要求：
1. 保持代码整体逻辑不变，只修复导致错误的部分
2. 确保修复后的代码可以直接执行
3. 如果错误是由于缺少依赖，请在代码开头添加 pip install 的安装代码（在沙箱中执行）
4. 只输出修复后的完整代码，用 ```python ``` 包裹

修复后的代码："""

        try:
            response = self.llm.invoke(prompt)
            fixed_code = self._extract_code(response.content)
            logger.info("修复代码生成成功")
            return fixed_code
        except Exception as e:
            logger.error(f"修复代码生成失败: {e}")
            return broken_code  # 返回原代码，不重试

    def _extract_code(self, text: str) -> str:
        """
        从 LLM 输出中提取纯 Python 代码。

        LLM 可能用 ```python ``` 包裹代码，也可能直接输出代码。
        本方法尝试多种策略提取。

        Args:
            text: LLM 的原始输出

        Returns:
            提取后的纯代码字符串
        """
        text = text.strip()

        # 策略 1：提取 ```python ``` 或 ``` ``` 中的内容
        pattern = r"```(?:python)?\s*\n(.*?)\n```"
        matches = re.findall(pattern, text, re.DOTALL)
        if matches:
            return matches[0].strip()

        # 策略 2：如果输出以 ``` 开头，手动截取
        if text.startswith("```"):
            lines = text.split("\n")
            # 去掉第一行（```python）和最后一行（```）
            code_lines = []
            started = False
            for line in lines:
                if line.strip().startswith("```") and not started:
                    started = True
                    continue
                if line.strip() == "```" and started:
                    break
                if started:
                    code_lines.append(line)
            return "\n".join(code_lines).strip()

        # 策略 3：假设整个输出就是代码
        return text

    def _default_system_prompt(self) -> str:
        """返回默认的系统提示词。"""
        return """你是一个 Python 数据分析助手。
用户会用自然语言描述需求，你的任务是生成可执行的 Python 代码来解决用户问题。

代码要求：
1. 使用 pandas 处理表格数据，matplotlib/seaborn 绘制图表
2. 数据文件路径使用 /home/user/data/ 前缀（沙箱中的路径）
3. 图表保存为 /home/user/output/plot.png，并用 print("PLOT_SAVED:/home/user/output/plot.png") 标记
4. 最终用 print("RESULT: ...") 输出关键结果摘要
5. 不要使用 input() 等需要交互的函数
6. 代码要完整、可直接执行，包含必要的 import
7. 如果数据文件不存在，先生成模拟数据用于演示

只输出 Python 代码，用 ```python ``` 包裹。"""
