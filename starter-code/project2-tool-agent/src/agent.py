"""
LangGraph Agent 主文件

本模块是工具调用 Agent 的主入口，提供：
1. 工具注册和管理
2. Agent 循环（ReAct）
3. 命令行交互界面
4. 工具调用日志

作者：智能体工程师培养计划
日期：2024
"""

import os
import sys
import json
import logging
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 导入工具
from tools.weather import get_weather
from tools.calculator import calculator
from tools.calendar import get_today, add_event, list_events, get_current_time
from prompts import get_system_prompt


class ToolAgent:
    """
    工具调用 Agent 类
    
    实现 ReAct 循环：Reasoning -> Acting -> Observing
    """
    
    def __init__(self, model: str = "gpt-4o-mini", max_iterations: int = 5):
        """
        初始化 Agent
        
        Args:
            model: 模型名称
            max_iterations: 最大迭代次数
        """
        self.model = model
        self.max_iterations = max_iterations
        
        # 检查 API Key
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("未找到 OPENAI_API_KEY 环境变量")
        
        # 初始化 OpenAI 客户端
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key)
        
        # 工具注册表
        self.tools = {
            "get_weather": get_weather,
            "calculator": calculator,
            "get_today": get_today,
            "get_current_time": get_current_time,
            "add_event": add_event,
            "list_events": list_events,
        }
        
        # 工具 Schema（用于 OpenAI Function Calling）
        self.tools_schema = self._build_tools_schema()
        
        # 对话历史
        self.conversation_history = []
        
        logger.info(f"ToolAgent 初始化完成: model={model}, tools={list(self.tools.keys())}")
    
    def _build_tools_schema(self) -> List[Dict]:
        """
        构建工具 Schema（OpenAI Function Calling 格式）
        
        Returns:
            工具 Schema 列表
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "查询指定城市和日期的天气。当用户问天气、温度、下雨等问题时调用。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "city": {
                                "type": "string",
                                "description": "城市名，例如 '深圳'、'北京'、'Shanghai'"
                            },
                            "date": {
                                "type": "string",
                                "description": "日期，默认为'今天'，也支持'明天'、'后天'"
                            }
                        },
                        "required": ["city"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "calculator",
                    "description": "数学计算器，支持基本运算和科学计算。当用户需要计算数学表达式时调用。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "expression": {
                                "type": "string",
                                "description": "数学表达式，例如 '2+3*4'、'sqrt(16)'、'sin(pi/2)'"
                            }
                        },
                        "required": ["expression"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_today",
                    "description": "获取今天的日期和星期。当用户问'今天几号'、'今天星期几'时调用。",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_current_time",
                    "description": "获取当前时间。当用户问'现在几点'时调用。",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "add_event",
                    "description": "添加日程。当用户说'帮我加个日程'、'提醒我明天开会'时调用。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "event_name": {
                                "type": "string",
                                "description": "事件名称"
                            },
                            "date": {
                                "type": "string",
                                "description": "日期，格式 '2024-01-15' 或 '明天'"
                            },
                            "time": {
                                "type": "string",
                                "description": "时间，格式 '14:00' 或 '全天'"
                            },
                            "description": {
                                "type": "string",
                                "description": "事件描述（可选）"
                            }
                        },
                        "required": ["event_name", "date"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "list_events",
                    "description": "查询日程。当用户问'我有什么安排'、'明天有什么事'时调用。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "date": {
                                "type": "string",
                                "description": "日期筛选（可选）"
                            }
                        }
                    }
                }
            }
        ]
    
    def run(self, user_input: str) -> str:
        """
        运行 Agent（ReAct 循环）
        
        Args:
            user_input: 用户输入
            
        Returns:
            Agent 的回答
        """
        # 添加用户消息到历史
        self.conversation_history.append({"role": "user", "content": user_input})
        
        # 构建 messages
        messages = [
            {"role": "system", "content": get_system_prompt("weather")},
            *self.conversation_history
        ]
        
        # ReAct 循环
        for iteration in range(self.max_iterations):
            logger.info(f"迭代 {iteration + 1}/{self.max_iterations}")
            
            # 1. LLM 决策
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self.tools_schema,
                tool_choice="auto"
            )
            
            message = response.choices[0].message
            
            # 2. 判断是否要调用工具
            if not message.tool_calls:
                # 不需要调用工具，直接返回回答
                answer = message.content
                
                # 添加到历史
                self.conversation_history.append({"role": "assistant", "content": answer})
                
                logger.info(f"迭代 {iteration + 1}: LLM 直接回答")
                return answer
            
            # 3. 执行工具调用
            messages.append(message)  # 保留 LLM 的工具调用决策
            
            for tool_call in message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                logger.info(f"迭代 {iteration + 1}: 调用工具 {function_name}, 参数: {function_args}")
                
                # 执行工具
                if function_name in self.tools:
                    try:
                        result = self.tools[function_name](**function_args)
                        logger.info(f"工具 {function_name} 返回: {result[:100]}...")
                    except Exception as e:
                        result = f"工具执行失败: {str(e)}"
                        logger.error(f"工具 {function_name} 执行失败: {str(e)}")
                else:
                    result = f"未知工具: {function_name}"
                    logger.error(f"未知工具: {function_name}")
                
                # 4. 把工具结果加回 messages
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result
                })
            
            # 继续循环（让 LLM 基于工具结果生成回答）
        
        # 达到最大迭代次数
        logger.warning(f"达到最大迭代次数 {self.max_iterations}")
        
        # 最后一次调用 LLM 生成回答
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages
        )
        
        answer = response.choices[0].message.content
        self.conversation_history.append({"role": "assistant", "content": answer})
        
        return answer
    
    def clear_history(self):
        """
        清除对话历史
        """
        self.conversation_history = []
        logger.info("对话历史已清除")


def main():
    """
    主函数：命令行交互界面
    """
    print("=" * 60)
    print("🤖 工具调用 Agent")
    print("=" * 60)
    print("\n可用工具：")
    print("  - 天气查询 (get_weather)")
    print("  - 计算器 (calculator)")
    print("  - 日历操作 (get_today, add_event, list_events)")
    print("\n输入 'quit' 或 'exit' 退出")
    print("输入 'clear' 清除对话历史")
    print("=" * 60)
    
    try:
        # 初始化 Agent
        agent = ToolAgent()
        
        # 交互循环
        while True:
            # 用户输入
            user_input = input("\n👤 你: ").strip()
            
            # 退出命令
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\n👋 再见！")
                break
            
            # 清除历史命令
            if user_input.lower() == 'clear':
                agent.clear_history()
                print("\n🗑️ 对话历史已清除")
                continue
            
            # 空输入
            if not user_input:
                continue
            
            # 运行 Agent
            try:
                answer = agent.run(user_input)
                print(f"\n🤖 Agent: {answer}")
            except Exception as e:
                print(f"\n❌ 错误: {str(e)}")
        
    except Exception as e:
        print(f"\n❌ 初始化失败: {str(e)}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
