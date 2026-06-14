# GitHub Code Review Agent

智能体工程师培养计划 - 项目 10：端到端 Agent 应用（毕业设计） - 选题 1

## 项目简介

GitHub Code Review Agent 是一个自动化的代码审查工具，它能够：

- 接收 GitHub PR Webhook 事件
- 使用 LLM 分析代码变更
- 自动生成代码审查意见
- 将审查结果发布到 GitHub PR

## 学习目标

通过本项目，你将掌握：

1. **Webhook 集成** - 接收和处理 GitHub Webhook 事件
2. **LLM 应用** - 使用 LLM 进行代码分析
3. **GitHub API** - 调用 GitHub REST API
4. **异步编程** - 使用 Python asyncio 处理并发
5. **容器化部署** - Docker + Docker Compose 部署

## 技术栈

- **后端框架**: FastAPI
- **LLM**: OpenAI API / Anthropic API
- **GitHub 集成**: PyGithub + aiohttp
- **监控**: Prometheus + Grafana
- **部署**: Docker + Docker Compose

## 项目结构

```
topic1-github-review/
├── src/
│   ├── app.py                  # FastAPI 主应用
│   ├── github_webhook.py       # GitHub Webhook 处理
│   ├── agent/
│   │   └── review_agent.py    # 审查 Agent 核心逻辑
│   └── tools/
│       └── git_tools.py        # Git 工具函数
├── prometheus/
│   └── prometheus.yml         # Prometheus 配置
├── grafana/
│   ├── provisioning/          # Grafana 配置
│   └── dashboards/            # 仪表盘 JSON
├── docker-compose.yml         # 服务编排
├── requirements.txt           # Python 依赖
├── .env.example              # 环境变量模板
└── README.md                 # 本文件
```

## 快速开始

### 1. 环境准备

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，填写必要配置
# - GITHUB_TOKEN: GitHub Personal Access Token
# - GITHUB_WEBHOOK_SECRET: Webhook 密钥
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
docker-compose logs -f review-agent

# 停止服务
docker-compose down
```

## GitHub Webhook 配置

1. 打开 GitHub 仓库设置
2. 进入 **Settings > Webhooks > Add webhook**
3. 填写配置：
   - **Payload URL**: `https://your-domain.com/webhook/github`
   - **Content type**: `application/json`
   - **Secret**: 填写 `GITHUB_WEBHOOK_SECRET` 的值
   - **Events**: 选择 **Pull request**
4. 点击 **Add webhook**

## API 文档

### POST /webhook/github

接收 GitHub Webhook 事件

**Headers:**
- `X-GitHub-Event`: 事件类型
- `X-Hub-Signature-256`: 签名（用于验证）

**响应:**
- `202 Accepted`: Webhook 已接收，正在处理
- `401 Unauthorized`: 签名验证失败

### POST /api/v1/review

手动触发 PR 审查

**请求体:**
```json
{
  "repo_owner": "your-org",
  "repo_name": "your-repo",
  "pr_number": 123,
  "github_token": "optional-override-token",
  "review_level": "normal"
}
```

**响应:**
```json
{
  "pr_number": 123,
  "repo": "your-org/your-repo",
  "review_comments": [...],
  "summary": "## 审查摘要...",
  "generated_at": "2026-01-15T12:00:00Z"
}
```

### GET /health

健康检查

**响应:**
```json
{
  "status": "healthy",
  "timestamp": "2026-01-15T12:00:00Z",
  "version": "1.0.0"
}
```

## 审查级别

| 级别 | 说明 |
|------|------|
| basic | 只检查明显的 bug 和安全问题 |
| normal | 检查 bug、安全问题、代码风格和最佳实践 |
| strict | 严格检查所有问题，包括性能、可维护性和设计模式 |

## 监控

### Prometheus 指标

访问 `http://localhost:8000/metrics` 查看指标

主要指标：
- `github_webhook_received_total`: Webhook 接收总数
- `review_generated_total`: 审查生成总数
- `review_duration_seconds`: 审查耗时

### Grafana 仪表盘

访问 `http://localhost:13000` (admin/admin)

导入预配置的仪表盘查看：
- Webhook 接收速率
- 审查生成延迟
- 错误率
- Token 消耗

## 扩展方向

1. **多 LLM 支持** - 支持 Claude、Gemini 等多种模型
2. **自定义规则** - 允许用户配置自定义审查规则
3. **批量审查** - 支持批量审查多个 PR
4. **报告生成** - 生成 PDF/HTML 格式的审查报告
5. **Slack/钉钉通知** - 发送审查结果到即时通讯工具
6. **代码质量评分** - 给出量化的代码质量分数

## 测试场景

### 场景 1：自动审查

1. 配置 GitHub Webhook
2. 创建新 PR
3. 等待 Agent 自动审查
4. 查看 PR 评论

### 场景 2：手动审查

```bash
curl -X POST http://localhost:8000/api/v1/review \
  -H "Content-Type: application/json" \
  -d '{
    "repo_owner": "your-org",
    "repo_name": "your-repo",
    "pr_number": 123
  }'
```

### 场景 3：监控验证

1. 访问 Prometheus `http://localhost:19090`
2. 查询指标 `rate(github_webhook_received_total[5m])`
3. 访问 Grafana 查看仪表盘

## 故障排查

### Webhook 签名验证失败

- 检查 `GITHUB_WEBHOOK_SECRET` 是否和 GitHub 配置一致
- 确保 Webhook Secret 没有多余空格

### 无法访问 GitHub API

- 检查 `GITHUB_TOKEN` 是否有效
- 确保 Token 有 `repo` 权限
- 检查网络连通性

### LLM 调用失败

- 检查 `OPENAI_API_KEY` 是否有效
- 检查 API 配额是否充足
- 查看应用日志 `docker-compose logs review-agent`

## 许可证

MIT License

## 参考资料

- [GitHub Webhooks 文档](https://docs.github.com/en/developers/webhooks-and-events/webhooks)
- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [OpenAI API 文档](https://platform.openai.com/docs/)
