"""
FastAPI 监控 API - 智能体工程师培养计划 项目 8
提供监控数据查询 API
"""

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime, date
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
# FastAPI 应用初始化
# ============================================================
app = FastAPI(
    title="Agent Monitoring API",
    description="智能体工程师培养计划 - 项目 8：监控与成本优化",
    version="1.0.0"
)

# ============================================================
# 数据模型
# ============================================================
class CostSummaryResponse(BaseModel):
    """成本汇总响应"""
    period: str
    total_cost_usd: float
    total_tokens: int
    total_calls: int
    by_model: Dict
    by_user: Optional[Dict] = None
    by_date: Optional[Dict] = None

class LatencyStatsResponse(BaseModel):
    """延迟统计响应"""
    model: str
    p50_ms: float
    p95_ms: float
    p99_ms: float
    avg_ms: float
    max_ms: float

class AlertListResponse(BaseModel):
    """告警列表响应"""
    alerts: List[Dict]
    total: int

class BudgetStatusResponse(BaseModel):
    """预算状态响应"""
    user_id: str
    date: str
    budget_usd: float
    spent_usd: float
    remaining_usd: float
    usage_pct: float
    over_budget: bool

class CallRecordResponse(BaseModel):
    """调用记录响应"""
    call_id: str
    timestamp: str
    user_id: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    latency_ms: int
    status: str

# ============================================================
# 路由
# ============================================================
@app.get("/")
async def root():
    """根路径 - 返回 API 信息"""
    return {
        "service": "Agent Monitoring API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "cost_summary": "/api/v1/cost/summary",
            "latency_stats": "/api/v1/latency/stats",
            "recent_calls": "/api/v1/calls/recent",
            "anomalies": "/api/v1/anomalies",
            "alerts": "/api/v1/alerts",
            "budget": "/api/v1/users/{user_id}/budget",
            "metrics": "/metrics",
            "docs": "/docs"
        }
    }

@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.get("/api/v1/cost/summary", response_model=CostSummaryResponse)
async def get_cost_summary(
    start_date: str = Query(..., description="开始日期 YYYY-MM-DD"),
    end_date: str = Query(..., description="结束日期 YYYY-MM-DD"),
    user_id: Optional[str] = Query(None, description="按用户筛选"),
    model: Optional[str] = Query(None, description="按模型筛选")
):
    """成本汇总查询
    
    返回指定时间范围内的成本汇总，包括总成本和按模型/用户/日期分组。
    
    Args:
        start_date: 开始日期
        end_date: 结束日期
        user_id: 用户 ID（可选）
        model: 模型名称（可选）
        
    Returns:
        成本汇总响应
    """
    try:
        import sqlite3
        
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
        
        if model:
            query += " AND model = ?"
            params.append(model)
        
        query += """
            GROUP BY DATE(timestamp), user_id, model
            ORDER BY date, user_id, model
        """
        
        with sqlite3.connect("llm_logs.db") as conn:
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            
            # 构建响应
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
                date_str, uid, model_name, calls, prompt_tokens, completion_tokens, tokens, cost = row
                
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
                if model_name not in report["by_model"]:
                    report["by_model"][model_name] = {"cost": 0.0, "calls": 0, "tokens": 0}
                report["by_model"][model_name]["cost"] += cost
                report["by_model"][model_name]["calls"] += calls
                report["by_model"][model_name]["tokens"] += tokens
            
            # 四舍五入
            report["total_cost_usd"] = round(report["total_cost_usd"], 4)
            
            return CostSummaryResponse(**report)
            
    except Exception as e:
        logger.error(f"成本汇总查询失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/latency/stats", response_model=List[LatencyStatsResponse])
