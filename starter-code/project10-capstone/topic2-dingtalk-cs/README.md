# 钉钉智能客服 Agent

智能体工程师培养计划 - 项目 10：端到端 Agent 应用（毕业设计） - 选题 2

## 项目简介

钉钉智能客服 Agent 是一个企业级智能客服系统，它能够：

- 接收钉钉群聊/单聊消息
- 使用 LLM 理解用户意图
- 调用后台 API 查询订单、物流等信息
- 自动回复用户咨询
- 支持转人工客服

## 学习目标

通过本项目，你将掌握：

1. **企业 IM 集成** - 钉钉机器人 Webhook 集成
2. **意图识别** - 使用 LLM 进行意图识别和实体提取
3. **工具调用** - Agent 调用后台 API 完成复杂任务
4. **会话管理** - 维护多轮对话上下文
5. **知识库集成** - 搜索知识库回答常见问题

## 技术栈

- **后端框架**: FastAPI
- **LLM**: OpenAI API / Anthropic API
- **企业 IM**: 钉钉自定义机器人
- **数据库**: Redis (Session 存储)
- **监控**: Prometheus
- **部署**: Docker + Docker Compose

## 项目结构

```
topic2-dingtalk-cs/
├── src/
│   ├── app.py                    # FastAPI 主应用
│   ├── agent/
│   │   └── cs_agent.py         # 客服 Agent 核心逻辑
│   └── tools/
│       └── customer_tools.py     # 客服工具集
├── data/
│   └── knowledge_base.json      # 知识库数据
├── prometheus/
│   └── prometheus.yml           # Prometheus 配置
├── docker-compose.yml           # 服务编排
├── requirements.txt              # Python 依赖
├── .env.example                # 环境变量模板
└── README.md                   # 本文件
```

## 快速开始

### 1. 环境准备

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，填写必要配置
# - DINGTALK_APP_KEY: 钉钉应用 Key
# - DINGTALK_APP_SECRET: 钉钉应用 Secret
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
docker-compose logs -f cs-agent

# 停止服务
docker-compose down
```

## 钉钉机器人配置

### 方式一：自定义机器人（群聊）

1. 在钉钉群聊中，点击 **群设置 > 智能群助手 > 添加机器人**
2. 选择 **自定义机器人**
3. 填写机器人名称，选择 **加签** 安全设置
4. 复制 **Webhook 地址** 和 **加签密钥**
5. 在 `.env` 中配置 `DINGTALK_WEBHOOK_URL` 和 `DINGTALK_APP_SECRET`

### 方式二：企业内部应用（单聊）

1. 登录 [钉钉开放平台](https://open.dingtalk.com/)
2. 创建 **企业内部应用**
3. 添加 **机器人** 能力
4. 配置 **消息接收地址** 为 `https://your-domain.com/webhook/dingtalk`
5. 复制 **AppKey** 和 **AppSecret** 到 `.env`

## API 文档

### POST /webhook/dingtalk

接收钉钉 Webhook 消息

**Headers:**
- `timestamp`: 时间戳
- `sign`: 签名（用于验证）

**请求体:**
```json
{
  "msgtype": "text",
  "text": {
    "content": "你好，我的订单号是 12345，请问发货了吗？"
  },
  "senderId": "user_id_here",
  "conversationId": "conv_id_here"
}
```

**响应:**
- `200 OK`: 消息已接收
- `401 Unauthorized`: 签名验证失败

### POST /api/v1/chat

主动聊天接口

**请求体:**
```json
{
  "user_id": "user123",
  "message": "查询订单 12345",
  "session_id": "session_abc"
}
```

**响应:**
```json
{
  "reply": "您好！订单 12345 已发货，物流单号：SF1234567890。预计 2 天后送达。",
  "session_id": "session_abc",
  "intent": "query_shipping",
  "confidence": 0.95
}
```

### GET /api/v1/sessions/{session_id}

获取会话历史

### DELETE /api/v1/sessions/{session_id}

清除会话历史

### GET /health

健康检查

## 意图识别

Agent 支持以下意图：

| 意图 | 说明 | 需要工具 |
|------|------|----------|
| query_order | 查询订单 | ✅ query_order |
| cancel_order | 取消订单 | ✅ cancel_order |
| return_refund | 退货退款 | ❌ 转人工 |
| query_shipping | 查询物流 | ✅ query_shipping |
| product_inquiry | 商品咨询 | ✅ search_kb |
| complaint | 投诉建议 | ❌ 创建工单 |
| greeting | 问候 | ❌ |
| fallback | 无法理解 | ❌ |

## 工具列表

### query_order

查询订单信息

**参数:**
- `order_id`: 订单 ID
- `user_id`: 用户 ID (可选)

### cancel_order

取消订单

**参数:**
- `order_id`: 订单 ID
- `reason`: 取消原因 (可选)

### query_shipping

查询物流信息

**参数:**
- `order_id`: 订单 ID

### search_kb

搜索知识库

**参数:**
- `query`: 搜索关键词
- `category`: 分类 (可选)

### create_ticket

创建工单

**参数:**
- `user_id`: 用户 ID
- `issue_type`: 问题类型
- `description`: 问题描述

### transfer_to_human

转接人工客服

**参数:**
- `user_id`: 用户 ID
- `reason`: 转接原因

## 监控

### Prometheus 指标

访问 `http://localhost:8000/metrics` 查看指标

主要指标：
- `cs_message_received_total`: 接收消息总数
- `cs_intent_recognized_total`: 意图识别总数
- `cs_tool_executed_total`: 工具调用总数
- `cs_response_duration_seconds`: 响应耗时

## 扩展方向

1. **多轮对话** - 支持更复杂的多轮对话流程
2. **情感分析** - 检测用户情绪，优先级调整
3. **个性化推荐** - 根据用户历史推荐商品
4. **多渠道支持** - 支持企业微信、飞书等
5. **语音支持** - 语音消息转文字并回复
6. **主动推送** - 物流更新、活动通知等主动推送

## 测试场景

### 场景 1：订单查询

```
用户: 你好，我的订单号是 12345，请问发货了吗？
Agent: 您好！订单 12345 已发货，物流单号：SF1234567890。
       预计 2 天后送达。您可以通过顺丰速运官网查询详细物流信息。
```

### 场景 2：取消订单

```
用户: 我想取消订单 67890
Agent: 您好！订单 67890 当前状态为"待付款"，可以取消。
       取消后将在 1-3 个工作日内退款 399.00 元。确认取消吗？
用户: 确认
Agent: 订单 67890 已成功取消，退款将在 1-3 个工作日内到账。
```

### 场景 3：知识库查询

```
用户: 请问可以退货吗？
Agent: 当然可以！我们支持 7 天无理由退货，30 天质量问题换货。
       您可以在订单详情页点击"申请退货"按钮发起退货申请。
```

### 场景 4：转人工

```
用户: 我要投诉！
Agent: 很抱歉给您带来不便。正在为您转接人工客服，请稍候...
       （当前排队位置：3，预计等待 5 分钟）
```

## 故障排查

### 钉钉签名验证失败

- 检查 `DINGTALK_APP_SECRET` 是否正确
- 确保时间戳在 1 小时内

### 无法接收钉钉消息

- 检查 Webhook URL 是否配置正确
- 确保公网可访问（或使用 ngrok 内网穿透）

### LLM 调用失败

- 检查 `OPENAI_API_KEY` 是否有效
- 检查 API 配额是否充足

## 许可证

MIT License

## 参考资料

- [钉钉开放平台文档](https://open.dingtalk.com/document/)
- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [OpenAI API 文档](https://platform.openai.com/docs/)
