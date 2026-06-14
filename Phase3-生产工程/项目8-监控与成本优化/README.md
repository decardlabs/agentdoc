# 项目 8：监控与成本优化

> **阶段**：Phase 3 - 生产工程
> **周次**：Week 11
> **难度**：⭐⭐⭐⭐
> **预估工时**：15-20 小时

---

## 一、项目目标

为项目 7 的 Agent 系统接入监控，实时追踪 LLM 调用、Token 消耗、性能指标。

**核心能力培养**：
- LLM 调用追踪
- 成本计算与预警
- 性能指标监控
- 异常检测
- 可观测性思维

---

## 二、可观测性基础

### 三大支柱

```
┌─────────────────────────────────────┐
│          可观测性（Observability）    │
├─────────────────────────────────────┤
│                                     │
│  1. 日志（Logs）                    │
│     - 离散事件                      │
│     - "发生了什么"                  │
│                                     │
│  2. 指标（Metrics）                  │
│     - 数值化时序数据                 │
│     - "系统健康度"                  │
│                                     │
│  3. 链路追踪（Traces）               │
│     - 请求生命周期                  │
│     - "哪里慢了/出错了"             │
│                                     │
└─────────────────────────────────────┘
```

### Agent 系统的可观测性挑战

| 传统 Web 应用 | Agent 系统 |
|--------------|-----------|
| 请求/响应明确 | 多次 LLM 调用 |
| 一次调用一个服务 | 一次用户请求 = 多次 LLM + 多次工具 |
| 错误易定位 | 错误原因多样（幻觉、工具失败、Token 超限）|
| 成本易计算 | Token 成本波动大，难预测 |

**Agent 特有的监控指标**：
- 每次 LLM 调用的 Token 消耗
- 工具调用成功率
- Agent 循环次数
- 端到端响应时间
- 单次任务的成本

---

## 三、详细任务说明

### 3.1 基础版任务（必做，10-12 小时）

#### Step 1：接入 LangSmith（3 小时）

**任务清单**：
- [ ] 注册 LangSmith 账号
- [ ] 配置环境变量
- [ ] 自动追踪所有 LLM 调用
- [ ] 查看 Dashboard

**LangSmith 是什么？**
- LangChain 官方的可观测性平台
- 自动追踪 LLM 调用链
- 提供 Dashboard + 调试工具

**接入步骤**：
1. 访问 https://smith.langchain.com
2. 注册账号（免费额度：5K traces / 月，足够本课程使用）
3. 创建 API Key
4. 配置环境变量：

```bash
# .env
LANGCHAIN_TRACING_V2=true
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
LANGCHAIN_API_KEY=ls__...
LANGCHAIN_PROJECT=multi-agent-system
```

**自动追踪**：
```python
# 只要使用了 LangChain/LlamaIndex/AutoGen
# 开启 LANGCHAIN_TRACING_V2 后会自动追踪
# 无需修改代码

from langchain.chat_models import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o-mini")
response = llm.invoke("Hello")
# 这条调用会自动出现在 LangSmith Dashboard
```

**Dashboard 功能**：
- 所有 LLM 调用的输入/输出
- Token 消耗统计
- 响应时间分布
- 错误率
- 按用户/项目/时间筛选

---

#### Step 2：自建调用日志（4 小时）

**任务清单**：
- [ ] 用 SQLite/PostgreSQL 记录每次 LLM 调用
- [ ] 包含：时间、用户、模型、Token、延迟、状态
- [ ] 提供查询 API

**数据库设计**：
```sql
CREATE TABLE llm_calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id TEXT,
    session_id TEXT,
    model TEXT NOT NULL,
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    total_tokens INTEGER,
    cost_usd REAL,
    latency_ms INTEGER,
    status TEXT,  -- success / error
    error_message TEXT,
    request_json TEXT,
    response_json TEXT
);

CREATE INDEX idx_timestamp ON llm_calls(timestamp);
CREATE INDEX idx_user_id ON llm_calls(user_id);
CREATE INDEX idx_session_id ON llm_calls(session_id);
```

