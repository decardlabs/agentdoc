"""
内容工具集
提供内容优化、SEO 分析、图片生成等工具
"""

import os
import logging
from typing import Dict, List, Any, Optional
import re
from datetime import datetime

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)


class ContentTools:
    """内容工具集"""

    def __init__(self):
        self.stop_words = set(["的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一", "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着", "没有", "看", "好", "自己", "这"])

    def extract_keywords(self, content: str, top_k: int = 10) -> List[str]:
        """
        提取关键词

        Args:
            content: 文本内容
            top_k: 返回 top-k 关键词

        Returns:
            关键词列表
        """
        logger.info(f"提取关键词: content_length={len(content)}")

        words = re.findall(r'\w+', content.lower())

        word_freq = {}
        for word in words:
            if len(word) < 2 or word in self.stop_words:
                continue
            word_freq[word] = word_freq.get(word, 0) + 1

        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)

        return [w[0] for w in sorted_words[:top_k]]

    def calculate_seo_score(self, content: str, keywords: List[str]) -> Dict[str, Any]:
        """
        计算 SEO 分数

        Args:
            content: 文本内容
            keywords: 目标关键词

        Returns:
            SEO 分析结果
        """
        logger.info(f"计算 SEO 分数: keywords={keywords}")

        score = 0
        suggestions = []

        content_lower = content.lower()
        word_count = len(content)

        for keyword in keywords:
            count = content_lower.count(keyword.lower())
            density = count / word_count * 100 if word_count > 0 else 0

            if density < 0.5:
                suggestions.append(f"关键词 '{keyword}' 密度过低（{density:.2f}%），建议增加")
            elif density > 3:
                suggestions.append(f"关键词 '{keyword}' 密度过高（{density:.2f}%），建议减少")

            if count > 0:
                score += 10

        headers = re.findall(r'#{1,6}\s+(.+)', content)
        if len(headers) < 3:
            suggestions.append("建议使用更多标题标签（H1-H6）来结构化内容")
        else:
            score += 10

        paragraphs = content.split('\n\n')
        avg_para_len = sum(len(p) for p in paragraphs) / len(paragraphs) if paragraphs else 0

        if avg_para_len > 200:
            suggestions.append("段落过长，建议拆分为更短的段落以提高可读性")
        else:
            score += 10

        if word_count < 300:
            suggestions.append("内容长度较短，建议扩充到 300 字以上")
        else:
            score += 10

        score = min(score, 100)

        return {
            "seo_score": score,
            "keyword_density": {k: content_lower.count(k.lower()) / word_count * 100 for k in keywords},
            "word_count": word_count,
            "headers_count": len(headers),
            "suggestions": suggestions
        }

    def generate_hashtags(self, content: str, platform: str = "xiaohongshu", count: int = 5) -> List[str]:
        """
        生成话题标签

        Args:
            content: 文本内容
            platform: 平台（影响标签风格）
            count: 生成数量

        Returns:
            标签列表
        """
        logger.info(f"生成标签: platform={platform}, count={count}")

        keywords = self.extract_keywords(content, top_k=count * 2)

        hashtags = []
        for kw in keywords[:count]:
            if platform == "xiaohongshu":
                hashtags.append(f"#{kw}#")
            elif platform == "weibo":
                hashtags.append(f"#{kw}#")
            else:
                hashtags.append(kw.replace(" ", ""))

        return hashtags

    def check_readability(self, content: str) -> Dict[str, Any]:
        """
        检查可读性

        Args:
            content: 文本内容

        Returns:
            可读性分析结果
        """
        logger.info("检查可读性")

        sentences = re.split(r'[。！？\.\!\?]+', content)
        words = content.split()

        avg_sentence_len = sum(len(s) for s in sentences if s) / len([s for s in sentences if s]) if sentences else 0
        avg_word_len = sum(len(w) for w in words) / len(words) if words else 0

        paragraphs = content.split('\n\n')
        avg_para_len = sum(len(p) for p in paragraphs) / len(paragraphs) if paragraphs else 0

        score = 100
        suggestions = []

        if avg_sentence_len > 50:
            score -= 15
            suggestions.append("平均句长过长，建议拆分长句")

        if avg_para_len > 300:
            score -= 15
            suggestions.append("段落过长，建议拆分")

        if content.count('\n\n') < 3:
            score -= 10
            suggestions.append("段落过少，建议增加段落分隔")

        if not re.search(r'[#*_`]', content):
            score -= 10
            suggestions.append("建议使用 Markdown 格式（加粗、列表等）增强可读性")

        score = max(score, 0)

        return {
            "readability_score": score,
            "avg_sentence_length": avg_sentence_len,
            "avg_paragraph_length": avg_para_len,
            "paragraph_count": len(paragraphs),
            "suggestions": suggestions
        }

    def optimize_title(self, title: str, platform: str = "wechat") -> List[str]:
        """
        优化标题

        Args:
            title: 原始标题
            platform: 平台

        Returns:
            优化后的标题列表
        """
        logger.info(f"优化标题: title={title}, platform={platform}")

        optimized = []

        if platform == "wechat":
            optimized.append(f"【深度】{title}")
            optimized.append(f"{title}（深度解析）")
            optimized.append(f"终于搞清楚了：{title}")
        elif platform == "xiaohongshu":
            optimized.append(f"✨ {title} 💯")
            optimized.append(f"亲身实测！{title}")
            optimized.append(f"后悔没早知道！{title}")
        elif platform == "weibo":
            optimized.append(f"{title}！")
            optimized.append(f"热议！{title}")
            optimized.append(f"{title}#{title}#")

        return optimized

    def generate_image_prompt(self, content: str, style: str = "photorealistic") -> str:
        """
        根据内容生成图片描述

        Args:
            content: 文本内容
            style: 图片风格

        Returns:
            图片描述
        """
        logger.info("生成图片描述")

        keywords = self.extract_keywords(content, top_k=5)

        style_prefix = {
            "photorealistic": "A photorealistic image of",
            "illustration": "A colorful illustration of",
            "minimalist": "A minimalist design of",
            "cartoon": "A cartoon style image of"
        }.get(style, "An image of")

        prompt = f"{style_prefix} {', '.join(keywords)}"

        return prompt[:500]


class ContentAnalyzer:
    """内容分析器"""

    def __init__(self):
        self.tools = ContentTools()

    def analyze(self, content: str, platform: str = "wechat") -> Dict[str, Any]:
        """
        全面分析内容

        Args:
            content: 文本内容
            platform: 平台

        Returns:
            分析结果
        """
        logger.info(f"分析内容: platform={platform}")

        keywords = self.tools.extract_keywords(content)
        seo_result = self.tools.calculate_seo_score(content, keywords[:5])
        readability = self.tools.check_readability(content)
        hashtags = self.tools.generate_hashtags(content, platform)

        return {
            "word_count": len(content),
            "keywords": keywords,
            "seo": seo_result,
            "readability": readability,
            "hashtags": hashtags,
            "optimized_titles": self.tools.optimize_title(
                content.split('\n')[0] if content else "标题",
                platform
            )
        }
