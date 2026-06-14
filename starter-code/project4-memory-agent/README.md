# 项目 4：有记忆的对话 Agent

> Phase 2 - 系统构建 | 预计用时：1-2 周

## 项目简介

构建一个具备**短期记忆**和**长期记忆**的智能对话 Agent，能够记住用户的偏好和历史对话，提供个性化体验。

### 核心能力

- **短期记忆**（Redis）：存储当前会话的最近对话，支持快速存取和 TTL 自动过期
- **长期记忆**（Chroma 向量库）：将对话摘要向量化存储，支持语义检索，实现跨会话记忆
- **对话摘要**：定期将对话历史压缩为摘要，节省 Token 并保持上下文连贯
- **用户画像**：从对话中自动提取用户特征（姓名、职业、兴趣、偏好等），持续更新
- **流式 API**：基于 FastAPI 提供 SSE 流式对话接口

## 技术架构

```
用户输入
   │
   ▼
┌─────────────────────────────────────┐
│         LangGraph 状态图             │
│                                     │
│   retrieve → generate → [条件分支]  │
│                  │                  │
│                  ├──→ update_profile │
│                  └──→ summarize     │
└─────────────────────────────────────┘
   │
   ├── 短期记忆（Redis）
   ├── 长期记忆（Chroma）
   └── 用户画像（Redis）
```

## 快速开始

### 1. 环境准备

```bash
# 复制环境变量模板
cp .env.example .env
# 填写 OPENAI_API_KEY 等配置

# 安装依赖
pip install -r requirements.txt

# 启动 Redis 和 Chroma
docker-compose up -d
```

### 2. 命令行对话

```bash
python -m src.agent
```

### 3. 启动 API 服务

```bash
python -m src.api
# 服务启动在 http://localhost:8000
# API 文档：http://localhost:8000/docs
```

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| POST | `/chat` | 非流式对话 |
| POST | `/chat/stream` | 流式对话（SSE） |
| GET | `/profile/{user_id}` | 获取用户画像 |
| POST | `/profile/{user_id}/reset` | 重置用户画像 |
| DELETE | `/memory/short/{user_id}/{session_id}` | 清空短期记忆 |
| DELETE | `/memory/long/{user_id}` | 清空长期记忆 |

### 流式对话示例

```bash
curl -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"user_id": "alice", "message": "你好，我是 Alice", "stream": true}'
```

## 环境变量说明

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `OPENAI_API_KEY` | 必填 | OpenAI API 密钥 |
| `OPENAI_BASE_URL` | 可选 | 自定义 API 地址（如 Azure） |
| `MODEL_NAME` | `gpt-4o-mini` | 使用的模型名 |
| `REDIS_URL` | `redis://localhost:6379` | Redis 连接地址 |
| `CHROMA_HOST` | `localhost` | Chroma 服务主机 |
| `CHROMA_PORT` | `8000` | Chroma 服务端口 |
| `API_HOST` | `0.0.0.0` | API 绑定地址 |
| `API_PORT` | `8000` | API 监听端口 |

## 目录结构

```
project4-memory-agent/
├── src/
│   ├── agent.py           # LangGraph Agent 主文件
│   ├── api.py             # FastAPI 服务（流式）
│   ├── memory/
│   │   ├── short_term.py # 短期记忆（Redis）
│   │   ├── long_term.py  # 长期记忆（Chroma）
│   │   └── summarizer.py # 对话摘要器
│   └── tools/
│       └── profile.py    # 用户画像工具
├── tests/
│   └── test_memory.py    # 记忆模块测试
├── docker-compose.yml     # Redis + Chroma 服务
├── requirements.txt
├── .env.example
└── README.md
```

## 学习要点

1. **LangGraph 状态图**：理解 `StateGraph`、`add_node`、`add_edge` 的使用
2. **Redis 数据结构设计**：List 存储消息、TTL 管理会话生命周期
3. **向量检索**：Chroma 相似度搜索、`where` 过滤条件
4. **用户画像提取**：用 LLM 从非结构化对话中提取结构化信息
5. **SSE 流式响应**：FastAPI 的 `StreamingResponse` 实现逐 token 推送

## 扩展挑战

- [ ] 支持多模态输入（图片 + 文字）
- [ ] 添加记忆重要性评分（重要记忆长期保留）
- [ ] 实现记忆遗忘机制（遗忘不重要或过期的信息）
- [ ] 支持多个 LLM 提供商（OpenAI / Anthropic / 本地模型）