**Python 封装**：
```python
import sqlite3
import time
import json
from contextlib import contextmanager
from typing import Optional

# 模型定价（每 1M tokens）
# 注意：价格以官方最新定价为准，请定期参考 openai.com/pricing 和 anthropic.com/pricing
# 以下价格为文档编写时的参考值，实际使用时请校对更新
MODEL_PRICING = {
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4o": {"input": 2.50, "output": 10.00},  # 2024年已降价
    "claude-3-5-sonnet": {"input": 3.00, "output": 15.00},
    "claude-3-haiku": {"input": 0.25, "output": 1.25},
}
# 建议：生产环境通过 API 动态获取最新价格，而非硬编码

class LLMCallLogger:
    """LLM 调用日志记录器"""

    def __init__(self, db_path: str = "llm_logs.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """初始化数据库"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS llm_calls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    user_id TEXT,
                    session_id TEXT,
                    model TEXT NOT NULL,
                    prompt_tokens INTEGER,
                    completion_tokens INTEGER,
                    total_tokens INTEGER,
                    cost_usd REAL,
                    latency_ms INTEGER,
                    status TEXT,
                    error_message TEXT,
                    request_json TEXT,
                    response_json TEXT
                )
            """)

    def calculate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        """计算成本（美元）"""
        if model not in MODEL_PRICING:
            return 0.0
        pricing = MODEL_PRICING[model]
        cost = (prompt_tokens / 1_000_000) * pricing["input"] + \
               (completion_tokens / 1_000_000) * pricing["output"]
        return round(cost, 6)

    @contextmanager
    def log_call(self, model: str, user_id: str = None, session_id: str = None):
        """上下文管理器：自动记录 LLM 调用"""
        start_time = time.time()
        request_data = {}

        try:
            # 在这个上下文中执行 LLM 调用
            # 调用方需要 set request_data
            yield request_data
            status = "success"
            error_msg = None
        except Exception as e:
            status = "error"
            error_msg = str(e)
            raise
        finally:
            latency_ms = int((time.time() - start_time) * 1000)

            # 提取 token 信息
            prompt_tokens = request_data.get("prompt_tokens", 0)
            completion_tokens = request_data.get("completion_tokens", 0)
            total_tokens = prompt_tokens + completion_tokens

            # 计算成本
            cost = self.calculate_cost(model, prompt_tokens, completion_tokens)

            # 写入数据库
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO llm_calls
                    (user_id, session_id, model, prompt_tokens, completion_tokens,
                     total_tokens, cost_usd, latency_ms, status, error_message,
                     request_json, response_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_id, session_id, model,
                    prompt_tokens, completion_tokens, total_tokens,
                    cost, latency_ms, status, error_msg,
                    json.dumps(request_data.get("request", {})),
                    json.dumps(request_data.get("response", {}))
                ))

# 集成到 OpenAI 调用
class MonitoredOpenAIClient:
    """带监控的 OpenAI 客户端"""

    def __init__(self, logger: LLMCallLogger):
        from openai import OpenAI
        self.client = OpenAI()
        self.logger = logger

    def chat(self, messages, model="gpt-4o-mini", user_id=None, session_id=None, **kwargs):
        """调用 LLM 并自动记录"""
        with self.logger.log_call(model, user_id, session_id) as log_data:
            log_data["request"] = {"messages": messages, "model": model}

            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                **kwargs
            )

            # 记录响应
            log_data["response"] = {
                "content": response.choices[0].message.content
            }
            log_data["prompt_tokens"] = response.usage.prompt_tokens
            log_data["completion_tokens"] = response.usage.completion_tokens

            return response.choices[0].message.content

# 使用
logger = LLMCallLogger()
client = MonitoredOpenAIClient(logger)

response = client.chat(
    messages=[{"role": "user", "content": "Hello"}],
    user_id="user_001",
    session_id="session_abc"
)
# 自动记录到数据库
```
> 以上为 LLMCallLogger 核心实现。完整版本（含异步写入、连接池、批量写入优化）见 [技术架构建议书 - 第 5 节](./技术架构/02-讲解说明.md) 的扩展说明。

---

#### Step 3：构建成本 Dashboard（3 小时）

**任务清单**：
- [ ] 用 Streamlit 构建 Dashboard
- [ ] 展示总成本、每日成本、用户成本
- [ ] 图表展示（趋势、Top 用户、Top 模型）

