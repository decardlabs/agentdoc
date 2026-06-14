# 项目 2：工具调用 Agent —— 天气/日历/计算器助手

> **阶段**：Phase 1 - 基础入门
> **周次**：Week 3
> **难度**：⭐⭐
> **预估工时**：10-15 小时

---

## 一、项目目标

构建一个命令行 Agent，能调用外部工具完成用户任务。至少实现 3 个工具：天气查询、计算器、当前时间。

**核心能力培养**：
- Function Calling / Tool Use 机制
- Agent 循环原理（Thought → Action → Observation）
- 工具定义规范
- 错误处理与重试

---

## 二、详细任务说明

### 2.1 基础版任务（必做，8-10 小时）

#### Step 1：理解 Function Calling 原理（1 小时）

**学习目标**：
- 理解为什么需要 Function Calling
- 理解工具定义、工具选择、工具执行的流程

**核心概念**：
```
用户输入: "北京今天天气怎么样？"
     ↓
LLM 思考: 用户在问天气，我需要调用天气查询工具
     ↓
LLM 输出: { "tool": "get_weather", "args": { "city": "北京" } }
     ↓
执行工具: 调用天气 API，获取结果
     ↓
LLM 再次思考: 我有了天气数据，可以回答用户了
     ↓
最终回复: "北京今天晴，25°C..."
```

**可视化 Agent 循环**：
```
┌─────────────────────────────────────────┐
│  1. 用户输入                             │
│     ↓                                   │
│  2. LLM 思考（Thought）                  │
│     ↓                                   │
│  3. 需要调用工具？                        │
│     ├─ 否 → 直接回复（步骤 6）            │
│     └─ 是 → 继续                         │
│     ↓                                   │
│  4. LLM 选择工具 + 参数（Action）         │
│     ↓                                   │
│  5. 执行工具，获取结果（Observation）     │
│     ↓                                   │
│  6. LLM 基于结果生成最终回复              │
│     ↓                                   │
│  7. 返回给用户                           │
└─────────────────────────────────────────┘
```

---

#### Step 2：定义工具（3 小时）

**任务清单**：
- [ ] 定义"获取当前时间"工具
- [ ] 定义"计算器"工具（支持加减乘除、平方根、幂运算）
- [ ] 定义"天气查询"工具（用免费 API 或 mock 数据）
- [ ] 按 OpenAI Function Calling 规范定义

**OpenAI Function Calling 规范**：
```json
{
  "type": "function",
  "function": {
    "name": "get_weather",
    "description": "获取指定城市的当前天气",
    "parameters": {
      "type": "object",
      "properties": {
        "city": {
          "type": "string",
          "description": "城市名称，例如：北京、上海"
        }
      },
      "required": ["city"]
    }
  }
}
```

**工具实现示例**：
```python
import datetime
import math
import requests

# 工具 1：获取当前时间
def get_current_time() -> str:
    """获取当前时间"""
    now = datetime.datetime.now()
    return now.strftime("%Y-%m-%d %H:%M:%S")

# 工具 2：计算器
def calculator(expression: str) -> str:
    """
    执行数学计算
    支持: +, -, *, /, **, sqrt()
    """
    try:
        # 安全检查：只允许数字和运算符
        allowed_chars = set("0123456789+-*/.() ")
        if not all(c in allowed_chars for c in expression):
            return "错误：包含非法字符"

        result = eval(expression)  # 注意：实际项目中不要直接用 eval
        return str(result)
    except Exception as e:
        return f"计算错误：{str(e)}"

# 工具 3：天气查询
def get_weather(city: str) -> str:
    """获取指定城市的天气（使用 wttr.in 免费 API）"""
    try:
        url = f"https://wttr.in/{city}?format=j1"
        response = requests.get(url, timeout=10)
        data = response.json()
        current = data["current_condition"][0]
        return f"{city}当前天气：{current['weatherDesc'][0]['value']}，温度 {current['temp_C']}°C"
    except Exception as e:
        return f"查询失败：{str(e)}"

# 工具注册表
TOOLS = {
    "get_current_time": get_current_time,
    "calculator": calculator,
    "get_weather": get_weather,
}
```

