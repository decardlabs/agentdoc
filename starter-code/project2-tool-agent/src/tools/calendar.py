"""
日历工具（模拟）

本模块提供日历操作功能（模拟版本），支持：
1. 查询今天的日期
2. 添加日程（模拟）
3. 查询日程（模拟）
4. 日期计算

注意：这是模拟版本，实际项目中可以接入 Google Calendar API

作者：智能体工程师培养计划
日期：2024
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional
import json


# 模拟数据库（内存中）
_calendar_events = []


def get_today() -> str:
    """
    获取今天的日期
    
    Returns:
        格式化的日期字符串
        
    Examples:
        >>> get_today()
        '今天是 2024年1月15日 星期一'
    """
    today = datetime.now()
    weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    weekday = weekdays[today.weekday()]
    
    result = f"""📅 今天的日期：
- 日期：{today.year}年{today.month}月{today.day}日
- 星期：{weekday}
- 时间：{today.hour:02d}:{today.minute:02d}
"""
    
    return result


def get_current_time() -> str:
    """
    获取当前时间
    
    Returns:
        格式化的时间字符串
    """
    now = datetime.now()
    return f"当前时间：{now.hour:02d}:{now.minute:02d}:{now.second:02d}"


def add_event(event_name: str, date: str, time: str = "全天", description: str = "") -> str:
    """
    添加日程（模拟）
    
    Args:
        event_name: 事件名称
        date: 日期，格式 "2024-01-15" 或 "明天"、"下周一审"
        time: 时间，格式 "14:00" 或 "全天"
        description: 事件描述（可选）
        
    Returns:
        操作结果字符串
        
    Examples:
        >>> add_event("团队会议", "明天", "14:00", "讨论项目进展")
        '✅ 已添加日程：团队会议 (明天 14:00)'
    """
    try:
        # 解析日期
        parsed_date = _parse_date(date)
        
        # 创建事件
        event = {
            "id": len(_calendar_events) + 1,
            "name": event_name,
            "date": parsed_date.strftime("%Y-%m-%d"),
            "time": time,
            "description": description,
            "created_at": datetime.now().isoformat()
        }
        
        # 添加到模拟数据库
        _calendar_events.append(event)
        
        return f"✅ 已添加日程：{event_name} ({parsed_date.strftime('%Y年%m月%d日')} {time})"
        
    except Exception as e:
        return f"❌ 添加日程失败：{str(e)}"


def list_events(date: Optional[str] = None) -> str:
    """
    查询日程（模拟）
    
    Args:
        date: 日期筛选（可选），格式 "2024-01-15" 或 "今天"、"明天"
        
    Returns:
        格式化的日程列表
    """
    try:
        events = _calendar_events
        
        # 日期筛选
        if date:
            parsed_date = _parse_date(date)
            date_str = parsed_date.strftime("%Y-%m-%d")
            events = [e for e in events if e["date"] == date_str]
        
        if not events:
            return "📅 没有找到日程"
        
        # 格式化输出
        result = "📅 日程列表：\n"
        for event in events:
            result += f"""
- {event['name']}
  日期：{event['date']}
  时间：{event['time']}
  描述：{event['description'] if event['description'] else '无'}
"""
        
        return result
        
    except Exception as e:
        return f"❌ 查询日程失败：{str(e)}"


def delete_event(event_id: int) -> str:
    """
    删除日程（模拟）
    
    Args:
        event_id: 事件 ID
        
    Returns:
        操作结果字符串
    """
    global _calendar_events
    
    try:
        # 查找事件
        event = next((e for e in _calendar_events if e["id"] == event_id), None)
        
        if not event:
            return f"❌ 未找到 ID 为 {event_id} 的日程"
        
        # 删除事件
        _calendar_events = [e for e in _calendar_events if e["id"] != event_id]
        
        return f"✅ 已删除日程：{event['name']}"
        
    except Exception as e:
        return f"❌ 删除日程失败：{str(e)}"


def calculate_date_offset(date: str, days: int) -> str:
    """
    日期计算：计算指定日期前后 N 天的日期
    
    Args:
        date: 基准日期，格式 "2024-01-15" 或 "今天"
        days: 偏移天数（正数表示之后，负数表示之前）
        
    Returns:
        计算结果字符串
        
    Examples:
        >>> calculate_date_offset("今天", 7)
        '今天之后 7 天是：2024年1月22日'
    """
    try:
        parsed_date = _parse_date(date)
        result_date = parsed_date + timedelta(days=days)
        
        return f"{date} 之后 {days} 天是：{result_date.year}年{result_date.month}月{result_date.day}日"
        
    except Exception as e:
        return f"❌ 日期计算失败：{str(e)}"


def _parse_date(date_str: str) -> datetime:
    """
    解析日期字符串
    
    Args:
        date_str: 日期字符串
        
    Returns:
        datetime 对象
    """
    # 处理相对日期
    if date_str == "今天" or date_str == "today":
        return datetime.now()
    elif date_str == "明天" or date_str == "tomorrow":
        return datetime.now() + timedelta(days=1)
    elif date_str == "后天":
        return datetime.now() + timedelta(days=2)
    elif date_str == "下周一审" or date_str == "next monday":
        today = datetime.now()
        days_ahead = 0 - today.weekday()  # 周一 = 0
        if days_ahead <= 0:
            days_ahead += 7
        return today + timedelta(days=days_ahead)
    
    # 尝试解析绝对日期
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        try:
            return datetime.strptime(date_str, "%Y/%m/%d")
        except ValueError:
            raise ValueError(f"无法解析日期：{date_str}")


if __name__ == "__main__":
    # 测试代码
    print("测试日历工具（模拟）")
    print("=" * 50)
    
    # 测试获取今天日期
    print("\n测试 1: 获取今天日期")
    print(get_today())
    
    # 测试添加日程
    print("\n测试 2: 添加日程")
    print(add_event("团队会议", "明天", "14:00", "讨论项目进展"))
    print(add_event("看医生", "2024-01-20", "10:00", "年度体检"))
    
    # 测试查询日程
    print("\n测试 3: 查询日程")
    print(list_events())
    
    # 测试日期计算
    print("\n测试 4: 日期计算")
    print(calculate_date_offset("今天", 7))
    
    print("\n" + "=" * 50)
    print("测试完成！")