**Streamlit Dashboard**：
```python
import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

st.set_page_config(page_title="LLM 成本监控", page_icon="💰")
st.title("💰 LLM 成本监控 Dashboard")

# 数据库查询
@st.cache_data(ttl=60)
def load_data():
    conn = sqlite3.connect("llm_logs.db")
    df = pd.read_sql("SELECT * FROM llm_calls", conn)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df

df = load_data()

# 侧边栏筛选
with st.sidebar:
    st.header("🔍 筛选")
    date_range = st.date_input(
        "时间范围",
        value=(datetime.now() - timedelta(days=7), datetime.now())
    )
    selected_models = st.multiselect(
        "模型",
        options=df['model'].unique(),
        default=df['model'].unique()
    )

# 应用筛选
df_filtered = df[
    (df['timestamp'].dt.date >= date_range[0]) &
    (df['timestamp'].dt.date <= date_range[1]) &
    (df['model'].isin(selected_models))
]

# ============ 核心指标 ============
st.header("📊 核心指标")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("总调用次数", f"{len(df_filtered):,}")

with col2:
    total_cost = df_filtered['cost_usd'].sum()
    st.metric("总成本", f"${total_cost:.2f}")

with col3:
    total_tokens = df_filtered['total_tokens'].sum()
    st.metric("总 Token", f"{total_tokens:,}")

with col4:
    avg_latency = df_filtered['latency_ms'].mean()
    st.metric("平均延迟", f"{avg_latency:.0f} ms")

# ============ 趋势图 ============
st.header("📈 成本趋势")
daily_stats = df_filtered.groupby(df_filtered['timestamp'].dt.date).agg({
    'cost_usd': 'sum',
    'total_tokens': 'sum',
    'id': 'count'
}).reset_index()

fig = px.line(
    daily_stats,
    x='timestamp',
    y='cost_usd',
    title='每日成本趋势',
    labels={'cost_usd': '成本 (USD)', 'timestamp': '日期'}
)
st.plotly_chart(fig, use_container_width=True)

# ============ Top 用户 ============
st.header("👥 Top 10 用户（按成本）")
user_stats = df_filtered.groupby('user_id').agg({
    'cost_usd': 'sum',
    'total_tokens': 'sum',
    'id': 'count'
}).sort_values('cost_usd', ascending=False).head(10)

st.dataframe(user_stats)

# ============ 模型分布 ============
st.header("🤖 模型分布")
model_stats = df_filtered.groupby('model').agg({
    'cost_usd': 'sum',
    'total_tokens': 'sum',
    'id': 'count'
}).reset_index()

fig = px.pie(
    model_stats,
    values='cost_usd',
    names='model',
    title='成本分布（按模型）'
)
st.plotly_chart(fig, use_container_width=True)

# ============ 错误率 ============
st.header("❌ 错误率")
error_rate = (df_filtered['status'] == 'error').mean() * 100
st.metric("错误率", f"{error_rate:.2f}%")

if error_rate > 5:
    st.error("⚠️ 错误率过高，请检查！")
elif error_rate > 1:
    st.warning("⚠️ 错误率偏高")
else:
    st.success("✅ 错误率正常")
```

---

#### Step 4：成本预警（2 小时）

**任务清单**：
- [ ] 设置成本阈值
- [ ] 超过阈值时发送告警
- [ ] 支持多种通知方式（邮件、Webhook、钉钉）

