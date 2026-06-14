"""
Prometheus 指标采集 - 智能体工程师培养计划 项目 8
定义和采集 Prometheus 指标
"""

from typing import Optional, Dict
from prometheus_client import Counter, Gauge, Histogram, Info, start_http_server
import time
import logging
import os

# ============================================================
# 日志配置
# ============================================================
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================
# 指标定义
# ============================================================

# ============ LLM 调用指标 ============
llm_call_total = Counter(
    "llm_call_total",
    "Total LLM API calls",
    ["model", "status", "user_id"]
)

token_consumed_total = Counter(
    "token_consumed_total",
    "Total tokens consumed",
    ["model", "token_type"]  # token_type: input / output
)

llm_cost_usd_total = Counter(
    "llm_cost_usd_total",
    "Total LLM cost in USD",
    ["model", "user_id"]
)

llm_call_duration_seconds = Histogram(
    "llm_call_duration_seconds",
    "LLM call latency in seconds",
    ["model"],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
)

llm_active_requests = Gauge(
    "llm_active_requests",
    "Currently active LLM requests",
    ["model"]
)

# ============ 工具调用指标 ============
tool_call_total = Counter(
    "tool_call_total",
    "Total tool calls",
    ["tool_name", "status"]
)

tool_call_duration_seconds = Histogram(
    "tool_call_duration_seconds",
    "Tool call latency in seconds",
    ["tool_name"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
)

tool_error_total = Counter(
    "tool_error_total",
    "Total tool errors",
    ["tool_name", "error_type"]
)

# ============ Agent 运行指标 ============
agent_run_total = Counter(
    "agent_run_total",
    "Total agent runs",
    ["status"]  # status: success / error / timeout
)

agent_run_duration_seconds = Histogram(
    "agent_run_duration_seconds",
    "Agent run latency in seconds",
    buckets=[1.0, 3.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0]
)

agent_iteration_count = Histogram(
    "agent_iteration_count",
    "Number of iterations per agent run",
    buckets=[1, 2, 3, 5, 10, 15, 20]
)

agent_active_runs = Gauge(
    "agent_active_runs",
    "Currently active agent runs"
)

# ============ 成本指标 ============
cost_hourly_usd = Gauge(
    "cost_hourly_usd",
    "Hourly cost in USD"
)

cost_daily_usd = Gauge(
    "cost_daily_usd",
    "Daily cost in USD by user",
    ["user_id"]
)

budget_usage_ratio = Gauge(
    "budget_usage_ratio",
    "Budget usage ratio (0.0 - 1.0)",
    ["user_id", "budget_type"]  # budget_type: daily / monthly
)

# ============ 系统指标 ============
request_queue_size = Gauge(
    "request_queue_size",
    "Request queue size"
)

active_sessions = Gauge(
    "active_sessions",
    "Number of active sessions"
)

db_connection_pool_size = Gauge(
    "db_connection_pool_size",
    "Database connection pool size",
    ["pool_name"]
)

log_write_queue_size = Gauge(
    "log_write_queue_size",
    "Log write queue size"
)

error_rate_percent = Gauge(
    "error_rate_percent",
    "Error rate percentage",
    ["model"]
)

# ============ 自定义业务指标 ============
user_satisfaction_score = Gauge(
    "user_satisfaction_score",
    "User satisfaction score (0-5)",
    ["user_id"]
)

rag_retrieval_recall = Gauge(
    "rag_retrieval_recall",
    "RAG retrieval recall score (0.0-1.0)"
)

hallucination_detected_total = Counter(
    "hallucination_detected_total",
    "Total hallucination detections",
    ["model"]
)

# ============ 应用信息 ============
app_info = Info("agent_app", "Application info")

# ============================================================
# 指标更新函数
# ============================================================

def record_llm_call(
    model: str,
    status: str,
    user_id: str,
    prompt_tokens: int,
    completion_tokens: int,
    cost_usd: float,
    latency_seconds: float
):
    """记录 LLM 调用指标
    
    Args:
        model: 模型名称
        status: 状态（success / error / timeout）
        user_id: 用户 ID
        prompt_tokens: 输入 Token 数
        completion_tokens: 输出 Token 数
        cost_usd: 成本（美元）
        latency_seconds: 延迟（秒）
    """
    # Counter: LLM 调用总数
    llm_call_total.labels(model=model, status=status, user_id=user_id).inc()
    
    # Counter: Token 消耗
    token_consumed_total.labels(model=model, token_type="input").inc(prompt_tokens)
    token_consumed_total.labels(model=model, token_type="output").inc(completion_tokens)
    
    # Counter: 成本
    llm_cost_usd_total.labels(model=model, user_id=user_id).inc(cost_usd)
    
    # Histogram: 延迟
    llm_call_duration_seconds.labels(model=model).observe(latency_seconds)
    
    logger.debug(f"LLM 调用指标已记录: model={model}, status={status}, cost=${cost_usd:.6f}")

def record_tool_call(
    tool_name: str,
    status: str,
    latency_seconds: float,
    error_type: Optional[str] = None
):
    """记录工具调用指标
    
    Args:
        tool_name: 工具名称
        status: 状态（success / error）
        latency_seconds: 延迟（秒）
        error_type: 错误类型（可选）
    """
    # Counter: 工具调用总数
    tool_call_total.labels(tool_name=tool_name, status=status).inc()
    
    # Histogram: 延迟
    tool_call_duration_seconds.labels(tool_name=tool_name).observe(latency_seconds)
    
    # Counter: 错误
    if status == "error" and error_type:
        tool_error_total.labels(tool_name=tool_name, error_type=error_type).inc()
    
    logger.debug(f"工具调用指标已记录: tool={tool_name}, status={status}")

def record_agent_run(
    status: str,
    latency_seconds: float,
    num_iterations: int
):
    """记录 Agent 运行指标
    
    Args:
        status: 状态（success / error / timeout）
        latency_seconds: 延迟（秒）
        num_iterations: 迭代次数
    """
    # Counter: Agent 运行总数
    agent_run_total.labels(status=status).inc()
    
    # Histogram: 延迟
    agent_run_duration_seconds.observe(latency_seconds)
    
    # Histogram: 迭代次数
    agent_iteration_count.observe(num_iterations)
    
    logger.debug(f"Agent 运行指标已记录: status={status}, iterations={num_iterations}")

def set_active_requests(model: str, count: int):
    """设置当前活跃请求数
    
    Args:
        model: 模型名称
        count: 活跃请求数
    """
    llm_active_requests.labels(model=model).set(count)

def set_active_runs(count: int):
    """设置当前活跃 Agent 运行数
    
    Args:
        count: 活跃运行数
    """
    agent_active_runs.set(count)

def update_cost_metrics(hourly_cost: float, daily_costs: Dict[str, float]):
    """更新成本指标
    
    Args:
        hourly_cost: 每小时成本
        daily_costs: 每日成本（按用户分组）
    """
    cost_hourly_usd.set(hourly_cost)
    
    for user_id, cost in daily_costs.items():
        cost_daily_usd.labels(user_id=user_id).set(cost)

def update_budget_metrics(
    user_id: str,
    daily_budget: float,
    monthly_budget: float
):
    """更新预算使用率指标
    
    Args:
        user_id: 用户 ID
        daily_budget: 日预算（美元）
        monthly_budget: 月预算（美元）
    """
    # 这里需要从数据库查询实际使用情况
    # 示例：假设已使用 50%
    daily_usage = 0.5
    monthly_usage = 0.3
    
    budget_usage_ratio.labels(user_id=user_id, budget_type="daily").set(daily_usage)
    budget_usage_ratio.labels(user_id=user_id, budget_type="monthly").set(monthly_usage)

def update_error_rate(model: str, error_rate: float):
    """更新错误率指标
    
    Args:
        model: 模型名称
        error_rate: 错误率（0.0 - 1.0）
    """
    error_rate_percent.labels(model=model).set(error_rate * 100)

def set_app_info(version: str, model: str, environment: str):
    """设置应用信息
    
    Args:
        version: 应用版本
        model: 模型名称
        environment: 环境（development / staging / production）
    """
    app_info.info({
        "version": version,
        "model": model,
        "environment": environment
    })

# ============================================================
# 指标服务器
# ============================================================
def start_metrics_server(port: int = 8001):
    """启动 Prometheus 指标服务器
    
    Args:
        port: 端口号（默认 8001）
    """
    start_http_server(port)
    logger.info(f"Prometheus 指标服务器已启动，端口: {port}")
    logger.info(f"指标端点: http://localhost:{port}/metrics")

# ============================================================
# 监控装饰器
# ============================================================
def monitor_llm_call(model: str, user_id: str = "anonymous"):
    """监控 LLM 调用的装饰器
    
    Args:
        model: 模型名称
        user_id: 用户 ID
        
    Returns:
        装饰器函数
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            set_active_requests(model, 1)
            
            try:
                result = func(*args, **kwargs)
                latency = time.time() - start_time
                
                # 记录成功指标
                record_llm_call(
                    model=model,
                    status="success",
                    user_id=user_id,
                    prompt_tokens=0,  # 需要从结果中提取
                    completion_tokens=0,
                    cost_usd=0.0,
                    latency_seconds=latency
                )
                
                return result
            except Exception as e:
                latency = time.time() - start_time
                
                # 记录错误指标
                record_llm_call(
                    model=model,
                    status="error",
                    user_id=user_id,
                    prompt_tokens=0,
                    completion_tokens=0,
                    cost_usd=0.0,
                    latency_seconds=latency
                )
                
                raise
            finally:
                set_active_requests(model, -1)
        
        return wrapper
    return decorator

# ============================================================
# 使用示例
# ============================================================
if __name__ == "__main__":
    # 设置应用信息
    set_app_info(version="1.0.0", model="gpt-4o-mini", environment="development")
    
    # 启动指标服务器
    start_metrics_server(port=8001)
    
    # 模拟指标更新
    record_llm_call(
        model="gpt-4o-mini",
        status="success",
        user_id="user_001",
        prompt_tokens=150,
        completion_tokens=280,
        cost_usd=0.003,
        latency_seconds=1.2
    )
    
    record_tool_call(
        tool_name="search_web",
        status="success",
        latency_seconds=0.5
    )
    
    record_agent_run(
        status="success",
        latency_seconds=3.5,
        num_iterations=3
    )
    
    print(f"指标服务器已启动，访问 http://localhost:8001/metrics 查看指标")
    
    # 保持运行
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("指标服务器已停止")
