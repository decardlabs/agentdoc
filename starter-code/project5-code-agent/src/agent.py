"""
代码执行 Agent 主模块

使用 E2B Sandbox 作为安全的代码执行环境，结合 LLM 代码生成能力，
实现"自然语言 → Python 代码 → 执行 → 结果展示"的完整流程。

核心流程：
1. 用户用自然语言描述需求
2. LLM 生成 Python 代码
3. 代码在 E2B 沙箱中执行
4. 若执行出错，自动修复（最多 3 次重试）
5. 返回执行结果，支持图表可视化
"""

import os
import io
import traceback
import logging
from typing import Optional

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from src.code_generator import CodeGenerator
from src.sandbox import E2BSandboxManager
from src.executor import CodeExecutor
from src.error_handler import ErrorHandler
from src.visualizer import Visualizer

logger = logging.getLogger(__name__)


class CodeExecutionAgent:
    """
    代码执行 Agent，协调各模块完成代码生成与执行。

    Attributes:
        llm: 语言模型（用于代码生成和错误修复）
        code_generator: 代码生成器
        sandbox_manager: E2B 沙箱管理器
        executor: 代码执行器
        error_handler: 错误处理与自动修复
        visualizer: 结果可视化器
        max_retries: 最大自动修复重试次数
    """

    SYSTEM_PROMPT = """你是一个 Python 数据分析助手。
用户会用自然语言描述需求，你的任务是生成可执行的 Python 代码来解决用户问题。

代码要求：
1. 使用 pandas 处理表格数据，matplotlib/seaborn 绘制图表
2. 数据文件路径使用 /home/user/data/ 前缀（沙箱中的路径）
3. 图表保存为 /home/user/output/plot.png，并用 print("PLOT_SAVED:/home/user/output/plot.png") 标记
4. 最终用 print("RESULT: ...") 输出关键结果摘要
5. 不要使用 input() 等需要交互的函数
6. 代码要完整、可直接执行，包含必要的 import

只输出 Python 代码，用 ```python ``` 包裹。"""

    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        e2b_api_key: Optional[str] = None,
        model_name: str = "gpt-4o-mini",
        max_retries: int = 3,
    ):
        """
        初始化代码执行 Agent。

        Args:
            openai_api_key: OpenAI API 密钥；为 None 时从环境变量读取
            e2b_api_key: E2B API 密钥；为 None 时从环境变量读取
            model_name: 使用的 LLM 模型名
            max_retries: 最大自动修复重试次数
        """
        api_key = openai_api_key or os.getenv("OPENAI_API_KEY", "")
        self.e2b_api_key = e2b_api_key or os.getenv("E2B_API_KEY", "")

        if not api_key:
            raise ValueError("OPENAI_API_KEY 未设置，请在 .env 中配置")
        if not self.e2b_api_key:
            raise ValueError("E2B_API_KEY 未设置，请在 .env 中配置")

        # 初始化 LLM
        self.llm = ChatOpenAI(
            model=model_name,
            api_key=api_key,
            base_url=os.getenv("OPENAI_BASE_URL", None),
            temperature=0.2,
        )

        # 初始化各模块
        self.code_generator = CodeGenerator(llm=self.llm, system_prompt=self.SYSTEM_PROMPT)
        self.sandbox_manager = E2BSandboxManager(api_key=self.e2b_api_key)
        self.executor = CodeExecutor()
        self.error_handler = ErrorHandler(llm=self.llm, max_retries=max_retries)
        self.visualizer = Visualizer()
        self.max_retries = max_retries

        logger.info(f"CodeExecutionAgent 初始化完成，模型={model_name}，最大重试={max_retries}")

    def run(self, user_request: str, data_files: Optional[list[str]] = None) -> dict:
        """
        执行完整的"需求 → 代码 → 执行 → 结果"流程。

        Args:
            user_request: 用户的自然语言需求描述
            data_files: 需要上传到沙箱的数据文件路径列表（如 CSV 文件）

        Returns:
            结果字典，包含：
            - success: 是否成功
            - code: 最终执行的代码
            - stdout: 标准输出
            - plot_path: 生成的图表路径（若有）
            - error: 错误信息（若失败）
            - retry_count: 重试次数
        """
        logger.info(f"开始处理用户需求: {user_request[:100]}...")

        # 第 1 步：生成代码
        code = self.code_generator.generate(user_request)
        logger.info(f"代码生成完成，长度={len(code)} 字符")

        # 第 2 步：上传数据文件到沙箱（若有）
        if data_files:
            self.sandbox_manager.upload_files(data_files)

        # 第 3 步：执行代码，失败时自动修复
        retry_count = 0
        execution_result = None
        last_error = None

        while retry_count <= self.max_retries:
            try:
                execution_result = self.executor.execute(
                    sandbox_manager=self.sandbox_manager,
                    code=code,
                )
                # 执行成功
                logger.info("代码执行成功")
                break

            except Exception as e:
                last_error = traceback.format_exc()
                logger.warning(f"代码执行失败 (重试 {retry_count + 1}/{self.max_retries}): {e}")

                if retry_count >= self.max_retries:
                    logger.error("达到最大重试次数，放弃修复")
                    break

                # 尝试自动修复代码
                fixed_code = self.error_handler.fix_code(
                    broken_code=code,
                    error_message=last_error,
                    user_request=user_request,
                )

                if fixed_code == code:
                    # 修复代码与原有代码相同，说明无法修复
                    logger.warning("修复代码无变化，停止重试")
                    break

                code = fixed_code
                retry_count += 1

        # 第 4 步：处理结果
        result = self._process_result(
            code=code,
            execution_result=execution_result,
            error=last_error,
            retry_count=retry_count,
        )

        return result

    def _process_result(
        self,
        code: str,
        execution_result: Optional[dict],
        error: Optional[str],
        retry_count: int,
    ) -> dict:
        """
        处理执行结果，提取输出、图表路径等信息。

        Returns:
            标准化结果字典
        """
        if error and not execution_result:
            return {
                "success": False,
                "code": code,
                "stdout": "",
                "stderr": error,
                "plot_path": None,
                "error": error,
                "retry_count": retry_count,
            }

        stdout = execution_result.get("stdout", "") if execution_result else ""
        stderr = execution_result.get("stderr", "") if execution_result else ""

        # 检查是否有图表生成
        plot_path = None
        for line in stdout.split("\n"):
            if line.startswith("PLOT_SAVED:"):
                plot_path = line.replace("PLOT_SAVED:", "").strip()
                break

        # 提取 RESULT 标记的内容
        result_summary = ""
        for line in stdout.split("\n"):
            if line.startswith("RESULT:"):
                result_summary = line.replace("RESULT:", "").strip()
                break

        success = execution_result is not None and not stderr.strip()

        return {
            "success": success,
            "code": code,
            "stdout": stdout,
            "stderr": stderr,
            "plot_path": plot_path,
            "result_summary": result_summary,
            "error": stderr if not success else None,
            "retry_count": retry_count,
        }

    def close(self):
        """释放沙箱资源。"""
        self.sandbox_manager.close()
        logger.info("沙箱资源已释放")