**工具定义（OpenAI Schema）**：
```python
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "获取当前时间",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "执行数学计算，支持加减乘除、幂运算",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "数学表达式，例如：(2+3)*5"
                    }
                },
                "required": ["expression"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "获取指定城市的当前天气",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市名称"
                    }
                },
                "required": ["city"]
            }
        }
    }
]
```

---

#### Step 3：实现 Agent 循环（3 小时）

**任务清单**：
- [ ] 调用 LLM，让它决定是否需要调用工具
- [ ] 如果需要，解析工具名和参数
- [ ] 执行工具，获取结果
- [ ] 把工具结果反馈给 LLM
- [ ] LLM 生成最终回复
- [ ] 循环直到 LLM 不再调用工具

**完整代码**：
```python
from openai import OpenAI
import json

client = OpenAI()

SYSTEM_PROMPT = """你是一个智能助手，可以使用以下工具来回答用户问题：
- get_current_time: 获取当前时间
- calculator: 执行数学计算
- get_weather: 查询天气

回答风格：
- 简洁、准确
- 如果需要使用工具，先调用工具，再基于工具结果回答
"""

def run_agent(user_input: str) -> str:
    """运行 Agent 循环"""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_input}
    ]

    max_iterations = 5  # 防止无限循环
    for i in range(max_iterations):
        print(f"\n--- 迭代 {i+1} ---")

        # 1. 调用 LLM
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=TOOL_DEFINITIONS,
            tool_choice="auto"  # 让 LLM 自动决定是否调用工具
        )

        assistant_message = response.choices[0].message
        messages.append(assistant_message)

        # 2. 检查 LLM 是否要调用工具
        if assistant_message.tool_calls:
            print(f"🤖 LLM 决定调用 {len(assistant_message.tool_calls)} 个工具")

            # 3. 执行所有工具调用
            for tool_call in assistant_message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)

                print(f"🔧 调用工具: {function_name}({function_args})")

                # 执行工具
                if function_name in TOOLS:
                    try:
                        function_result = TOOLS[function_name](**function_args)
                    except Exception as e:
                        function_result = f"工具执行失败：{str(e)}"
                else:
                    function_result = f"未知工具：{function_name}"

                print(f"📊 工具结果: {function_result}")

                # 4. 把工具结果反馈给 LLM
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": function_result
                })

        else:
            # 5. LLM 不再调用工具，返回最终回复
            final_answer = assistant_message.content
            print(f"✅ 最终回复: {final_answer}")
            return final_answer

    return "达到最大迭代次数，任务未完成"

# 测试
if __name__ == "__main__":
    print(run_agent("北京今天天气怎么样？"))
    print("\n" + "="*50 + "\n")
    print(run_agent("(25 + 17) * 3 等于多少？"))
    print("\n" + "="*50 + "\n")
    print(run_agent("现在几点了？"))
```

**预期输出**：
```
--- 迭代 1 ---
🤖 LLM 决定调用 1 个工具
🔧 调用工具: get_weather({'city': '北京'})
📊 工具结果: 北京当前天气：Sunny，温度 25°C
--- 迭代 2 ---
✅ 最终回复: 北京今天是晴天，温度 25°C。
```

---

#### Step 4：构建命令行交互（1 小时）

**任务清单**：
- [ ] 实现 REPL（Read-Eval-Print Loop）
- [ ] 显示 Agent 思考过程
- [ ] 支持退出命令（exit / quit）

**代码**：
```python
def main():
    print("🤖 智能助手已启动（输入 'quit' 退出）")
    print("可用工具：天气、计算器、时间")
    print("="*50)

    while True:
        user_input = input("\n👤 你: ").strip()

        if user_input.lower() in ["quit", "exit", "退出"]:
            print("👋 再见！")
            break

        if not user_input:
            continue

        try:
            response = run_agent(user_input)
            print(f"\n🤖 助手: {response}")
        except Exception as e:
            print(f"❌ 错误: {str(e)}")

if __name__ == "__main__":
    main()
```

