"""
结果可视化模块

负责从沙箱下载生成的图表，并在本地展示或保存。
支持 matplotlib 图表的渲染、Base64 编码（用于 API 返回）等功能。
"""

import os
import io
import base64
import logging
from typing import Optional

from PIL import Image
import matplotlib.pyplot as plt
import matplotlib.image as mpimg

logger = logging.getLogger(__name__)


class Visualizer:
    """
    结果可视化器，负责处理沙箱中生成的图表。

    Attributes:
        output_dir: 本地保存图表的目录
    """

    def __init__(self, output_dir: str = "./output"):
        """
        初始化可视化器。

        Args:
            output_dir: 本地图表保存目录，默认 ./output
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"可视化器初始化完成，输出目录={output_dir}")

    def save_plot_locally(
        self,
        plot_data: bytes,
        filename: str = "plot.png",
    ) -> str:
        """
        将图表二进制数据保存为本地文件。

        Args:
            plot_data: 图表文件的二进制数据
            filename: 保存的文件名

        Returns:
            保存后的本地文件路径
        """
        filepath = os.path.join(self.output_dir, filename)
        with open(filepath, "wb") as f:
            f.write(plot_data)
        logger.info(f"图表已保存到本地: {filepath}")
        return filepath

    def display_plot(self, plot_path: str) -> None:
        """
        在本地显示图表（使用 matplotlib 预览）。

        Args:
            plot_path: 图表文件路径
        """
        if not os.path.exists(plot_path):
            logger.error(f"图表文件不存在: {plot_path}")
            return

        img = mpimg.imread(plot_path)
        plt.figure(figsize=(10, 6))
        plt.imshow(img)
        plt.axis("off")
        plt.title(os.path.basename(plot_path))
        plt.show()

    def plot_to_base64(self, plot_path: str) -> str:
        """
        将图表文件编码为 Base64 字符串（用于 API 返回给前端）。

        Args:
            plot_path: 图表文件路径

        Returns:
            Base64 编码的字符串（不含 data:image/png;base64, 前缀）
        """
        if not os.path.exists(plot_path):
            logger.error(f"图表文件不存在: {plot_path}")
            return ""

        with open(plot_path, "rb") as f:
            plot_data = f.read()

        base64_str = base64.b64encode(plot_data).decode("utf-8")
        logger.debug(f"图表已编码为 Base64，长度={len(base64_str)}")
        return base64_str

    def generate_html_report(
        self,
        plot_path: str,
        result_summary: str,
        code: str,
        output_path: str = "report.html",
    ) -> str:
        """
        生成包含图表、结果摘要和代码的 HTML 报告。

        Args:
            plot_path: 图表文件路径
            result_summary: 结果摘要文本
            code: 执行的代码
            output_path: 输出的 HTML 文件路径

        Returns:
            HTML 报告的文件路径
        """
        base64_plot = self.plot_to_base64(plot_path)

        html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>代码执行报告</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 40px; background: #f5f5f5; }}
        .container {{ max-width: 900px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; border-bottom: 2px solid #4CAF50; padding-bottom: 10px; }}
        h2 {{ color: #555; margin-top: 30px; }}
        .plot {{ text-align: center; margin: 20px 0; }}
        .plot img {{ max-width: 100%; border-radius: 4px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        .result {{ background: #e8f5e9; padding: 15px; border-radius: 4px; margin: 15px 0; }}
        .code-block {{ background: #263238; color: #aed581; padding: 15px; border-radius: 4px; overflow-x: auto; font-family: 'Fira Code', monospace; }}
        .footer {{ margin-top: 40px; color: #999; font-size: 12px; text-align: center; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 代码执行报告</h1>

        <h2>结果摘要</h2>
        <div class="result">
            <p>{result_summary or "无摘要"}</p>
        </div>

        <h2>生成的图表</h2>
        <div class="plot">
            <img src="data:image/png;base64,{base64_plot}" alt="生成的图表" />
        </div>

        <h2>执行代码</h2>
        <div class="code-block">
            <pre>{self._escape_html(code)}</pre>
        </div>

        <div class="footer">
            <p>由 Code Execution Agent 自动生成</p>
        </div>
    </div>
</body>
</html>"""

        output_filepath = os.path.join(self.output_dir, output_path)
        with open(output_filepath, "w", encoding="utf-8") as f:
            f.write(html_content)

        logger.info(f"HTML 报告已生成: {output_filepath}")
        return output_filepath

    def create_plot_from_data(
        self,
        x_data,
        y_data,
        plot_type: str = "line",
        title: str = "图表",
        xlabel: str = "X",
        ylabel: str = "Y",
        filename: str = "generated_plot.png",
    ) -> str:
        """
        在本地直接用 matplotlib 生成图表（不依赖沙箱）。

        适用于 Agent 返回数据而非图表文件的场景。

        Args:
            x_data: X 轴数据（列表）
            y_data: Y 轴数据（列表）
            plot_type: 图表类型（"line", "bar", "scatter"）
            title: 图表标题
            xlabel: X 轴标签
            ylabel: Y 轴标签
            filename: 保存的文件名

        Returns:
            保存后的文件路径
        """
        plt.figure(figsize=(10, 6))

        if plot_type == "line":
            plt.plot(x_data, y_data, marker='o')
        elif plot_type == "bar":
            plt.bar(x_data, y_data)
        elif plot_type == "scatter":
            plt.scatter(x_data, y_data)
        else:
            plt.plot(x_data, y_data)

        plt.title(title, fontsize=14)
        plt.xlabel(xlabel, fontsize=12)
        plt.ylabel(ylabel, fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()

        filepath = os.path.join(self.output_dir, filename)
        plt.savefig(filepath, dpi=150)
        plt.close()

        logger.info(f"图表已生成: {filepath}")
        return filepath

    def _escape_html(self, text: str) -> str:
        """转义 HTML 特殊字符。"""
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