**实现**：
```python
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests

class CostAlerter:
    """成本告警器"""

    def __init__(self, daily_budget: float = 10.0, monthly_budget: float = 200.0):
        self.daily_budget = daily_budget
        self.monthly_budget = monthly_budget

    def check_budget(self):
        """检查预算并告警"""
        today_cost = self._get_today_cost()
        month_cost = self._get_month_cost()

        alerts = []

        if today_cost > self.daily_budget:
            alerts.append({
                "level": "critical",
                "message": f"今日成本 ${today_cost:.2f} 超过日预算 ${self.daily_budget}"
            })
        elif today_cost > self.daily_budget * 0.8:
            alerts.append({
                "level": "warning",
                "message": f"今日成本 ${today_cost:.2f} 已达日预算 80%"
            })

        if month_cost > self.monthly_budget:
            alerts.append({
                "level": "critical",
                "message": f"本月成本 ${month_cost:.2f} 超过月预算 ${self.monthly_budget}"
            })

        for alert in alerts:
            self._send_alert(alert)

    def _get_today_cost(self) -> float:
        """获取今日成本"""
        with sqlite3.connect("llm_logs.db") as conn:
            result = conn.execute("""
                SELECT COALESCE(SUM(cost_usd), 0)
                FROM llm_calls
                WHERE DATE(timestamp) = DATE('now')
            """).fetchone()
            return result[0]

    def _get_month_cost(self) -> float:
        """获取本月成本"""
        with sqlite3.connect("llm_logs.db") as conn:
            result = conn.execute("""
                SELECT COALESCE(SUM(cost_usd), 0)
                FROM llm_calls
                WHERE strftime('%Y-%m', timestamp) = strftime('%Y-%m', 'now')
            """).fetchone()
            return result[0]

    def _send_alert(self, alert: dict):
        """发送告警"""
        # 1. 邮件告警
        self._send_email(alert)

        # 2. Webhook 告警（钉钉/飞书/企业微信）
        self._send_webhook(alert)

    def _send_email(self, alert: dict):
        """发送邮件"""
        import os
        msg = MIMEText(f"[{alert['level'].upper()}] {alert['message']}")
        msg['Subject'] = f"LLM 成本告警 - {alert['level']}"
        msg['From'] = os.getenv("SMTP_FROM", "alerts@yourcompany.com")
        msg['To'] = os.getenv("SMTP_TO", "ops@yourcompany.com")

        # SMTP 配置（从环境变量读取）
        smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER")
        smtp_password = os.getenv("SMTP_PASSWORD")

        if smtp_user and smtp_password:
            smtp = smtplib.SMTP(smtp_host, smtp_port)
            smtp.starttls()
            smtp.login(smtp_user, smtp_password)
            smtp.send_message(msg)
            smtp.quit()

    def _send_webhook(self, alert: dict):
        """发送 Webhook（钉钉示例）"""
        webhook_url = "https://oapi.dingtalk.com/robot/send?access_token=..."

        payload = {
            "msgtype": "markdown",
            "markdown": {
                "title": f"LLM 成本告警 - {alert['level']}",
                "text": f"## ⚠️ 成本告警\n\n{alert['message']}"
            }
        }

        requests.post(webhook_url, json=payload)

# 定时检查（用 cron 或 APScheduler）
from apscheduler.schedulers.blocking import BlockingScheduler

alerter = CostAlerter(daily_budget=10.0, monthly_budget=200.0)

scheduler = BlockingScheduler()
scheduler.add_job(alerter.check_budget, 'cron', hour=9)  # 每天 9 点检查
scheduler.start()
```

---

### 3.2 挑战版任务（选做 2 个，6-8 小时）

#### 挑战 1：性能指标监控（P50/P95/P99 延迟）

**任务**：
- [ ] 计算延迟百分位数
- [ ] 用 Grafana 可视化
- [ ] 设置 SLA 告警

**实现**：
```python
import numpy as np

class LatencyAnalyzer:
    """延迟分析器"""

    def __init__(self, db_path: str = "llm_logs.db"):
        self.db_path = db_path

    def get_percentiles(self, time_range_hours: int = 24) -> dict:
        """获取延迟百分位数"""
        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql(f"""
                SELECT latency_ms
                FROM llm_calls
                WHERE timestamp >= datetime('now', '-{time_range_hours} hours')
                AND status = 'success'
            """, conn)

        if len(df) == 0:
            return {}

        return {
            "p50": np.percentile(df['latency_ms'], 50),
            "p75": np.percentile(df['latency_ms'], 75),
            "p90": np.percentile(df['latency_ms'], 90),
            "p95": np.percentile(df['latency_ms'], 95),
            "p99": np.percentile(df['latency_ms'], 99),
            "max": df['latency_ms'].max(),
            "min": df['latency_ms'].min(),
            "mean": df['latency_ms'].mean()
        }

# 使用
analyzer = LatencyAnalyzer()
percentiles = analyzer.get_percentiles(24)
print(f"P50: {percentiles['p50']:.0f}ms")
print(f"P95: {percentiles['p95']:.0f}ms")
print(f"P99: {percentiles['p99']:.0f}ms")
```

