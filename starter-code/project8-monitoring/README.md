# 项目 8：监控与成本优化

> 智能体工程师培养计划 - Phase 3 生产工程

## 项目简介

本项目是"智能体工程师培养计划"的 Phase 3 第二个项目，旨在教授如何监控 Agent 系统并优化成本。

### 学习目标

- 理解 Agent 系统的监控需求（Tracing / Metrics / Logging / Cost）
- 集成 LangSmith 进行 LLM 调用追踪
- 配置 Prometheus + Grafana 监控栈
- 实现 Token 成本计算和预算控制
- 设置告警规则和异常检测

### 技术栈

- **追踪**: LangSmith, OpenTelemetry
- **指标**: Prometheus, Grafana
- **成本**: 自研成本追踪器
- **告警**: AlertManager, 钉钉/飞书 Webhook

## 项目结构

```
project8-monitoring/
├── src/
│   ├── monitor.py           # LangSmith 集成
│   ├── cost_tracker.py      # 成本追踪器
│   ├── metrics.py          # Prometheus 指标采集
│   ├── api.py             # FastAPI 监控 API
│   └── alerts.py           # 告警规则
├── prometheus/
│   ├── prometheus.yml     # Prometheus 配置
│   └── alert_rules.yml    # 告警规则
├── grafana/
│   ├── dashboards/        # Grafana 仪表板
│   └── provisioning/      # 数据源配置
├── docker-compose.monitoring.yml  # 监控栈编排
├── requirements.txt
├── .env.example
└── README.md
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
vim .env  # 填入 LangSmith API Key 等
```

### 3. 启动监控栈

```bash
# 启动 Prometheus + Grafana + AlertManager
docker compose -f docker-compose.monitoring.yml up -d

# 查看服务状态
docker compose -f docker-compose.monitoring.yml ps
```

### 4. 启动监控 API

```bash
# 启动 FastAPI 监控 API
uvicorn src.api:app --reload --host 0.0.0.0 --port 8002
```

### 5. 验证

```bash
# 健康检查
curl http://localhost:8002/health

# 访问 Prometheus
open http://localhost:9090

# 访问 Grafana（默认账号：admin/admin）
open http://localhost:3000

# 访问监控 API 文档
open http://localhost:8002/docs
```

## 详细指南

### LangSmith 集成

LangSmith 是 LangChain 官方提供的 LLM 调用追踪平台。

**配置步骤**：

1. 注册 LangSmith 账号：https://smith.langchain.com/
2. 获取 API Key
3. 设置环境变量：

```bash
export LANGCHAIN_TRACING_V2=true
export LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
export LANGCHAIN_API_KEY=ls__xxxxx
export LANGCHAIN_PROJECT=agent-monitoring
```

**使用装饰器追踪**：

```python
from src.monitor import LangSmithMonitor

monitor = LangSmithMonitor(enabled=True)

@monitor.trace_llm_call
def call_openai(prompt: str):
    # 这个函数会自动被追踪
    return client.chat.completions.create(...)
```

### Prometheus 指标采集

本项目定义了 20+ 指标，包括：

- **LLM 调用指标**: 调用总数、Token 消耗、成本、延迟
- **工具调用指标**: 调用总数、延迟、错误
- **Agent 运行指标**: 运行总数、延迟、迭代次数
- **成本指标**: 每小时成本、每日成本、预算使用率
- **系统指标**: 队列长度、活跃会话、连接池大小

**查看指标**：

```bash
# 启动指标服务器
from src.metrics import start_metrics_server
start_metrics_server(port=8001)

# 访问指标端点
curl http://localhost:8001/metrics
```

### Grafana 仪表板

预配置了 6 个 Panel：

1. **LLM 调用 QPS**: 实时 QPS 折线图
2. **P95 延迟**: 当前 P95 延迟数值
3. **Token 消耗速率**: 每小时 Token 消耗折线图
4. **错误率**: 当前错误率数值
5. **工具调用 QPS**: 工具调用频率折线图
6. **每小时成本**: 当前每小时成本数值

### 成本追踪

成本追踪器支持：

- 多模型定价表（gpt-4o-mini, gpt-4o, claude-3.5-sonnet 等）
- 单次调用成本计算
- 会话总成本计算
- 预算阈值检查
- 成本报告生成

**示例**：

```python
from src.cost_tracker import CostTracker

tracker = CostTracker(daily_budget=10.0, user_daily_budget=2.0)

# 计算成本
cost = tracker.calculate_cost(
    model="gpt-4o",
    prompt_tokens=2000,
    completion_tokens=500
)
print(f"成本: ${cost:.6f}")

# 检查预算
alerts = tracker.check_budget("user_001")
for alert in alerts:
    print(f"告警: {alert.alert_type}, 使用率: {alert.usage_pct}%")
```

### 告警规则

配置了 10 条告警规则：

1. **HighErrorRate**: 错误率 > 5%
2. **HighLatencyP95**: P95 延迟 > 10s
3. **HourlyCostExceeded**: 每小时 Token 消耗异常
4. **UserRateAnomaly**: 用户调用频率异常
5. **ToolFailureRate**: 工具调用失败率 > 10%
6. **AgentFailureRate**: Agent 运行失败率 > 10%
7. **DailyBudgetWarning**: 日预算 80%
8. **DailyBudgetExceeded**: 日预算耗尽
9. **UserDailyBudgetExceeded**: 用户日预算耗尽
10. **ServiceDown**: 服务不可用

## 测试场景

本项目包含 30 个测试场景：

1. **基础监控** (10 个): LangSmith 追踪、成本计算、Prometheus 指标等
2. **成本控制** (8 个): 预算告警、成本对账、缓存定价等
3. **性能监控** (6 个): P95 延迟、错误率、Grafana 刷新等
4. **异常检测与告警** (6 个): 延迟异常、成本异常、告警去重等

## 成本估算

| 组件 | 月成本 |
|------|--------|
| Prometheus (EC2 t3.small) | ~$15 |
| Grafana (共用) | $0 |
| 存储 (RDS) | ~$25 |
| **合计** | **~$40/月** |

## 扩展方向

完成项目 8 后，可以继续学习：

- **项目 9**: 安全与评估（Prompt 注入检测、安全过滤）
- **项目 10**: 端到端 Agent 应用（毕业设计）

## 参考资料

- [LangSmith 文档](https://docs.smith.langchain.com/)
- [Prometheus 文档](https://prometheus.io/docs/)
- [Grafana 文档](https://grafana.com/docs/)
- [OpenTelemetry 文档](https://opentelemetry.io/docs/)

## 许可证

MIT License

---

**Happy Monitoring! 📊**
