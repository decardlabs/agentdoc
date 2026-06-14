"""
告警规则 - 智能体工程师培养计划 项目 8
定义 Prometheus 告警规则和 AlertManager 配置
"""

# ============================================================
# Prometheus 告警规则
# 用途：定义告警条件和通知方式
# ============================================================

alert_rules = """
groups:
  - name: agent_alerts
    rules:
      # 规则 1: 错误率超过 5%
      - alert: HighErrorRate
        expr: |
          sum(rate(llm_call_total{status="error"}[5m]))
          / sum(rate(llm_call_total[5m])) > 0.05
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "LLM 错误率过高"
          description: "当前错误率 {{ $value | humanizePercentage }}，超过 5% 阈值"

      # 规则 2: P95 延迟超过 10s
      - alert: HighLatencyP95
        expr: |
          histogram_quantile(0.95, rate(llm_call_duration_seconds_bucket[5m])) > 10
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "LLM P95 延迟过高"
          description: "当前 P95 延迟 {{ $value }}s，模型 {{ $labels.model }}"

      # 规则 3: 每小时成本超过阈值
      - alert: HourlyCostExceeded
        expr: |
          sum(rate(token_consumed_total{token_type="output"}[1h])) * 3600 > 100000
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "每小时 Token 消耗异常"
          description: "每小时输出 Token 达到 {{ $value }}，请检查是否有异常调用"

      # 规则 4: 单用户调用频率异常
      - alert: UserRateAnomaly
        expr: |
          sum by (user_id) (rate(llm_call_total[5m])) > 10
        for: 3m
        labels:
          severity: warning
        annotations:
          summary: "用户调用频率异常"
          description: "用户 {{ $labels.user_id }} 每秒 {{ $value }} 次调用"

      # 规则 5: 工具调用失败率超过 10%
      - alert: ToolFailureRate
        expr: |
          sum(rate(tool_call_total{status="error"}[5m]))
          / sum(rate(tool_call_total[5m])) > 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "工具调用失败率过高"
          description: "当前失败率 {{ $value | humanizePercentage }}，工具：{{ $labels.tool_name }}"

      # 规则 6: Agent 运行失败率超过 10%
      - alert: AgentFailureRate
        expr: |
          sum(rate(agent_run_total{status="error"}[5m]))
          / sum(rate(agent_run_total[5m])) > 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Agent 运行失败率过高"
          description: "当前失败率 {{ $value | humanizePercentage }}"

      # 规则 7: 日预算即将耗尽（80%）
      - alert: DailyBudgetWarning
        expr: |
          budget_usage_ratio{user_id="global", budget_type="daily"} > 0.8
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "日预算即将耗尽"
          description: "当前日预算使用率 {{ $value | humanizePercentage }}"

      # 规则 8: 日预算已耗尽（100%）
      - alert: DailyBudgetExceeded
        expr: |
          budget_usage_ratio{user_id="global", budget_type="daily"} >= 1.0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "日预算已耗尽"
          description: "当前日预算使用率 {{ $value | humanizePercentage }}，已停止服务"

      # 规则 9: 用户日预算已耗尽
      - alert: UserDailyBudgetExceeded
        expr: |
          budget_usage_ratio{budget_type="daily"} >= 1.0
          and on(user_id) user_id != "global"
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "用户 {{ $labels.user_id }} 日预算已耗尽"
          description: "当前预算使用率 {{ $value | humanizePercentage }}"

      # 规则 10: 服务不可用
      - alert: ServiceDown
        expr: |
          up{job="agent-service"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Agent 服务不可用"
          description: "服务 {{ $labels.instance }} 已下线超过 1 分钟"
"""

# ============================================================
# AlertManager 配置
# 用途：配置告警通知渠道和路由规则
# ============================================================

alertmanager_config = """
global:
  resolve_timeout: 5m
  smtp_smarthost: 'smtp.gmail.com:587'
  smtp_from: 'alerts@your-domain.com'
  smtp_auth_username: 'alerts@your-domain.com'
  smtp_auth_password: 'your-app-password'

route:
  receiver: "dingtalk"
  group_by: ["alertname", "model"]
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 1h

  routes:
    - match:
        severity: critical
      receiver: "dingtalk"
      repeat_interval: 10m

    - match:
        severity: warning
      receiver: "feishu"
      repeat_interval: 30m

receivers:
  - name: "dingtalk"
    webhook_configs:
      - url: "http://webhook-adapter:8080/dingtalk"
        send_resolved: true

  - name: "feishu"
    webhook_configs:
      - url: "http://webhook-adapter:8080/feishu"
        send_resolved: true

  - name: "email"
    email_configs:
      - to: "admin@your-domain.com"
        send_resolved: true

templates:
  - "/etc/alertmanager/templates/*.tmpl"
"""