async def get_latency_stats(
    hours: int = Query(24, description="统计时间范围（小时）"),
    model: Optional[str] = Query(None, description="按模型筛选")
):
    """延迟统计查询
    
    返回指定时间范围内的延迟统计（P50/P95/P99/平均值/最大值）。
    
    Args:
        hours: 统计时间范围（小时）
        model: 模型名称（可选）
        
    Returns:
        延迟统计响应列表
    """
    try:
        import sqlite3
        import numpy as np
        
        query = """
            SELECT model, latency_ms
            FROM cost_records
            WHERE timestamp >= datetime('now', ? || ' hours')
            AND status = 'success'
        """
        params = [f"-{hours}"]
        
        if model:
            query += " AND model = ?"
            params.append(model)
        
        with sqlite3.connect("llm_logs.db") as conn:
            df = conn.execute(query, params).fetchall()
            
            if not df:
                return []
            
            # 按模型分组计算
            from collections import defaultdict
            model_data = defaultdict(list)
            for row in df:
                model_name, latency = row
                model_data[model_name].append(latency)
            
            result = []
            for model_name, latencies in model_data.items():
                latencies_array = np.array(latencies)
                result.append(LatencyStatsResponse(
                    model=model_name,
                    p50_ms=float(np.percentile(latencies_array, 50)),
                    p95_ms=float(np.percentile(latencies_array, 95)),
                    p99_ms=float(np.percentile(latencies_array, 99)),
                    avg_ms=float(np.mean(latencies_array)),
                    max_ms=float(np.max(latencies_array))
                ))
            
            return result
            
    except Exception as e:
        logger.error(f"延迟统计查询失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/calls/recent", response_model=List[CallRecordResponse])
async def get_recent_calls(
    limit: int = Query(50, le=200, description="返回记录数"),
    status: Optional[str] = Query(None, description="按状态筛选"),
    user_id: Optional[str] = Query(None, description="按用户筛选")
):
    """最近调用列表
    
    返回最近的 LLM 调用记录。
    
    Args:
        limit: 返回记录数（最大 200）
        status: 状态筛选（success/error/timeout）
        user_id: 用户 ID 筛选
        
    Returns:
        调用记录响应列表
    """
    try:
        import sqlite3
        
        query = """
            SELECT 
                call_id, timestamp, user_id, model,
                prompt_tokens, completion_tokens, total_tokens,
                cost_usd, latency_ms, status
            FROM cost_records
            WHERE 1=1
        """
        params = []
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        
        query += """
            ORDER BY timestamp DESC
            LIMIT ?
        """
        params.append(limit)
        
        with sqlite3.connect("llm_logs.db") as conn:
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            
            result = []
            for row in rows:
                result.append(CallRecordResponse(
                    call_id=row[0],
                    timestamp=row[1],
                    user_id=row[2],
                    model=row[3],
                    prompt_tokens=row[4],
                    completion_tokens=row[5],
                    total_tokens=row[6],
                    cost_usd=row[7],
                    latency_ms=row[8],
                    status=row[9]
                ))
            
            return result
            
    except Exception as e:
        logger.error(f"最近调用查询失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/users/{user_id}/budget", response_model=BudgetStatusResponse)
async def get_user_budget(user_id: str):
    """查询用户预算使用情况
    
    返回指定用户的预算使用情况，包括今日消费和预算使用率。
    
    Args:
        user_id: 用户 ID
        
    Returns:
        预算状态响应
    """
    try:
        import sqlite3
        
        today = date.today().isoformat()
        
        with sqlite3.connect("llm_logs.db") as conn:
            # 今日消费
            result = conn.execute("""
                SELECT COALESCE(SUM(cost_usd), 0)
                FROM cost_records
                WHERE user_id = ? AND DATE(timestamp) = ?
                AND status = 'success'
            """, (user_id, today)).fetchone()
            
            spent = result[0]
            
            # 这里应该从配置文件或数据库读取预算
            daily_limit = 2.0  # 默认用户日预算 $2
            
            remaining = daily_limit - spent
            usage_pct = (spent / daily_limit * 100) if daily_limit > 0 else 0
            
            return BudgetStatusResponse(
                user_id=user_id,
                date=today,
                budget_usd=daily_limit,
                spent_usd=round(spent, 4),
                remaining_usd=round(remaining, 4),
                usage_pct=round(usage_pct, 1),
                over_budget=spent > daily_limit
            )
            
    except Exception as e:
        logger.error(f"预算查询失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================
# 启动入口
# ============================================================
if __name__ == "__main__":
    """主入口 - 启动 FastAPI 应用"""
    import uvicorn
    
    port = int(os.getenv("PORT", 8002))
    
    logger.info(f"Starting Agent Monitoring API on port {port}")
    
    uvicorn.run(
        "src.api:app",
        host="0.0.0.0",
        port=port,
        workers=2,
        log_level="info"
    )
