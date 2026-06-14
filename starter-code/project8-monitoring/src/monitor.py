"""
监控模块 - 智能体工程师培养计划 项目 8
集成 LangSmith 进行 LLM 调用追踪和监控
"""

from typing import Optional, Dict, Any, List
import os
import logging
from datetime import datetime
import json

# ============================================================
# 日志配置
# ============================================================
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================
# LangSmith 集成
# ============================================================

class LangSmithMonitor:
    """LangSmith 监控器 - 追踪 LLM 调用
    
    功能：
    - 自动追踪所有 LLM 调用
    - 记录输入、输出、延迟、Token 使用
    - 支持多 Span 嵌套（追踪完整调用链）
    """
    
    def __init__(self, enabled: bool = True, project_name: str = "agent-monitoring"):
        """初始化 LangSmith 监控器
        
        Args:
            enabled: 是否启用 LangSmith 追踪
            project_name: LangSmith 项目名称
        """
        self.enabled = enabled
        self.project_name = project_name
        
        if self.enabled:
            # 检查环境变量
            api_key = os.getenv("LANGCHAIN_API_KEY")
            if not api_key:
                logger.warning("LANGCHAIN_API_KEY 未设置，LangSmith 追踪将禁用")
                self.enabled = False
            else:
                # 设置 LangSmith 环境变量
                os.environ["LANGCHAIN_TRACING_V2"] = "true"
                os.environ["LANGCHAIN_PROJECT"] = self.project_name
                logger.info(f"LangSmith 监控已启用，项目：{project_name}")
    
    def trace_llm_call(self, func):
        """装饰器：追踪 LLM 调用
        
        Args:
            func: 要追踪的函数
            
        Returns:
            包装后的函数
        """
        if not self.enabled:
            return func
        
        try:
            from langsmith.run_helpers import traceable
            
            @traceable(run_type="llm", name=func.__name__)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            
            return wrapper
        except ImportError:
            logger.warning("langsmith 未安装，无法使用追踪装饰器")
            return func
    
    def trace_chain(self, func):
        """装饰器：追踪 Agent 调用链
        
        Args:
            func: 要追踪的函数
            
        Returns:
            包装后的函数
        """
        if not self.enabled:
            return func
        
        try:
            from langsmith.run_helpers import traceable
            
            @traceable(run_type="chain", name=func.__name__)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            
            return wrapper
        except ImportError:
            logger.warning("langsmith 未安装，无法使用追踪装饰器")
            return func
    
    def trace_tool(self, func):
        """装饰器：追踪工具调用
        
        Args:
            func: 要追踪的函数
            
        Returns:
            包装后的函数
        """
        if not self.enabled:
            return func
        
        try:
            from langsmith.run_helpers import traceable
            
            @traceable(run_type="tool", name=func.__name__)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            
            return wrapper
        except ImportError:
            logger.warning("langsmith 未安装，无法使用追踪装饰器")
            return func


# ============================================================
# OpenTelemetry 集成（可选，用于标准化追踪）
# ============================================================

class OTelMonitor:
    """OpenTelemetry 监控器 - 标准化追踪
    
    功能：
    - 使用 OTel 标准进行追踪
    - 可以导出到 Jaeger、Tempo 等后端
    - 与 LangSmith 可以同时使用
    """
    
    def __init__(self, enabled: bool = False, service_name: str = "agent-service"):
        """初始化 OTel 监控器
        
        Args:
            enabled: 是否启用 OTel 追踪
            service_name: 服务名称
        """
        self.enabled = enabled
        self.service_name = service_name
        
        if self.enabled:
            try:
                from opentelemetry import trace
                from opentelemetry.sdk.trace import TracerProvider
                from opentelemetry.sdk.trace.export import BatchSpanProcessor
                from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
                
                # 初始化 TracerProvider
                provider = TracerProvider()
                processor = BatchSpanProcessor(
                    OTLPSpanExporter(endpoint="http://localhost:4317")
                )
                provider.add_span_processor(processor)
                trace.set_tracer_provider(provider)
                
                self.tracer = trace.get_tracer(self.service_name)
                logger.info(f"OTel 监控已启用，服务：{service_name}")
                
            except ImportError:
                logger.warning("opentelemetry 未安装，OTel 追踪将禁用")
                self.enabled = False
    
    def start_span(self, span_name: str, attributes: Optional[Dict[str, Any]] = None):
        """开始一个新的 Span
        
        Args:
            span_name: Span 名称
            attributes: Span 属性（可选）
            
        Returns:
            Span 上下文管理器
        """
        if not self.enabled:
            # 返回空上下文管理器
            from contextlib import nullcontext
            return nullcontext()
        
        return self.tracer.start_as_current_span(span_name, attributes=attributes)