# ============================================================
# 告警管理器
# 用途：Python 端告警逻辑（补充 Prometheus 规则覆盖不到的场景）
# ============================================================

class AlertManager:
    """告警管理器 - 补充 Prometheus 规则覆盖不到的业务级告警"""

    def __init__(
        self,
        daily_budget: float = 10.0,
        monthly_budget: float = 200.0,
        user_daily_budget: float = 2.0
    ):
        """初始化告警管理器

        Args:
            daily_budget: 全局日预算（美元）
            monthly_budget: 全局月预算（美元）
            user_daily_budget: 用户日预算（美元）
        """
        self.daily_budget = daily_budget
        self.monthly_budget = monthly_budget
        self.user_daily_budget = user_daily_budget
        self._alert_cache = {}  # 告警去重缓存

    def check_and_alert(self, user_id: str, current_cost: float):
        """每次调用后检查预算

        Args:
            user_id: 用户 ID
            current_cost: 当前调用成本
        """
        import time
        alerts = []

        # 全局日预算
        today_total = self._get_today_total_cost()
        if today_total > self.daily_budget:
            alerts.append(("critical", f"全局日预算已超: ${today_total:.2f} / ${self.daily_budget:.2f}"))
        elif today_total > self.daily_budget * 0.8:
            alerts.append(("warning", f"全局日预算 80%: ${today_total:.2f} / ${self.daily_budget:.2f}"))

        # 用户日预算
        user_today = self._get_user_today_cost(user_id)
        if user_today > self.user_daily_budget:
            alerts.append(("critical", f"用户 {user_id} 日预算已超: ${user_today:.2f} / ${self.user_daily_budget:.2f}"))

        # 发送告警（带去重）
        for level, msg in alerts:
            key = f"{level}:{msg[:50]}"
            if key in self._alert_cache and time.time() - self._alert_cache[key] < 300:
                continue  # 5 分钟内不重复
            self._alert_cache[key] = time.time()
            self._send_alert(level, msg)

    def _get_today_total_cost(self) -> float:
        """获取今日总成本"""
        import sqlite3
        try:
            with sqlite3.connect("llm_logs.db") as conn:
                result = conn.execute("""
                    SELECT COALESCE(SUM(cost_usd), 0)
                    FROM cost_records
                    WHERE DATE(timestamp) = DATE('now')
                    AND status = 'success'
                """).fetchone()
                return result[0]
        except Exception:
            return 0.0

    def _get_user_today_cost(self, user_id: str) -> float:
        """获取用户今日成本"""
        import sqlite3
        try:
            with sqlite3.connect("llm_logs.db") as conn:
                result = conn.execute("""
                    SELECT COALESCE(SUM(cost_usd), 0)
                    FROM cost_records
                    WHERE user_id = ?
                    AND DATE(timestamp) = DATE('now')
                    AND status = 'success'
                """, (user_id,)).fetchone()
                return result[0]
        except Exception:
            return 0.0

    def _send_alert(self, level: str, message: str):
        """发送告警到钉钉/飞书

        Args:
            level: 告警级别（critical / warning）
            message: 告警消息
        """
        import requests
        from datetime import datetime

        webhook_url = "https://oapi.dingtalk.com/robot/send?access_token=YOUR_TOKEN"

        payload = {
            "msgtype": "markdown",
            "markdown": {
                "title": f"[{level.upper()}] Agent 成本告警",
                "text": f"## {level.upper()}\n\n{message}\n\n时间: {datetime.now()}"
            }
        }

        try:
            requests.post(webhook_url, json=payload, timeout=5)
        except Exception:
            pass  # 告警发送失败不能影响业务


# ============================================================
# 导出配置
# ============================================================

def save_alert_rules(path: str = "prometheus/alert_rules.yml"):
    """保存告警规则到文件

    Args:
        path: 文件路径
    """
    import os
    os.makedirs(os.path.dirname(path), exist_ok=True)

    with open(path, "w") as f:
        f.write(alert_rules)
    print(f"告警规则已保存到: {path}")

def save_alertmanager_config(path: str = "prometheus/alertmanager.yml"):
    """保存 AlertManager 配置到文件

    Args:
        path: 文件路径
    """
    import os
    os.makedirs(os.path.dirname(path), exist_ok=True)

    with open(path, "w") as f:
        f.write(alertmanager_config)
    print(f"AlertManager 配置已保存到: {path}")


# ============================================================
# 使用示例
# ============================================================
if __name__ == "__main__":
    # 保存配置
    save_alert_rules()
    save_alertmanager_config()

    # 测试告警管理器
    alert_mgr = AlertManager(
        daily_budget=10.0,
        monthly_budget=200.0,
        user_daily_budget=2.0
    )

    # 模拟检查
    alert_mgr.check_and_alert("user_001", 0.005)
    print("告警规则生成完成")
