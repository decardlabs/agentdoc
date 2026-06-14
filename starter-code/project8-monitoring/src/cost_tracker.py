"""
成本追踪器 - 智能体工程师培养计划 项目 8
追踪 LLM 调用的 Token 消耗和成本
"""

from typing import Optional, Dict, List
from dataclasses import dataclass, field
from datetime import datetime, date
import json
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
# 定价表（$/1M tokens）
# ============================================================
PRICING_TABLE = {
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-cached": {"input": 1.25, "output": 10.00},
    "claude-3.5-sonnet": {"input": 3.00, "output": 15.00},
    "claude-3-haiku": {"input": 0.25, "output": 1.25},
    "deepseek-chat": {"input": 0.14, "output": 0.28},
}

# ============================================================
# 数据模型
# ============================================================
@dataclass
class CostRecord:
    """单次调用成本记录"""
    call_id: str
    timestamp: str
    user_id: str
    session_id: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    latency_ms: int
    status: str
    error_message: Optional[str] = None

@dataclass
class BudgetAlert:
    """预算告警"""
    user_id: str
    alert_type: str  # "daily" | "monthly" | "user_daily"
    current_usd: float
    limit_usd: float
    usage_pct: float
    timestamp: str

# ============================================================
# 成本追踪器
# ============================================================
class CostTracker:
    """成本追踪器 - 计算、记录和追踪 LLM 调用成本
    
    功能：
    - 计算单次调用成本
    - 计算会话总成本
    - 检查预算阈值
    - 生成成本报告
    """
    
    def __init__(
        self,
        daily_budget: float = 10.0,
        monthly_budget: float = 200.0,
        user_daily_budget: float = 2.0,
        db_path: str = "llm_logs.db"
    ):
        """初始化成本追踪器
        
        Args:
            daily_budget: 全局日预算（美元）
            monthly_budget: 全局月预算（美元）
            user_daily_budget: 用户日预算（美元）
            db_path: 数据库路径
        """
        self.daily_budget = daily_budget
        self.monthly_budget = monthly_budget
        self.user_daily_budget = user_daily_budget
        self.db_path = db_path
        self._alert_cache = {}  # 告警去重缓存
        
        logger.info(f"成本追踪器初始化完成，日预算：${daily_budget}，月预算：${monthly_budget}")
    
    def calculate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        """计算单次调用成本（美元）
        
        Args:
            model: 模型名称
            prompt_tokens: 输入 Token 数
            completion_tokens: 输出 Token 数
            
        Returns:
            成本（美元），保留 6 位小数
            
        Raises:
            ValueError: 模型不在定价表中
        """
        if model not in PRICING_TABLE:
            # 尝试模糊匹配
            for known_model in PRICING_TABLE:
                if known_model in model or model in known_model:
                    logger.warning(f"模型 '{model}' 不在定价表中，使用 '{known_model}' 的定价")
                    model = known_model
                    break
            else:
                raise ValueError(f"模型 {model} 不在定价表中，请先添加")
        
        pricing = PRICING_TABLE[model]
        cost = (prompt_tokens / 1_000_000) * pricing["input"] + \
               (completion_tokens / 1_000_000) * pricing["output"]
        
        return round(cost, 6)
    
    def record_call(self, record: CostRecord):
        """记录单次调用到数据库
        
        Args:
            record: 成本记录
        """
        try:
            import sqlite3
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS cost_records (
                        call_id TEXT PRIMARY KEY,
                        timestamp TEXT,
                        user_id TEXT,
                        session_id TEXT,
                        model TEXT,
                        prompt_tokens INTEGER,
                        completion_tokens INTEGER,
                        total_tokens INTEGER,
                        cost_usd REAL,
                        latency_ms INTEGER,
                        status TEXT,
                        error_message TEXT
                    )
                """)
                
                conn.execute("""
                    INSERT OR REPLACE INTO cost_records
                    (call_id, timestamp, user_id, session_id, model,
                     prompt_tokens, completion_tokens, total_tokens,
                     cost_usd, latency_ms, status, error_message)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    record.call_id,
                    record.timestamp,
                    record.user_id,
                    record.session_id,
                    record.model,
                    record.prompt_tokens,
                    record.completion_tokens,
                    record.prompt_tokens + record.completion_tokens,
                    record.cost_usd,
                    record.latency_ms,
                    record.status,
                    record.error_message
                ))
                
                logger.debug(f"成本记录已保存：{record.call_id}，成本：${record.cost_usd:.6f}")
                
        except Exception as e:
            logger.error(f"保存成本记录失败：{str(e)}")
    
    def calculate_session_cost(self, records: List[CostRecord]) -> Dict:
        """计算一次会话的总成本
        
        Args:
            records: 会话中的所有调用记录
            
        Returns:
            包含总成本和按模型分组的字典
        """
        total_cost = sum(r.cost_usd for r in records)
        total_tokens = sum(r.prompt_tokens + r.completion_tokens for r in records)
        
        by_model = {}
        for r in records:
            if r.model not in by_model:
                by_model[r.model] = {"cost": 0.0, "tokens": 0, "calls": 0}
            by_model[r.model]["cost"] += r.cost_usd
            by_model[r.model]["tokens"] += r.prompt_tokens + r.completion_tokens
            by_model[r.model]["calls"] += 1
        
        return {
            "total_cost_usd": round(total_cost, 4),
            "total_tokens": total_tokens,
            "total_calls": len(records),
            "by_model": by_model,
        }
    
    def check_budget(self, user_id: str) -> List[BudgetAlert]:
        """检查预算阈值
        
        Args:
            user_id: 用户 ID
            
        Returns:
            告警列表
        """
        alerts = []
        today = date.today().isoformat()
        
        try:
            import sqlite3
            
            with sqlite3.connect(self.db_path) as conn:
                # 全局日预算
                result = conn.execute("""
                    SELECT COALESCE(SUM(cost_usd), 0)
                    FROM cost_records
                    WHERE DATE(timestamp) = ?
                    AND status = 'success'
                """, (today,)).fetchone()
                
                today_total = result[0]
                
                if today_total > self.daily_budget:
                    alerts.append(BudgetAlert(
                        user_id="global",
                        alert_type="daily",
                        current_usd=today_total,
                        limit_usd=self.daily_budget,
                        usage_pct=round(today_total / self.daily_budget * 100, 1),
                        timestamp=datetime.utcnow().isoformat()
                    ))
                elif today_total > self.daily_budget * 0.8:
                    alerts.append(BudgetAlert(
                        user_id="global",
                        alert_type="daily",
                        current_usd=today_total,
                        limit_usd=self.daily_budget,
                        usage_pct=round(today_total / self.daily_budget * 100, 1),
                        timestamp=datetime.utcnow().isoformat()
                    ))
                
                # 用户日预算
                result = conn.execute("""
                    SELECT COALESCE(SUM(cost_usd), 0)
                    FROM cost_records
                    WHERE user_id = ?
                    AND DATE(timestamp) = ?
                    AND status = 'success'
                """, (user_id, today)).fetchone()
                
                user_today = result[0]
                
                if user_today > self.user_daily_budget:
                    alerts.append(BudgetAlert(
                        user_id=user_id,
                        alert_type="user_daily",
                        current_usd=user_today,
                        limit_usd=self.user_daily_budget,
                        usage_pct=round(user_today / self.user_daily_budget * 100, 1),
                        timestamp=datetime.utcnow().isoformat()
                    ))
                
                # 全局月预算
                first_day_of_month = date.today().replace(day=1).isoformat()
                
                result = conn.execute("""
                    SELECT COALESCE(SUM(cost_usd), 0)
                    FROM cost_records
                    WHERE timestamp >= ?
                    AND status = 'success'
                """, (first_day_of_month,)).fetchone()
                
                month_total = result[0]
                
                if month_total > self.monthly_budget:
                    alerts.append(BudgetAlert(
                        user_id="global",
                        alert_type="monthly",
                        current_usd=month_total,
                        limit_usd=self.monthly_budget,
                        usage_pct=round(month_total / self.monthly_budget * 100, 1),
                        timestamp=datetime.utcnow().isoformat()
                    ))
                
        except Exception as e:
            logger.error(f"检查预算失败：{str(e)}")
        
        return alerts
    
    def generate_cost_report(self, start_date: str, end_date: str, user_id: Optional[str] = None) -> Dict:
        """生成成本报告
        
        Args:
            start_date: 开始日期（YYYY-MM-DD）
            end_date: 结束日期（YYYY-MM-DD）
            user_id: 用户 ID（可选，为 None 时查询所有用户）
            
        Returns:
            成本报告字典
        """
        try:
            import sqlite3
            
            with sqlite3.connect(self.db_path) as conn:
                # 构建查询
                query = """
                    SELECT 
                        DATE(timestamp) as date,
                        user_id,
                        model,
                        COUNT(*) as calls,
                        SUM(prompt_tokens) as total_prompt_tokens,
                        SUM(completion_tokens) as total_completion_tokens,
                        SUM(total_tokens) as total_tokens,
                        SUM(cost_usd) as total_cost
                    FROM cost_records
                    WHERE DATE(timestamp) BETWEEN ? AND ?
                    AND status = 'success'
                """
                params = [start_date, end_date]
                
                if user_id:
                    query += " AND user_id = ?"
                    params.append(user_id)
                
                query += """
                    GROUP BY DATE(timestamp), user_id, model
                    ORDER BY date, user_id, model
                """
                
                cursor = conn.execute(query, params)
                
                rows = cursor.fetchall()
                
                # 构建报告
                report = {
                    "period": f"{start_date} to {end_date}",
                    "total_cost_usd": 0.0,
                    "total_tokens": 0,
                    "total_calls": 0,
                    "by_date": {},
                    "by_user": {},
                    "by_model": {},
                }
                
                for row in rows:
                    date_str, uid, model, calls, prompt_tokens, completion_tokens, tokens, cost = row
                    
                    report["total_cost_usd"] += cost
                    report["total_tokens"] += tokens
                    report["total_calls"] += calls
                    
                    # 按日期分组
                    if date_str not in report["by_date"]:
                        report["by_date"][date_str] = {"cost": 0.0, "calls": 0}
                    report["by_date"][date_str]["cost"] += cost
                    report["by_date"][date_str]["calls"] += calls
                    
                    # 按用户分组
                    if uid not in report["by_user"]:
                        report["by_user"][uid] = {"cost": 0.0, "calls": 0}
                    report["by_user"][uid]["cost"] += cost
                    report["by_user"][uid]["calls"] += calls
                    
                    # 按模型分组
                    if model not in report["by_model"]:
                        report["by_model"][model] = {"cost": 0.0, "calls": 0, "tokens": 0}
                    report["by_model"][model]["cost"] += cost
                    report["by_model"][model]["calls"] += calls
                    report["by_model"][model]["tokens"] += tokens
                
                # 四舍五入
                report["total_cost_usd"] = round(report["total_cost_usd"], 4)
                
                return report
                
        except Exception as e:
            logger.error(f"生成成本报告失败：{str(e)}")
            return {}
    
    def get_model_pricing(self, model: str) -> Dict:
        """获取模型定价
        
        Args:
            model: 模型名称
            
        Returns:
            定价字典（input/output 价格）
        """
        if model in PRICING_TABLE:
            return PRICING_TABLE[model]
        else:
            return {"input": 0.0, "output": 0.0, "error": "Model not found"}
    
    def add_model_pricing(self, model: str, input_price: float, output_price: float):
        """添加模型定价
        
        Args:
            model: 模型名称
            input_price: 输入价格（$/1M tokens）
            output_price: 输出价格（$/1M tokens）
        """
        PRICING_TABLE[model] = {"input": input_price, "output": output_price}
        logger.info(f"已添加模型定价：{model}，输入：${input_price}/1M，输出：${output_price}/1M")


# ============================================================
# 使用示例
# ============================================================

if __name__ == "__main__":
    # 初始化成本追踪器
    tracker = CostTracker(
        daily_budget=10.0,
        monthly_budget=200.0,
        user_daily_budget=2.0
    )
    
    # 计算单次调用成本
    cost = tracker.calculate_cost(
        model="gpt-4o",
        prompt_tokens=2000,
        completion_tokens=500
    )
    print(f"单次成本: ${cost:.6f}")
    
    # 记录调用
    record = CostRecord(
        call_id="call_001",
        timestamp=datetime.utcnow().isoformat(),
        user_id="user_001",
        session_id="session_001",
        model="gpt-4o",
        prompt_tokens=2000,
        completion_tokens=500,
        cost_usd=cost,
        latency_ms=1200,
        status="success"
    )
    tracker.record_call(record)
    
    # 检查预算
    alerts = tracker.check_budget("user_001")
    for alert in alerts:
        print(f"预算告警: {alert.alert_type}, 用户: {alert.user_id}, 使用率: {alert.usage_pct}%")
    
    print("成本追踪器示例运行完成")