**Grafana 配置（docker-compose）**：
```yaml
prometheus:
  image: prom/prometheus
  volumes:
    - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml

# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'agent'
    static_configs:
      - targets: ['agent:8000']
```

---

#### 挑战 2：异常检测

**任务**：
- [ ] 自动识别异常调用（响应时间突增、错误率突增）
- [ ] 用统计方法（3-sigma）检测
- [ ] 异常时告警

**实现**：
```python
import numpy as np
from scipy import stats

class AnomalyDetector:
    """异常检测器"""

    def __init__(self, db_path: str = "llm_logs.db"):
        self.db_path = db_path

    def detect_latency_anomaly(self) -> list:
        """检测延迟异常"""
        with sqlite3.connect(self.db_path) as conn:
            # 获取过去 7 天的数据
            df = pd.read_sql("""
                SELECT
                    strftime('%H', timestamp) as hour,
                    AVG(latency_ms) as avg_latency
                FROM llm_calls
                WHERE timestamp >= datetime('now', '-7 days')
                AND status = 'success'
                GROUP BY hour
            """, conn)

        if len(df) < 24:
            return []

        # 计算 z-score
        mean = df['avg_latency'].mean()
        std = df['avg_latency'].std()
        df['z_score'] = np.abs(stats.zscore(df['avg_latency']))

        # z-score > 3 视为异常
        anomalies = df[df['z_score'] > 3]

        return anomalies.to_dict('records')

    def detect_error_rate_anomaly(self) -> list:
        """检测错误率异常"""
        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql("""
                SELECT
                    DATE(timestamp) as date,
                    SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) * 1.0 /
                    COUNT(*) as error_rate
                FROM llm_calls
                WHERE timestamp >= datetime('now', '-30 days')
                GROUP BY date
            """, conn)

        if len(df) < 7:
            return []

        mean = df['error_rate'].mean()
        std = df['error_rate'].std()
        df['z_score'] = np.abs((df['error_rate'] - mean) / std)

        anomalies = df[df['z_score'] > 2]

        return anomalies.to_dict('records')
```

---

#### 挑战 3：用户行为分析

**任务**：
- [ ] 分析哪些功能最常用
- [ ] 用户活跃时段
- [ ] 用户留存率

**实现**：
```python
class UserBehaviorAnalyzer:
    """用户行为分析"""

    def __init__(self, db_path: str = "llm_logs.db"):
        self.db_path = db_path

    def get_most_used_features(self) -> pd.DataFrame:
        """最常用功能"""
        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql("""
                SELECT
                    user_id,
                    COUNT(*) as call_count,
                    SUM(cost_usd) as total_cost,
                    AVG(latency_ms) as avg_latency
                FROM llm_calls
                GROUP BY user_id
                ORDER BY call_count DESC
            """, conn)
        return df

    def get_active_hours(self) -> pd.DataFrame:
        """活跃时段"""
        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql("""
                SELECT
                    strftime('%H', timestamp) as hour,
                    COUNT(*) as call_count
                FROM llm_calls
                GROUP BY hour
                ORDER BY hour
            """, conn)
        return df

    def get_user_retention(self) -> pd.DataFrame:
        """用户留存率"""
        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql("""
                WITH first_use AS (
                    SELECT user_id, MIN(DATE(timestamp)) as first_date
                    FROM llm_calls
                    GROUP BY user_id
                ),
                daily_active AS (
                    SELECT DISTINCT user_id, DATE(timestamp) as active_date
                    FROM llm_calls
                )
                SELECT
                    fu.first_date,
                    da.active_date,
                    julianday(da.active_date) - julianday(fu.first_date) as days_since_signup,
                    COUNT(DISTINCT da.user_id) as active_users
                FROM first_use fu
                JOIN daily_active da ON fu.user_id = da.user_id
                GROUP BY fu.first_date, da.active_date
            """, conn)
        return df
```

---

#### 挑战 4：Token 优化建议

**任务**：
- [ ] 分析哪些 Prompt 最耗 Token
- [ ] 提供优化建议
- [ ] 优化前后对比