# ============================================================
# 日志监控
# ============================================================

class MonitoringLogger:
    """监控日志器 - 结构化日志输出
    
    功能：
    - 输出 JSON 格式的 structured logs
    - 包含调用 ID、用户 ID、模型、延迟、成本等字段
    - 便于后续使用 ELK、Grafana Loki 等工具查询
    """
    
    def __init__(self, name: str = "agent-monitor"):
        """初始化监控日志器
        
        Args:
            name: 日志器名称
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))
    
    def log_llm_call(
        self,
        call_id: str,
        user_id: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost_usd: float,
        latency_ms: int,
        status: str,
        error_message: Optional[str] = None
    ):
        """记录 LLM 调用日志
        
        Args:
            call_id: 调用 ID
            user_id: 用户 ID
            model: 模型名称
            prompt_tokens: 输入 Token 数
            completion_tokens: 输出 Token 数
            cost_usd: 成本（美元）
            latency_ms: 延迟（毫秒）
            status: 状态（success/error/timeout）
            error_message: 错误信息（可选）
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": "INFO",
            "event": "llm_call",
            "call_id": call_id,
            "user_id": user_id,
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "cost_usd": cost_usd,
            "latency_ms": latency_ms,
            "status": status,
        }
        
        if error_message:
            log_entry["error_message"] = error_message
            log_entry["level"] = "ERROR"
        
        self.logger.info(json.dumps(log_entry, ensure_ascii=False))
    
    def log_tool_call(
        self,
        call_id: str,
        tool_name: str,
        tool_args: Dict[str, Any],
        latency_ms: int,
        status: str,
        error_message: Optional[str] = None
    ):
        """记录工具调用日志
        
        Args:
            call_id: 调用 ID
            tool_name: 工具名称
            tool_args: 工具参数
            latency_ms: 延迟（毫秒）
            status: 状态（success/error）
            error_message: 错误信息（可选）
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": "INFO",
            "event": "tool_call",
            "call_id": call_id,
            "tool_name": tool_name,
            "tool_args_preview": json.dumps(tool_args)[:200],  # 截断
            "latency_ms": latency_ms,
            "status": status,
        }
        
        if error_message:
            log_entry["error_message"] = error_message
            log_entry["level"] = "ERROR"
                
        self.logger.info(json.dumps(log_entry, ensure_ascii=False))
    
    def log_agent_run(
        self,
        run_id: str,
        user_id: str,
        session_id: str,
        total_tokens: int,
        total_cost_usd: float,
        total_latency_ms: int,
        status: str,
        num_iterations: int
    ):
        """记录 Agent 运行日志
        
        Args:
            run_id: 运行 ID
            user_id: 用户 ID
            session_id: 会话 ID
            total_tokens: 总 Token 数
            total_cost_usd: 总成本（美元）
            total_latency_ms: 总延迟（毫秒）
            status: 状态（success/error）
            num_iterations: 迭代次数
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": "INFO",
            "event": "agent_run",
            "run_id": run_id,
            "user_id": user_id,
            "session_id": session_id,
            "total_tokens": total_tokens,
            "total_cost_usd": total_cost_usd,
            "total_latency_ms": total_latency_ms,
            "status": status,
            "num_iterations": num_iterations,
        }
        
        self.logger.info(json.dumps(log_entry, ensure_ascii=False))


# ============================================================
# 使用示例
# ============================================================

if __name__ == "__main__":
    # 初始化监控器
    langsmith_monitor = LangSmithMonitor(enabled=True, project_name="agent-monitoring")
    otel_monitor = OTelMonitor(enabled=False)
    monitor_logger = MonitoringLogger()
    
    # 示例：追踪 LLM 调用
    @langsmith_monitor.trace_llm_call
    def call_openai(prompt: str, model: str = "gpt-4o-mini"):
        """模拟 OpenAI 调用"""
        import time
        time.sleep(1)  # 模拟延迟
        return f"模拟回复：{prompt[:20]}..."
    
    # 调用
    result = call_openai("解释什么是 RAG")
    print(f"结果：{result}")
    
    # 记录日志
    monitor_logger.log_llm_call(
        call_id="call_001",
        user_id="user_001",
        model="gpt-4o-mini",
        prompt_tokens=150,
        completion_tokens=280,
        cost_usd=0.003,
        latency_ms=1200,
        status="success"
    )
    
    print("监控示例运行完成")
