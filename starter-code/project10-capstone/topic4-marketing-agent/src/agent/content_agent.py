"""
Content Agent - 内容生成 Agent 核心逻辑
使用 LLM 生成各类营销内容
"""

import os
import logging
from typing import Dict, List, Any, Optional
from pydantic import BaseModel
import json

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)


class ContentResult(BaseModel):
    """内容生成结果"""
    content: str
    title: Optional[str] = None
    hashtags: Optional[List[str]] = None
    seo_keywords: Optional[List[str]] = None
    metadata: Optional[Dict] = None


class ContentAgent:
    """内容生成 Agent"""

    def __init__(self):
        self.llm_model = os.getenv("LLM_MODEL", "gpt-4o-mini")
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.templates = self._load_templates()

    async def generate(
        self,
        topic: str,
        content_type: str = "wechat",
        tone: str = "professional",
        length: int = 800,
        keywords: Optional[List[str]] = None,
        target_audience: Optional[str] = None,
        brand_voice: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        生成营销内容

        Args:
            topic: 主题
            content_type: 内容类型 (wechat, xiaohongshu, weibo, email, blog)
            tone: 语气 (professional, casual, funny, inspirational)
            length: 长度（字数）
            keywords: 关键词列表
            target_audience: 目标受众
            brand_voice: 品牌声音

        Returns:
            生成结果字典
        """
        logger.info(f"生成内容: topic={topic}, type={content_type}")

        template = self._get_template(content_type)

        prompt = self._build_prompt(
            topic=topic,
            content_type=content_type,
            tone=tone,
            length=length,
            keywords=keywords,
            target_audience=target_audience,
            brand_voice=brand_voice,
            template=template
        )

        try:
            import openai
            openai.api_key = self.openai_api_key

            response = openai.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {"role": "system", "content": "你是专业的营销内容创作专家。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )

            generated = response.choices[0].message.content

            result = self._parse_generated(generated, content_type)

            return result

        except Exception as e:
            logger.error(f"LLM 生成失败: {str(e)}")
            return {
                "content": f"生成失败: {str(e)}",
                "title": None,
                "hashtags": [],
                "seo_keywords": []
            }

    async def optimize(self, content: str, platform: str = "wechat") -> Dict[str, Any]:
        """
        优化内容

        Args:
            content: 原始内容
            platform: 平台

        Returns:
            优化结果
        """
        logger.info(f"优化内容: platform={platform}")

        prompt = f"""请优化以下营销内容，使其更适合 {platform} 平台。

## 原始内容
{content}

## 优化要求
1. 提升可读性（段落、排版）
2. 优化 SEO（关键词布局）
3. 增强吸引力（标题、开头）
4. 符合平台风格
5. 给出优化建议

请以 JSON 格式输出：
```json
{{
  "optimized": "优化后的内容",
  "suggestions": ["建议1", "建议2"],
  "seo_score": 85
}}
```

只输出 JSON，不要有其他内容。
"""

        try:
            import openai
            openai.api_key = self.openai_api_key

            response = openai.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {"role": "system", "content": "你是内容优化专家。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2000,
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)

            return {
                "optimized": result.get("optimized", content),
                "suggestions": result.get("suggestions", []),
                "seo_score": result.get("seo_score", 0)
            }

        except Exception as e:
            logger.error(f"优化失败: {str(e)}")
            return {
                "optimized": content,
                "suggestions": [],
                "seo_score": 0
            }

    async def generate_image(self, prompt: str, style: str = "photorealistic") -> Dict[str, Any]:
        """
        生成配图（使用 DALL-E）

        Args:
            prompt: 图片描述
            style: 风格

        Returns:
            生成结果
        """
        logger.info(f"生成配图: prompt={prompt[:50]}...")

        try:
            import openai
            openai.api_key = self.openai_api_key

            response = openai.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1024x1024",
                quality="standard",
                n=1
            )

            image_url = response.data[0].url

            return {
                "image_url": image_url,
                "prompt": prompt,
                "style": style
            }

        except Exception as e:
            logger.error(f"生成配图失败: {str(e)}")
            return {
                "image_url": None,
                "error": str(e)
            }

    def get_templates(self, content_type: Optional[str] = None) -> List[Dict]:
        """获取模板"""
        if content_type:
            return [t for t in self.templates if t["content_type"] == content_type]
        return self.templates

    def create_template(
        self,
        name: str,
        content_type: str,
        template: str,
        description: Optional[str] = None
    ):
        """创建模板"""
        self.templates.append({
            "name": name,
            "content_type": content_type,
            "template": template,
            "description": description
        })

        self._save_templates()

    def _build_prompt(
        self,
        topic: str,
        content_type: str,
        tone: str,
        length: int,
        keywords: Optional[List[str]],
        target_audience: Optional[str],
        brand_voice: Optional[str],
        template: Optional[str]
    ) -> str:
        """构建生成提示词"""
        platform_guides = {
            "wechat": "微信公众号文章。要求：有吸引力的标题、清晰的段落结构、适合深入阅读。",
            "xiaohongshu": "小红书笔记。要求：emoji 表情、短句、真实感、包含话题标签。",
            "weibo": "微博文案。要求：简洁有力、互动性强、适合转发。",
            "email": "营销邮件。要求：专业的标题、个性化的称呼、明确的 CTA。",
            "blog": "博客文章。要求：SEO 友好、信息丰富、结构清晰。"
        }

        prompt = f"""请创作一篇营销内容。

## 主题
{topic}

## 平台
{content_type}
{platform_guides.get(content_type, "")}

## 要求
- 语气：{tone}
- 长度：约 {length} 字
"""

        if keywords:
            prompt += f"- 关键词：{', '.join(keywords)}\n"

        if target_audience:
            prompt += f"- 目标受众：{target_audience}\n"

        if brand_voice:
            prompt += f"- 品牌声音：{brand_voice}\n"

        if template:
            prompt += f"\n## 参考模板\n{template}\n"

        prompt += """
## 输出格式
请按以下 JSON 格式输出：
```json
{
  "title": "标题",
  "content": "正文内容（Markdown 格式）",
  "hashtags": ["标签1", "标签2"],
  "seo_keywords": ["SEO关键词1", "SEO关键词2"]
}
```

只输出 JSON，不要有其他内容。
"""

        return prompt

    def _parse_generated(self, generated: str, content_type: str) -> Dict[str, Any]:
        """解析生成的内容"""
        try:
            # 更健壮的 JSON 提取
            # 方法1：使用正则匹配完整的 JSON 对象
            import re
            json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
            matches = re.findall(json_pattern, generated, re.DOTALL)
            
            if matches:
                # 尝试解析找到的最后一个完整 JSON
                for json_str in reversed(matches):
                    try:
                        result = json.loads(json_str)
                        return {
                            "content": result.get("content", generated),
                            "title": result.get("title"),
                            "hashtags": result.get("hashtags", []),
                            "seo_keywords": result.get("seo_keywords", [])
                        }
                    except json.JSONDecodeError:
                        continue
            
            # 方法2：简单的括号匹配（备用）
            json_start = generated.find("{")
            if json_start >= 0:
                # 找到匹配的 closing brace
                depth = 0
                for i, char in enumerate(generated[json_start:], json_start):
                    if char == '{':
                        depth += 1
                    elif char == '}':
                        depth -= 1
                        if depth == 0:
                            json_str = generated[json_start:i+1]
                            try:
                                result = json.loads(json_str)
                                return {
                                    "content": result.get("content", generated),
                                    "title": result.get("title"),
                                    "hashtags": result.get("hashtags", []),
                                    "seo_keywords": result.get("seo_keywords", [])
                                }
                            except json.JSONDecodeError:
                                break
            
            # 都没成功，返回原始内容
            return {
                "content": generated,
                "title": None,
                "hashtags": [],
                "seo_keywords": []
            }

        except Exception as e:
            logger.error(f"解析生成内容失败: {str(e)}")
            return {
                "content": generated,
                "title": None,
                "hashtags": [],
                "seo_keywords": []
            }

    def _get_template(self, content_type: str) -> Optional[str]:
        """获取模板"""
        for t in self.templates:
            if t["content_type"] == content_type:
                return t["template"]
        return None

    def _load_templates(self) -> List[Dict]:
        """加载模板"""
        return [
            {
                "name": "微信公众号-标准模板",
                "content_type": "wechat",
                "template": "# {标题}\n\n## 引言\n{开场白}\n\n## 正文\n{核心内容}\n\n## 结语\n{行动号召}",
                "description": "适合微信公众号的标准文章结构"
            },
            {
                "name": "小红书-种草模板",
                "content_type": "xiaohongshu",
                "template": "{开头 emoji} {标题}\n\n{真实体验描述}\n\n✨ {亮点1}\n✨ {亮点2}\n✨ {亮点3}\n\n💡 {使用建议}\n\n#话题1 #话题2 #话题3",
                "description": "适合小红书的种草笔记结构"
            }
        ]

    def _save_templates(self):
        """保存模板"""
        try:
            import os
            template_file = "data/templates.json"
            os.makedirs(os.path.dirname(template_file), exist_ok=True)

            with open(template_file, 'w', encoding='utf-8') as f:
                json.dump(self.templates, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存模板失败: {str(e)}")
