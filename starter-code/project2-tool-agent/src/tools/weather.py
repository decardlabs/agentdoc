"""
天气查询工具

本模块提供天气查询功能，支持：
1. 查询指定城市的天气
2. 支持今天、明天、后天等日期
3. 返回结构化的天气信息

数据源：wttr.in (免费，无需 API Key)

作者：智能体工程师培养计划
日期：2024
"""

import requests
from typing import Dict, Optional
import json


def get_weather(city: str, date: str = "今天") -> str:
    """
    查询指定城市和日期的天气
    
    Args:
        city: 城市名，例如 "深圳"、"北京"、"Shanghai"
        date: 日期，支持 "今天"、"明天"、"后天" 或具体日期 "2024-01-15"
        
    Returns:
        格式化的天气信息字符串
        
    Examples:
        >>> get_weather("深圳")
        '深圳 今天 天气：晴天，温度 25°C，湿度 60%'
        
        >>> get_weather("北京", "明天")
        '北京 明天 天气：多云，温度 5°C'
    """
    try:
        # 构建 API URL
        # wttr.in 支持中文城市名，但建议用英文
        url = f"https://wttr.in/{city}?format=j1"
        
        # 发送请求
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # 解析数据
        if date == "今天" or date == "today":
            weather_data = data["current_condition"][0]
            result = _parse_current_weather(city, weather_data)
        else:
            # 未来天气（明天、后天）
            weather_data = data["weather"]
            result = _parse_forecast_weather(city, date, weather_data)
        
        return result
        
    except requests.exceptions.RequestException as e:
        return f"天气查询失败：网络连接错误 ({str(e)})"
    except KeyError as e:
        return f"天气查询失败：数据解析错误，可能是城市名不正确 ({str(e)})"
    except Exception as e:
        return f"天气查询失败：{str(e)}"


def _parse_current_weather(city: str, weather_data: Dict) -> str:
    """
    解析当前天气数据
    
    Args:
        city: 城市名
        weather_data: 天气数据字典
        
    Returns:
        格式化的天气信息
    """
    # 提取信息
    temp = weather_data.get("temp_C", "N/A")
    feels_like = weather_data.get("FeelsLikeC", "N/A")
    humidity = weather_data.get("humidity", "N/A")
    description = weather_data.get("weatherDesc", [{}])[0].get("value", "N/A")
    wind_speed = weather_data.get("windspeedKmph", "N/A")
    
    # 格式化输出
    result = f"""📍 {city} 今天天气：
- 天气：{description}
- 温度：{temp}°C (体感 {feels_like}°C)
- 湿度：{humidity}%
- 风速：{wind_speed} km/h
"""
    
    return result


def _parse_forecast_weather(city: str, date: str, weather_data: list) -> str:
    """
    解析未来天气数据
    
    Args:
        city: 城市名
        date: 日期描述
        weather_data: 天气数据列表
        
    Returns:
        格式化的天气信息
    """
    # 日期映射
    date_map = {
        "今天": 0,
        "明天": 1,
        "后天": 2,
        "today": 0,
        "tomorrow": 1,
        "day after tomorrow": 2
    }
    
    # 获取索引
    index = date_map.get(date, 0)
    
    if index >= len(weather_data):
        return f"抱歉，无法查询 {city} {date} 的天气（数据不可用）"
    
    # 提取数据
    day_data = weather_data[index]
    max_temp = day_data.get("maxtempC", "N/A")
    min_temp = day_data.get("mintempC", "N/A")
    description = day_data.get("hourly", [{}])[0].get("weatherDesc", [{}])[0].get("value", "N/A")
    
    # 格式化输出
    result = f"""📍 {city} {date} 天气：
- 天气：{description}
- 最高温度：{max_temp}°C
- 最低温度：{min_temp}°C
"""
    
    return result


def get_weather_simple(city: str) -> str:
    """
    简化版天气查询（用于快速测试）
    
    Args:
        city: 城市名
        
    Returns:
        简化的天气信息
    """
    try:
        # 使用简化的格式
        url = f"https://wttr.in/{city}?format=3"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        return response.text.strip()
    except Exception as e:
        return f"天气查询失败：{str(e)}"


if __name__ == "__main__":
    # 测试代码
    print("测试天气查询工具")
    print("=" * 50)
    
    # 测试查询深圳天气
    print("\n测试 1: 查询深圳今天天气")
    result = get_weather("深圳")
    print(result)
    
    # 测试查询北京天气
    print("\n测试 2: 查询北京天气")
    result = get_weather("北京")
    print(result)
    
    # 测试简化版
    print("\n测试 3: 简化版查询")
    result = get_weather_simple("上海")
    print(result)
    
    print("\n" + "=" * 50)
    print("测试完成！")