def main():
    """命令行交互式入口。"""
    import sys

    # 检查依赖
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ 请先设置环境变量 OPENAI_API_KEY")
        sys.exit(1)
    if not os.getenv("E2B_API_KEY"):
        print("❌ 请先设置环境变量 E2B_API_KEY（在 https://e2b.dev 免费注册获取）")
        print("   免费版每月有 100 小时沙箱使用时长")
        sys.exit(1)

    agent = CodeExecutionAgent()

    print("🤖 代码执行 Agent 已启动！")
    print("输入自然语言描述你的数据分析需求，输入 'exit' 退出")
    print("提示：你可以指定数据文件路径，如 '分析 data/sales.csv 中的销售趋势'\n")

    try:
        while True:
            user_input = input("你: ").strip()
            if user_input.lower() == "exit":
                print("👋 再见！")
                break
            if not user_input:
                continue

            # 执行
            result = agent.run(user_input)

            print("\n" + "=" * 50)
            if result["success"]:
                print("✅ 执行成功")
                if result["result_summary"]:
                    print(f"📊 结果摘要: {result['result_summary']}")
                print(f"📝 输出:\n{result['stdout']}")
                if result["plot_path"]:
                    print(f"📈 图表已生成: {result['plot_path']}")
            else:
                print("❌ 执行失败")
                print(f"错误信息:\n{result['error']}")
            if result["retry_count"] > 0:
                print(f"🔧 自动修复次数: {result['retry_count']}")
            print("=" * 50 + "\n")

    finally:
        agent.close()


if __name__ == "__main__":
    main()