---

### 2.2 挑战版任务（选做 2 个，4-6 小时）

#### 挑战 1：加入记忆功能

**任务**：
- [ ] 记住用户之前问过什么
- [ ] 上下文相关的回答（"刚才那个城市"）

**实现思路**：
```python
class AgentWithMemory:
    def __init__(self):
        self.conversation_history = []

    def chat(self, user_input: str) -> str:
        # 把历史对话加入 messages
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            *self.conversation_history,
            {"role": "user", "content": user_input}
        ]

        response = run_agent_loop(messages)

        # 保存到历史
        self.conversation_history.append({"role": "user", "content": user_input})
        self.conversation_history.append({"role": "assistant", "content": response})

        # 限制历史长度（避免超出 Token）
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]

        return response
```

---

#### 挑战 2：工具组合调用

**任务**：
- [ ] 一个问题需要调用多个工具
- [ ] 例如："北京和上海哪个城市更热？"

**实现思路**：
```python
# LLM 可能生成两次工具调用
tool_calls = [
    {"function": {"name": "get_weather", "arguments": '{"city": "北京"}'}},
    {"function": {"name": "get_weather", "arguments": '{"city": "上海"}'}}
]

# 并行执行（提升性能）
import concurrent.futures
with concurrent.futures.ThreadPoolExecutor() as executor:
    futures = [
        executor.submit(TOOLS[call.function.name], **json.loads(call.function.arguments))
        for call in tool_calls
    ]
    results = [f.result() for f in futures]
```

**测试用例**：
- "北京和上海今天天气怎么样？"
- "现在是几点？1000 秒后是几点？"
- "深圳的天气温度乘以 2 是多少？"

---

#### 挑战 3：工具调用失败处理

**任务**：
- [ ] 工具执行失败时，Agent 能自我修复
- [ ] 例如：天气 API 超时 → 改用另一个数据源

**实现代码**：
```python
def get_weather_with_fallback(city: str) -> str:
    """带降级策略的天气查询"""
    try:
        # 尝试 wttr.in
        return get_weather_wttr(city)
    except Exception as e:
        print(f"wttr.in 失败：{e}")
        try:
            # 降级到 open-meteo
            return get_weather_openmeteo(city)
        except Exception as e2:
            return f"天气查询失败：{e2}"
```

**Agent 层面**：
- 在 Prompt 里告诉 LLM："如果工具失败，可以尝试其他方法"
- 把错误信息反馈给 LLM，让它决定下一步

---

#### 挑战 4：Web 界面

**任务**：
- [ ] 用 Streamlit 包装命令行 Agent
- [ ] 可视化展示 Agent 的思考过程

**实现**：
```python
import streamlit as st

st.title("🤖 工具调用 Agent")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "trace" not in st.session_state:
    st.session_state.trace = []

user_input = st.chat_input("请输入你的问题")
if user_input:
    # 显示用户消息
    st.chat_message("user").write(user_input)

    # 运行 Agent
    with st.spinner("思考中..."):
        response = run_agent(user_input, trace=True)

    # 显示助手回复
    st.chat_message("assistant").write(response)

    # 展示思考过程
    with st.expander("🔍 查看 Agent 思考过程"):
        for step in st.session_state.trace:
            st.write(step)
```

---

#### 挑战 5：自定义工具开发

**任务**：
- [ ] 让用户可以自定义工具（插件机制）
- [ ] 通过配置文件或 Python 文件动态加载

**配置文件**：
```yaml
tools:
  - name: search_baidu
    description: 百度搜索
    function: tools.search.search_baidu
    parameters:
      query:
        type: string
        description: 搜索关键词
```

