# 营销内容生成 Agent

智能体工程师培养计划 - 项目 10：端到端 Agent 应用（毕业设计） - 选题 4

## 项目简介

营销内容生成 Agent 是一个智能营销内容创作工具，它能够：

- 根据主题生成各类营销内容
- 支持微信公众号、小红书、微博、邮件、博客等平台
- 自动优化 SEO 和可读性
- 生成配图（可选）
- 批量生成内容提高效率

## 学习目标

通过本项目，你将掌握：

1. **内容生成** - 使用 LLM 生成高质量的营销文案
2. **平台适配** - 针对不同平台优化内容风格
3. **SEO 优化** - 自动优化关键词和可读性
4. **批量处理** - 高效生成大量内容
5. **多模态生成** - 结合文本和图像生成

## 技术栈

- **后端框架**: FastAPI
- **LLM**: OpenAI API / Anthropic API
- **图像生成**: DALL-E / Stable Diffusion
- **文本分析**: jieba, NLTK
- **监控**: Prometheus
- **部署**: Docker + Docker Compose

## 项目结构

```
topic4-marketing-agent/
├── src/
│   ├── app.py                      # FastAPI 主应用
│   ├── agent/
│   │   └── content_agent.py      # 内容生成 Agent
│   └── tools/
│       └── content_tools.py        # 内容工具集
├── data/
│   ├── templates.json             # 内容模板
│   └── history/                  # 生成历史
├── output/                        # 输出目录
├── prometheus/
│   └── prometheus.yml            # Prometheus 配置
├── docker-compose.yml              # 服务编排
├── requirements.txt                # Python 依赖
├── .env.example                  # 环境变量模板
└── README.md                     # 本文件
```

## 快速开始

### 1. 环境准备

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，填写必要配置
# - OPENAI_API_KEY: OpenAI API Key
```

### 2. 本地开发

```bash
# 安装依赖
pip install -r requirements.txt

# 启动应用
python -m src.app

# 访问 API 文档
open http://localhost:8000/docs
```

### 3. Docker 部署

```bash
# 构建并启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f marketing-agent

# 停止服务
docker-compose down
```

## API 文档

### POST /api/v1/generate

生成营销内容

**请求体:**
```json
{
  "topic": "秋季新款连衣裙上市",
  "content_type": "xiaohongshu",
  "tone": "casual",
  "length": 500,
  "keywords": ["秋季穿搭", "连衣裙", "新品"],
  "target_audience": "25-35 岁女性",
  "brand_voice": "时尚、年轻、有态度"
}
```

**响应:**
```json
{
  "content": "✨ 秋季新款连衣裙来啦！...\n\n#秋季穿搭 #连衣裙 #新品",
  "title": "秋季新款连衣裙，美到犯规！",
  "hashtags": ["#秋季穿搭#", "#连衣裙#", "#新品#"],
  "seo_keywords": ["秋季穿搭", "连衣裙", "新品"]
}
```

### POST /api/v1/batch

批量生成内容

**请求体:**
```json
{
  "requests": [
    {"topic": "产品 A 介绍", "content_type": "wechat"},
    {"topic": "产品 B 介绍", "content_type": "xiaohongshu"}
  ],
  "generate_images": false
}
```

### POST /api/v1/optimize

优化内容

**请求体:**
```
content: 原始内容（text/plain）
platform: wechat
```

**响应:**
```json
{
  "original": "原始内容...",
  "optimized": "优化后的内容...",
  "suggestions": ["建议1", "建议2"],
  "seo_score": 85
}
```

### POST /api/v1/generate-image

生成配图

**请求体:**
```
prompt: 秋季连衣裙穿搭
style: photorealistic
```

### GET /api/v1/templates

获取内容模板

### POST /api/v1/templates

创建内容模板

### GET /health

健康检查

## 内容类型

| 类型 | 平台 | 特点 |
|------|------|------|
| wechat | 微信公众号 | 深度、结构化、适合长文 |
| xiaohongshu | 小红书 | emoji、短句、真实感、话题标签 |
| weibo | 微博 | 简洁、互动性强、适合转发 |
| email | 营销邮件 | 专业、个性化、明确的 CTA |
| blog | 博客 | SEO 友好、信息丰富、结构清晰 |

## 语气风格

| 风格 | 说明 |
|------|------|
| professional | 专业、正式 |
| casual | 随意、亲切 |
| funny | 幽默、有趣 |
| inspirational | 励志、正能量 |

## 工具功能

### 关键词提取

从内容中自动提取关键词

### SEO 分析

计算 SEO 分数，提供优化建议

指标：
- 关键词密度
- 标题使用
- 段落长度
- 内容长度

### 可读性检查

检查内容可读性，提供改进建议

### 标题优化

生成多个优化后的标题供选择

### 标签生成

自动生成适合平台的话题标签

## 扩展方向

1. **多语言支持** - 生成多语言营销内容
2. **A/B 测试** - 自动生成多个版本进行 A/B 测试
3. **竞品分析** - 分析竞品内容，生成差异化内容
4. **自动发布** - 对接各平台 API，自动发布内容
5. **效果分析** - 跟踪内容表现，优化生成策略
6. **视频脚本** - 生成短视频脚本和分镜

## 测试场景

### 场景 1：生成小红书笔记

```bash
curl -X POST http://localhost:8000/api/v1/generate \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "秋季新款连衣裙",
    "content_type": "xiaohongshu",
    "tone": "casual",
    "length": 500,
    "keywords": ["秋季穿搭", "连衣裙"]
  }'
```

### 场景 2：优化内容

```bash
curl -X POST http://localhost:8000/api/v1/optimize \
  -H "Content-Type: text/plain" \
  -d "原始内容..."
```

### 场景 3：批量生成

```bash
curl -X POST http://localhost:8000/api/v1/batch \
  -H "Content-Type: application/json" \
  -d '{
    "requests": [
      {"topic": "产品 A", "content_type": "wechat"},
      {"topic": "产品 B", "content_type": "weibo"}
    ]
  }'
```

### 场景 4：生成配图

```bash
curl -X POST http://localhost:8000/api/v1/generate-image \
  -H "Content-Type: text/plain" \
  -d "秋季连衣裙穿搭，时尚杂志风格"
```

## 故障排查

### LLM 调用失败

- 检查 `OPENAI_API_KEY` 是否有效
- 检查 API 配额是否充足

### 图像生成失败

- 检查 `OPENAI_API_KEY` 是否有 DALL-E 权限
- 检查生成提示词是否符合政策

### 内容质量不佳

- 调整 `temperature` 参数（0.3-0.7 适合营销内容）
- 提供更详细的 `brand_voice` 和 `target_audience`
- 使用模板约束输出风格

## 许可证

MIT License

## 参考资料

- [OpenAI API 文档](https://platform.openai.com/docs/)
- [微信公众号运营规范](https://weixin.qq.com/)
- [小红书社区规范](https://www.xiaohongshu.com/)
- [SEO 最佳实践](https://moz.com/beginners-guide-to-seo)