**实现**：
```python
class TokenOptimizer:
    """Token 优化器"""

    def find_wasteful_calls(self, threshold: int = 5000) -> pd.DataFrame:
        """找出 Token 消耗过高的调用"""
        with sqlite3.connect("llm_logs.db") as conn:
            df = pd.read_sql(f"""
                SELECT
                    id,
                    model,
                    prompt_tokens,
                    completion_tokens,
                    total_tokens,
                    cost_usd,
                    timestamp
                FROM llm_calls
                WHERE total_tokens > {threshold}
                ORDER BY total_tokens DESC
            """, conn)
        return df

    def suggest_optimizations(self) -> list:
        """优化建议"""
        df = self.find_wasteful_calls()
        suggestions = []

        # 建议 1：减少 Prompt 长度
        high_prompt = df[df['prompt_tokens'] > 3000]
        if len(high_prompt) > 0:
            suggestions.append({
                "type": "prompt_too_long",
                "count": len(high_prompt),
                "potential_savings": high_prompt['cost_usd'].sum() * 0.3,
                "suggestion": "考虑摘要上下文或使用 RAG 减少 Prompt 长度"
            })

        # 建议 2：使用更便宜的模型
        expensive_models = df[df['model'].isin(['gpt-4o', 'claude-3-5-sonnet'])]
        if len(expensive_models) > 0:
            suggestions.append({
                "type": "expensive_model",
                "count": len(expensive_models),
                "potential_savings": expensive_models['cost_usd'].sum() * 0.8,
                "suggestion": "对于简单任务，可使用 gpt-4o-mini 替代 gpt-4o"
            })

        return suggestions
```

---

#### 挑战 5：实时告警（Webhook 集成）

**任务**：
- [ ] 集成钉钉/飞书/Slack Webhook
- [ ] 支持多种告警级别
- [ ] 告警去重（同一问题不重复告警）

**实现**：
```python
class WebhookAlerter:
    """Webhook 告警器"""

    def __init__(self):
        self.alert_history = {}  # 用于去重

    def send(self, alert: dict, platform: str = "dingtalk"):
        """发送告警"""
        # 去重检查（5 分钟内相同告警只发一次）
        alert_key = f"{alert['level']}:{alert['message'][:50]}"
        if alert_key in self.alert_history:
            if time.time() - self.alert_history[alert_key] < 300:
                return  # 5 分钟内不重复

        self.alert_history[alert_key] = time.time()

        if platform == "dingtalk":
            self._send_dingtalk(alert)
        elif platform == "feishu":
            self._send_feishu(alert)
        elif platform == "slack":
            self._send_slack(alert)

    def _send_dingtalk(self, alert: dict):
        """钉钉"""
        url = "https://oapi.dingtalk.com/robot/send?access_token=..."
        emoji = "🔴" if alert['level'] == 'critical' else "🟡"

        payload = {
            "msgtype": "markdown",
            "markdown": {
                "title": f"{emoji} LLM 告警",
                "text": f"## {emoji} {alert['level'].upper()}\n\n{alert['message']}\n\n时间：{datetime.now()}"
            }
        }
        requests.post(url, json=payload)

    def _send_feishu(self, alert: dict):
        """飞书"""
        url = "https://open.feishu.cn/open-apis/bot/v2/hook/..."
        payload = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {
                        "content": f"LLM 告警 - {alert['level']}"
                    }
                },
                "elements": [{
                    "tag": "markdown",
                    "content": alert['message']
                }]
            }
        }
        requests.post(url, json=payload)
```

---

## 四、踩坑经验汇总

### 坑 1：Token 计算不准确

**现象**：监控显示的成本和实际账单对不上  
**原因**：不同模型的计费方式不同（有的按字符，有的按 Token）  
**解决**：
- 用官方 API 返回的 `usage` 字段
- 定期对账
- 加上 ±10% 的误差容忍

### 坑 2：日志写入成为瓶颈

**现象**：高频调用时，写日志拖慢系统  
**解决**：
- 异步写入（用队列）
- 批量写入
- 用更快的存储（PostgreSQL 替代 SQLite）

