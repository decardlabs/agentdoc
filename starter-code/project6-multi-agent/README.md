# 项目 6：多 Agent 系统

> Phase 2 - 系统构建 | 预计用时：1-2 周

## 项目简介

构建一个**多 Agent 协作写作系统**，4 个专业 Agent 各司其职，通过 LangGraph 编排实现**顺序执行 + 条件分支**，输出 1000+ 字的高质量文章。

### 核心能力

| Agent | 职责 | 输出 |
|--------|------|------|
| 🔍 研究员 | 搜集资料和事实 | 结构化研究材料 |
| ✍️ 写作者 | 根据资料撰写文章 | 文章草稿（1000+ 字）|
| 📝 审校者 | 审校文章质量 | 通过/不通过 + 修改意见 |
| 💡 批评者（可选）| 深度评价和打分 | 评分 + 详细评论 |

### 工作流程

```
用户提交主题
       │
       ▼
   ┌──────────┐
   │ 研究员    │ → 搜集资料
   └──────────┘
       │
       ▼
   ┌──────────┐
   │ 写作者    │ → 撰写草稿
   └──────────┘
       │
       ▼
   ┌──────────┐
   │ 审校者    │ → 审校质量
   └──────────┘
       │
       ├── 不通过 ──→ 打回写作者（最多 2 次）
       │
       ▼ 通过
   ┌──────────┐
   │ 批评者    │ → 深度评价（可选）
   └──────────┘
       │
       ▼
   ┌──────────┐
   │ 人工审核   │ → 人工审批（可选）
   └──────────┘
       │
       ▼
     输出最终文章
```

## 快速开始

### 1. 环境准备

```bash
# 复制环境变量模板
cp .env.example .env
# 填写 OPENAI_API_KEY

# 安装依赖
pip install -r requirements.txt
```

### 2. 命令行运行

```bash
python -m src.orchestrator
```

示例对话：

```
文章主题: 大语言模型的发展现状与未来趋势

⏳ 开始处理，主题: 大语言模型的发展现状与未来趋势
（这可能需要 1-3 分钟，请耐心等待...）

✅ 处理完成！
主题: 大语言模型的发展现状与未来趋势
修订次数: 1
最终文章长度: 1245 字
批评者评分: 8.2
📄 文章已保存到: output/article_大语言模型的发展现状与未来趋势.md
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
| POST | `/write` | 提交写作任务（异步）|
| GET | `/tasks/{task_id}` | 查询任务状态 |
| GET | `/tasks/{task_id}/result` | 获取任务结果 |
| GET | `/tasks/{task_id}/article` | 下载最终文章 |
| POST | `/tasks/{task_id}/approve` | 人工审核通过/拒绝 |
| GET | `/tasks` | 列出所有任务 |

### 提交写作任务示例

```bash
curl -X POST http://localhost:8000/write \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "AI Agent 技术原理与应用",
    "style": "科普",
    "enable_critic": true,
    "enable_human_review": false
  }'
```

返回：

```json
{
  "task_id": "a1b2c3d4-...",
  "topic": "AI Agent 技术原理与应用",
  "status": "pending"
}
```

然后用 `task_id` 查询结果：

```bash
curl http://localhost:8000/tasks/a1b2c3d4-.../result
```

## 环境变量说明

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `OPENAI_API_KEY` | 必填 | OpenAI API 密钥 |
| `OPENAI_BASE_URL` | 可选 | 自定义 API 地址 |
| `MODEL_NAME` | `gpt-4o-mini` | 使用的模型名 |
| `MAX_REVISIONS` | `2` | 最大修订次数 |
| `ENABLE_CRITIC` | `true` | 是否启用批评者 |
| `ENABLE_HUMAN_REVIEW` | `false` | 是否启用人工审核 |
| `API_HOST` | `0.0.0.0` | API 绑定地址 |
| `API_PORT` | `8000` | API 监听端口 |

## 目录结构

```
project6-multi-agent/
├── src/
│   ├── orchestrator.py      # Agent 编排器（LangGraph）
│   ├── api.py              # FastAPI 服务
│   ├── agents/
│   │   ├── researcher.py   # 研究员工
│   │   ├── writer.py      # 写作者 Agent
│   │   ├── reviewer.py    # 审校者 Agent
│   │   └── critic.py      # 批评者 Agent（可选）
│   └── tools/
│       ├── search.py       # 搜索工具（模拟）
│       └── crawler.py     # 爬虫工具（模拟）
├── output/                  # 生成的文章
├── tests/
│   └── test_orchestrator.py
├── requirements.txt
├── .env.example
└── README.md
```

## 学习要点

1. **LangGraph 条件边**：`add_conditional_edges` 实现审校不通过打回
2. **状态共享**：多个 Agent 通过 `MultiAgentState` 共享数据
3. **Agent 专业化**：每个 Agent 有明确的 Prompt 和输出格式
4. **人工审核节点**：HITL（Human-in-the-Loop）的实现方式
5. **异步 API**：FastAPI `BackgroundTasks` 实现任务异步执行

## 扩展挑战

- [ ] 将搜索工具替换为真实搜索 API（SerpAPI / Bing Search）
- [ ] 添加更多 Agent 角色（如"事实核查员"、"翻译官"）
- [ ] 实现 Agent 之间的辩论机制（多轮对抗提升质量）
- [ ] 支持多语言文章生成
- [ ] 添加文章 plagiarism 检查
