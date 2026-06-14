# Obsidian 知识助手

智能体工程师培养计划 - 项目 10：端到端 Agent 应用（毕业设计） - 选题 3

## 项目简介

Obsidian 知识助手是一个个人知识库助手，它能够：

- 读取和搜索 Obsidian 笔记
- 使用 LLM 理解用户问题
- 基于笔记内容回答用户问题
- 支持语义搜索和关键词搜索
- 自动总结笔记内容

## 学习目标

通过本项目，你将掌握：

1. **本地文件处理** - 读取和解析 Markdown 文件
2. **向量检索** - 使用嵌入模型进行语义搜索
3. **RAG 应用** - 检索增强生成（Retrieval-Augmented Generation）
4. **知识图谱** - 构建和查询知识关联
5. **个人知识管理** - 提升个人知识库使用效率

## 技术栈

- **后端框架**: FastAPI
- **LLM**: OpenAI API / Anthropic API
- **向量数据库**: ChromaDB（可选）
- **嵌入模型**: OpenAI Embeddings / Sentence Transformers
- **Markdown 处理**: markdown, BeautifulSoup
- **部署**: Docker + Docker Compose

## 项目结构

```
topic3-obsidian-agent/
├── src/
│   ├── app.py                      # FastAPI 主应用
│   ├── agent/
│   │   └── knowledge_agent.py    # 知识检索 Agent
│   └── tools/
│       └── obsidian_tools.py       # Obsidian 工具集
├── vault/                         # Obsidian 笔记库（挂载）
├── data/                          # 数据目录
│   └── chroma/                   # Chroma 向量数据库
├── docker-compose.yml              # 服务编排
├── requirements.txt                # Python 依赖
├── .env.example                   # 环境变量模板
└── README.md                      # 本文件
```

## 快速开始

### 1. 环境准备

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，填写必要配置
# - OBSIDIAN_VAULT_PATH: Obsidian 笔记库路径
# - OPENAI_API_KEY: OpenAI API Key
```

### 2. 本地开发

```bash
# 安装依赖
pip install -r requirements.txt

# 设置环境变量
export OBSIDIAN_VAULT_PATH=/path/to/your/vault

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
docker-compose logs -f knowledge-agent

# 停止服务
docker-compose down
```

## API 文档

### POST /api/v1/search

搜索笔记

**请求体:**
```json
{
  "query": "Agent 设计模式",
  "top_k": 5,
  "folder": "AI"
}
```

**响应:**
```json
[
  {
    "file_path": "AI/Agent-Design.md",
    "title": "Agent Design",
    "content_snippet": "## Agent 设计模式\n\n1. ReAct...",
    "score": 0.92,
    "tags": ["ai", "agent"]
  }
]
```

### POST /api/v1/ask

提问

**请求体:**
```json
{
  "question": "什么是 ReAct 模式？",
  "context_files": ["AI/Agent-Design.md"]
}
```

**响应:**
```json
{
  "answer": "ReAct 模式是...（基于笔记内容回答）",
  "sources": [
    {
      "file_path": "AI/Agent-Design.md",
      "title": "Agent Design",
      "tags": ["ai", "agent"]
    }
  ],
  "confidence": 0.85
}
```

### GET /api/v1/notes

列出笔记

**Query 参数:**
- `folder`: 文件夹路径（可选）

### GET /api/v1/notes/{file_path}

获取笔记内容

### POST /api/v1/notes

创建笔记

**请求体:**
```json
{
  "title": "新笔记",
  "content": "## 内容...",
  "folder": "AI",
  "tags": ["ai", "agent"]
}
```

### PUT /api/v1/notes/{file_path}

更新笔记内容

### GET /api/v1/tags

列出所有标签

### GET /health

健康检查

## 搜索模式

### 关键词搜索

基于字符串匹配的简单搜索，快速有效。

### 语义搜索

使用嵌入模型将查询和笔记转换为向量，计算余弦相似度。

需要配置：
- `OPENAI_API_KEY` 或使用本地嵌入模型
- 可选：启动 ChromaDB 服务

## 扩展方向

1. **知识图谱** - 从笔记中提取实体和关系，构建知识图谱
2. **自动标签** - 使用 LLM 自动为笔记打标签
3. **笔记推荐** - 根据用户当前笔记推荐相关笔记
4. **定期总结** - 定期总结知识库，生成周报/月报
5. **多知识库** - 支持多个 Obsidian vault
6. **协作知识库** - 支持团队共享知识库

## 测试场景

### 场景 1：关键词搜索

```bash
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "Agent", "top_k": 5}'
```

### 场景 2：知识问答

```bash
curl -X POST http://localhost:8000/api/v1/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "如何设计一个 Agent？"}'
```

### 场景 3：创建笔记

```bash
curl -X POST http://localhost:8000/api/v1/notes \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Agent 学习笔记",
    "content": "## 今日学习\n\n- 学习了 ReAct 模式",
    "folder": "AI",
    "tags": ["ai", "learning"]
  }'
```

### 场景 4：获取所有标签

```bash
curl http://localhost:8000/api/v1/tags
```

## 故障排查

### Vault 路径不存在

- 检查 `OBSIDIAN_VAULT_PATH` 是否正确
- Docker 部署时，确保挂载路径正确

### 语义搜索失败

- 检查 `OPENAI_API_KEY` 是否有效
- 检查是否启动 ChromaDB 服务

### LLM 调用失败

- 检查 `OPENAI_API_KEY` 是否有效
- 检查 API 配额是否充足

## 许可证

MIT License

## 参考资料

- [Obsidian 官方文档](https://help.obsidian.md/)
- [RAG 介绍](https://python.langchain.com/docs/tutorials/rag/)
- [ChromaDB 文档](https://docs.trychroma.com/)
- [OpenAI Embeddings 文档](https://platform.openai.com/docs/guides/embeddings)