**动态加载**：
```python
import importlib

def load_tools_from_config(config_path: str) -> dict:
    """从配置文件加载工具"""
    with open(config_path) as f:
        config = yaml.safe_load(f)

    tools = {}
    for tool_config in config["tools"]:
        module = importlib.import_module(tool_config["function"].rsplit(".", 1)[0])
        func = getattr(module, tool_config["function"].rsplit(".", 1)[1])
        tools[tool_config["name"]] = func

    return tools
```

---

## 三、踩坑经验汇总

### 坑 1：LLM 陷入死循环

**现象**：Agent 反复调用同一个工具，无法停止  
**原因**：工具结果没有正确反馈给 LLM，或者 max_iterations 没设置  
**解决**：
- 设置 `max_iterations`（推荐 5-10）
- 严格检查 `tool_calls` 字段
- 记录已调用的工具，避免重复调用

### 坑 2：工具参数解析失败

**现象**：`json.loads(tool_call.function.arguments)` 报错  
**原因**：LLM 生成的 JSON 格式有问题  
**解决**：
```python
try:
    args = json.loads(tool_call.function.arguments)
except json.JSONDecodeError:
    # 尝试修复常见错误
    args_str = tool_call.function.arguments.replace("'", '"')
    args = json.loads(args_str)
```

### 坑 3：工具执行时间过长

**现象**：天气 API 调用卡住，整个 Agent 卡死  
**解决**：
```python
import signal

def timeout_handler(signum, frame):
    raise TimeoutError("工具执行超时")

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(10)  # 10 秒超时
try:
    result = TOOLS[name](**args)
finally:
    signal.alarm(0)
```

### 坑 4：Token 消耗激增

**现象**：多轮工具调用后，Context 变得很大  
**原因**：每次迭代都把之前的 tool_calls 和结果加进 messages  
**解决**：
- 限制 `max_iterations`
- 工具结果做摘要（如果结果太长）
- 定期清理历史消息

### 坑 5：工具名/参数拼写错误

**现象**：LLM 调用了不存在的工具，或者参数名拼错  
**原因**：工具定义不规范，或者 LLM "幻觉"  
**解决**：
- 工具定义用清晰的 `description`
- 在 Prompt 里强调："只能使用以下工具：[工具列表]"
- 严格校验参数，失败时让 LLM 重试

---

## 四、评估标准详解

### 及格（60 分）

- [ ] 实现了至少 3 个工具
- [ ] Agent 循环正确（能调用工具并基于结果回复）
- [ ] 命令行交互可用
- [ ] 代码可运行

### 良好（75 分）

在及格基础上：
- [ ] 工具执行失败有错误处理
- [ ] 有详细的注释和文档
- [ ] 代码结构清晰（类、函数、模块化）
- [ ] 演示了完整的 Agent 思考过程

### 优秀（90 分）

在良好基础上：
- [ ] 完成了至少 3 个挑战任务
- [ ] 记忆功能可用
- [ ] 并行工具调用
- [ ] Web 界面美观
- [ ] 有技术博客讲清楚 Agent 循环原理

---

## 五、进阶学习

完成本项目后，建议深入学习：

1. **ReAct 模式**（Reasoning + Acting）
   - 在 Thought 里加入推理过程
   - 论文：ReAct: Synergizing Reasoning and Acting in Language Models

2. **复杂工具链**
   - 工具 A 的输出作为工具 B 的输入
   - 动态工具发现

3. **Toolformer**
   - 让 LLM 自己学会调用工具
   - 论文：Toolformer: Language Models Can Teach Themselves to Use Tools

---

## 六、交付物清单

- [ ] **代码仓库**（GitHub）
  - 完整可运行代码
  - 工具定义文件
  - README.md
- [ ] **演示视频**（5 分钟）
  - 展示 Agent 调用工具的过程
  - 展示 Thought-Action-Observation
- [ ] **技术博客**（可选，1500 字）
  - Agent 循环原理
  - Function Calling 详解
  - 踩坑经验

---

**下一步**：完成本项目后，进入 [项目 3：RAG 系统](../项目3-RAG系统/README.md)