```python
import asyncio
from asyncio import Queue

class AsyncLogger:
    """异步日志记录器"""

    def __init__(self):
        self.queue = Queue()

    async def writer(self):
        """后台写入协程"""
        while True:
            batch = []
            for _ in range(100):  # 批量 100 条
                try:
                    item = await asyncio.wait_for(self.queue.get(), timeout=1)
                    batch.append(item)
                except asyncio.TimeoutError:
                    break

            if batch:
                # 批量写入数据库
                await self._batch_insert(batch)

    async def log(self, data):
        """异步记录"""
        await self.queue.put(data)
```

### 坑 3：监控本身消耗资源

**现象**：监控组件占用了大量 CPU/内存  
**解决**：
- 采样（不是每次调用都记录，而是 10% 采样）
- 分级（DEBUG 级别不记录）

### 坑 4：告警风暴

**现象**：一个问题导致几百条告警轰炸  
**解决**：
- 告警去重
- 告警聚合（5 分钟内的同类告警合并为一条）
- 告警分级

### 坑 5：监控数据丢失

**现象**：数据库损坏，所有历史数据没了  
**解决**：
- 定期备份
- 关键数据同步到云存储
- 启用 WAL 模式

---

## 五、评估标准详解

### 及格（60 分）

- [ ] 接入 LangSmith 或自建日志
- [ ] 能看到每次 LLM 调用的 Token 和成本
- [ ] 基本的 Dashboard
- [ ] 代码可运行

### 良好（75 分）

在及格基础上：
- [ ] 成本预警机制
- [ ] 多种通知方式（邮件/Webhook）
- [ ] 错误率监控
- [ ] 延迟监控

### 优秀（90 分）

在良好基础上：
- [ ] 完成了至少 3 个挑战任务
- [ ] 异常检测
- [ ] 用户行为分析
- [ ] Token 优化建议
- [ ] 有完整的技术博客讲解可观测性

---

## 六、监控的最佳实践

### 6.1 必须监控的指标

**黄金信号（Golden Signals）**：
- **延迟**（Latency）：响应时间
- **流量**（Traffic）：调用次数
- **错误**（Errors）：失败率
- **饱和度**（Saturation）：资源使用率

**Agent 系统特有**：
- Token 消耗（输入/输出）
- 成本（按用户/按时间）
- 工具调用成功率
- Agent 循环次数
- 幻觉率（答案与上下文的匹配度）

### 6.2 告警设计原则

- **告警必须 actionable**：收到告警后能采取行动
- **分级处理**：Critical（立即处理）/ Warning（关注）/ Info（了解）
- **避免告警疲劳**：重要告警才能叫醒人
- **提供上下文**：告警要包含足够信息（哪个用户、什么时间、具体错误）

### 6.3 SLO 设计

| 指标 | 目标 SLO |
|------|----------|
| 可用性 | 99.9%（每月停机 < 43 分钟）|
| P95 延迟 | < 5 秒 |
| 错误率 | < 1% |
| 成本 | 单次任务 < $0.1 |

### 6.4 测试场景概览（30 个）
> 完整测试场景见技术架构建议书第 10 节。以下为场景类别：

| 类别 | 场景数 | 说明 |
|------|--------|------|
| LLM 调用追踪 | 6 | Token 统计、成本计算、模型切换追踪、多轮对话追踪、工具调用链、流式调用 |
| 系统指标监控 | 6 | CPU/内存/磁盘使用率、请求 QPS、并发连接数、响应时间分布、GC 耗时 |
| 告警机制 | 5 | 成本阈值告警、错误率告警、延迟告警、告警聚合、多渠道通知 |
| 成本优化 | 5 | 缓存命中率、模型路由效果、Prompt 压缩效果、月度成本趋势、分用户成本 |
| Dashboard | 5 | 核心指标面板、成本分析面板、性能面板、用户面板、告警历史面板 |
| 数据持久化 | 3 | 数据库写入、查询性能、数据清理策略 |

---

## 七、交付物清单

- [ ] **代码仓库**（GitHub）
  - LLMCallLogger
  - Dashboard 代码
  - 告警配置
  - README.md
- [ ] **Dashboard 截图/链接**
- [ ] **成本优化报告**
  - 当前成本分析
  - 优化建议
  - 预期节省
- [ ] **技术博客**（可选，2000 字）
  - 可观测性三大支柱
  - Agent 系统监控挑战
  - 实战经验

---

**下一步**：完成本项目后，进入 [项目 9：安全与评估](../项目9-安全与评估/README.md)
