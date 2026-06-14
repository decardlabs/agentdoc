"""
错误捕获与自我修复模块

当代码执行失败时，分析错误信息，调用 LLM 生成修复后的代码，
最多重试指定次数，实现"自我修复"能力。
"""

import logging
import traceback
from typing import Optional

from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)


class ErrorHandler:
    """
    错误处理器，负责分析执行错误并自动修复代码。

    修复策略：
    1. 解析错误类型（ImportError、NameError、SyntaxError 等）
    2. 将错误信息和原代码送给 LLM，生成修复版本
    3. 最多重试 max_retries 次

    Attributes:
        llm: 用于代码修复的语言模型
        max_retries: 最大重试次数
    """

    # 常见错误类型的修复提示（作为 LLM 提示的补充）
    ERROR_HINTS = {
        "ModuleNotFoundError": "缺少 Python 包，请在代码开头添加 pip install 命令（在沙箱中用 os.system 执行）",
        "ImportError": "导入错误，检查模块名是否正确，或是否需要先安装",
        "NameError": "使用了未定义的变量或函数，检查拼写和定义顺序",
        "SyntaxError": "Python 语法错误，检查括号、引号、缩进是否匹配",
        "TypeError": "数据类型错误，检查函数参数类型是否正确",
        "FileNotFoundError": "文件不存在，检查文件路径是否正确（沙箱路径以 /home/user/data/ 开头）",
        "KeyError": "访问了字典中不存在的键，检查列名或 key 是否正确",
        "IndexError": "索引越界，检查列表/数组访问是否超出范围",
        "ValueError": "值错误，检查数据格式和类型转换",
    }

    def __init__(self, llm: ChatOpenAI, max_retries: int = 3):
        """
        初始化错误处理器。

        Args:
            llm: 语言模型实例（用于生成修复代码）
            max_retries: 最大自动修复重试次数，默认 3
        """
        self.llm = llm
        self.max_retries = max_retries

    def analyze_error(self, error_message: str) -> dict:
        """
        分析错误信息，提取错误类型和关键线索。

        Args:
            error_message: 完整的错误堆栈信息

        Returns:
            分析结果字典，包含 error_type、hint、traceback_lines
        """
        error_type = "UnknownError"
        for known_type in self.ERROR_HINTS:
            if known_type in error_message:
                error_type = known_type
                break

        hint = self.ERROR_HINTS.get(error_type, "请分析错误信息并修复代码")

        # 提取错误堆栈的最后几行（最相关的部分）
        lines = error_message.strip().split("\n")
        traceback_lines = lines[-5:] if len(lines) > 5 else lines

        return {
            "error_type": error_type,
            "hint": hint,
            "traceback_lines": traceback_lines,
        }

    def fix_code(
        self,
        broken_code: str,
        error_message: str,
        user_request: str,
    ) -> str:
        """
        根据错误信息生成修复后的代码。

        Args:
            broken_code: 执行失败的原始代码
            error_message: 完整的错误堆栈
            user_request: 原始用户需求（用于上下文）

        Returns:
            修复后的代码字符串；若无法修复则返回原代码
        """
        analysis = self.analyze_error(error_message)

        logger.info(f"错误类型: {analysis['error_type']}，开始生成修复代码")

        prompt = f"""以下 Python 代码执行时出错，请根据错误信息修复代码。

## 原始用户需求
{user_request}

## 出错的代码
```python
{broken_code}
```

## 错误信息
错误类型：{analysis['error_type']}
修复提示：{analysis['hint']}

错误堆栈：
{error_message}

## 修复要求
1. 保持代码整体逻辑不变，只修复导致错误的部分
2. 如果是缺少依赖（ModuleNotFoundError），在代码开头添加：
   ```python
   import subprocess
   subprocess.run(["pip", "install", "包名"], check=True)
   ```
3. 如果是文件路径问题，确保使用 /home/user/data/ 前缀
4. 如果是数据列名问题，先 print(df.columns.tolist()) 查看可用列
5. 确保修复后的代码可以直接执行
6. 只输出修复后的完整代码，用 ```python ``` 包裹

修复后的代码："""

        try:
            response = self.llm.invoke(prompt)
            fixed_code = self._extract_code(response.content)

            # 检查修复是否有效（代码是否有变化）
            if fixed_code == broken_code:
                logger.warning("修复代码与原始代码相同，无法修复")
                return broken_code

            logger.info(f"修复代码生成成功，变更长度={abs(len(fixed_code) - len(broken_code))}")
            return fixed_code

        except Exception as e:
            logger.error(f"生成修复代码失败: {e}")
            return broken_code

    def should_retry(self, retry_count: int, error_message: str) -> bool:
        """
        判断是否应该继续重试。

        Args:
            retry_count: 当前已重试次数
            error_message: 错误信息

        Returns:
            是否应该继续重试
        """
        if retry_count >= self.max_retries:
            return False

        # 某些错误无法自动修复，直接放弃
        non_fixable = ["KeyboardInterrupt", "SystemExit"]
        for nf in non_fixable:
            if nf in error_message:
                return False

        return True

    def _extract_code(self, text: str) -> str:
        """从 LLM 输出中提取纯 Python 代码（与 CodeGenerator 中的逻辑相同）。"""
        import re
        text = text.strip()

        pattern = r"```(?:python)?\s*\n(.*?)\n```"
        matches = re.findall(pattern, text, re.DOTALL)
        if matches:
            return matches[0].strip()

        if text.startswith("```"):
            lines = text.split("\n")
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

        return text
