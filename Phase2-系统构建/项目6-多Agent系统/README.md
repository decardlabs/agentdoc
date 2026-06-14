# 项目 6：多 Agent 系统 —— 自动化内容生成

> **阶段**：Phase 2 - 系统构建
> **周次**：Week 7-8
> **难度**：⭐⭐⭐⭐
> **预估工时**：18-22 小时

---

## 一、项目目标

用多 Agent 协作完成内容生产全流程：选题 → 资料研究 → 写作 → 审校。

**核心能力培养**：
- Agent 角色设计
- Agent 间通信协议
- 任务编排（顺序、并行、条件分支）
- 冲突解决
- 人工审核节点

---

## 二、多 Agent 系统基础

### 为什么需要多 Agent？

**单 Agent 的局限**：
- 任务复杂时，Prompt 难以描述
- 角色混乱（既是研究员又是写作者）
- 难以分工协作

**多 Agent 的优势**：
- 职责分离：每个 Agent 专注一件事
- 可组合：可以增删 Agent
- 可观察：可以追踪每个 Agent 的行为

### 多 Agent 协作模式

```
模式 1：顺序执行（Sequential）
Researcher → Writer → Reviewer → Editor
   ↓
   流水线式

模式 2：分层管理（Hierarchical）
        Manager
       /  |  \
   A1   A2   A3
   Manager 协调多个 Worker

模式 3：群组讨论（Group Chat）
   A1  A2  A3  A4
   自由讨论，达成共识
```

---

## 三、详细任务说明

### 3.1 基础版任务（必做，12-15 小时）

#### Step 1：环境准备（1 小时）

**任务清单**：
- [ ] 选择框架：**AutoGen**（推荐）或 **CrewAI**
- [ ] 安装依赖：`pip install pyautogen` 或 `pip install crewai`
- [ ] 配置 LLM（OpenAI GPT-4）

**AutoGen vs CrewAI 对比**：

| 维度 | AutoGen | CrewAI |
|------|---------|--------|
| 学习曲线 | 中等 | 简单 |
| 灵活性 | 🟢 高 | 🟡 中 |
| 群组对话 | ✅ 强 | 🟡 弱 |
| 任务编排 | 🟡 中 | ✅ 强 |
| 适合场景 | 研究型项目 | 业务型项目 |

**本项目推荐用 AutoGen**（更灵活，便于学习原理）

---

#### Step 2：设计 Agent 角色（3 小时）

**任务清单**：
- [ ] 设计 4 个 Agent：Researcher、Writer、Reviewer、Editor
- [ ] 为每个 Agent 写详细的 System Prompt
- [ ] 定义 Agent 间的通信协议

**Agent 设计**：

```
┌─────────────────────────────────────────┐
│ 1. Researcher（研究员）                  │
│    职责：根据主题搜集资料                  │
│    工具：Web Search、Read URL            │
│    输出：资料摘要 + 关键观点              │
├─────────────────────────────────────────┤
│ 2. Writer（作者）                        │
│    职责：基于资料写文章                   │
│    工具：无（纯 LLM 生成）                │
│    输入：研究员的资料                     │
│    输出：初稿文章                        │
├─────────────────────────────────────────┤
│ 3. Reviewer（审校）                      │
│    职责：检查文章质量                     │
│    评估：准确性、逻辑性、可读性           │
│    输出：审校意见 + 修改建议              │
├─────────────────────────────────────────┤
│ 4. Editor（主编）                        │
│    职责：根据审校意见修改文章              │
│    工具：无                             │
│    输出：最终定稿                        │
└─────────────────────────────────────────┘
```

**代码实现（AutoGen）**：
```python
import autogen

# 配置 LLM
config_list = [
    {
        "model": "gpt-4o-mini",
        "api_key": "sk-...",
    }
]

llm_config = {
    "config_list": config_list,
    "temperature": 0.7,
    "timeout": 120,
}

# 1. Researcher Agent
researcher = autogen.AssistantAgent(
    name="Researcher",
    llm_config=llm_config,
    system_message="""你是一个专业的研究员。

职责：
- 根据用户给定的主题，搜集相关资料
- 使用 search_web 工具搜索信息
- 使用 read_url 工具阅读网页
- 输出结构化的资料摘要

输出格式：
## 主题：[主题]
## 关键事实：
1. ...
2. ...
## 主要观点：
1. ...
2. ...
## 参考资料：
- [标题] URL
""",
)

# 2. Writer Agent
writer = autogen.AssistantAgent(
    name="Writer",
    llm_config=llm_config,
    system_message="""你是一个专业的内容作者。

职责：
- 基于 Researcher 提供的资料，撰写文章
- 文章结构清晰、逻辑严谨
- 语言生动、有吸引力
- 长度：800-1200 字

输出：完整的文章，包含标题、开头、正文、结尾。""",
)

# 3. Reviewer Agent
reviewer = autogen.AssistantAgent(
    name="Reviewer",
    llm_config=llm_config,
    system_message="""你是一个严格的审校编辑。

职责：
- 检查文章的准确性（事实是否正确）
- 检查逻辑性（论证是否合理）
- 检查可读性（语言是否流畅）
- 给出具体的修改建议

输出格式：
## 总评：[优秀/良好/及格/不及格]
## 优点：
- ...
## 问题：
- ...
## 修改建议：
- ...
""",
)

# 4. Editor Agent
editor = autogen.AssistantAgent(
    name="Editor",
    llm_config=llm_config,
    system_message="""你是一个主编。

职责：
- 根据 Reviewer 的审校意见修改文章
- 综合考虑可读性和准确性
- 输出最终定稿""",
)
```

---

#### Step 3：实现顺序执行流程（4 小时）

**任务清单**：
- [ ] 创建 User Proxy（模拟用户/协调者）
- [ ] 实现顺序执行：Researcher → Writer → Reviewer → Editor
- [ ] 测试完整流程

**AutoGen 实现**：
```python
# User Proxy（用户代理）
user_proxy = autogen.UserProxyAgent(
    name="User",
    human_input_mode="TERMINATE",  # 不需要人工干预
    max_consecutive_auto_reply=10,
    is_termination_msg=lambda x: "TERMINATE" in x.get("content", ""),
    code_execution_config=False,
)

# 顺序执行流程
def run_pipeline(topic: str) -> str:
    """运行完整的内容生产流水线"""

    # Step 1: 研究
    print("\n" + "="*50)
    print("📚 Step 1: Researcher 开始研究")
    print("="*50)
    user_proxy.initiate_chat(
        researcher,
        message=f"请研究以下主题：{topic}"
    )

    # Step 2: 写作
    print("\n" + "="*50)
    print("✍️ Step 2: Writer 开始写作")
    print("="*50)

    # 获取 Researcher 的输出
    research_result = researcher.last_message()["content"]

    user_proxy.initiate_chat(
        writer,
        message=f"""基于以下研究资料，撰写一篇文章：

主题：{topic}

研究资料：
{research_result}

请开始写作。"""
    )

    # Step 3: 审校
    print("\n" + "="*50)
    print("🔍 Step 3: Reviewer 开始审校")
    print("="*50)

    article = writer.last_message()["content"]

    user_proxy.initiate_chat(
        reviewer,
        message=f"""请审校以下文章：

{article}

请给出审校意见。"""
    )

    # Step 4: 修改
    print("\n" + "="*50)
    print("📝 Step 4: Editor 开始修改")
    print("="*50)

    review = reviewer.last_message()["content"]

    user_proxy.initiate_chat(
        editor,
        message=f"""根据以下审校意见修改文章：

原文章：
{article}

审校意见：
{review}

请输出修改后的最终版本。"""
    )

    final_article = editor.last_message()["content"]
    return final_article

# 测试
article = run_pipeline("人工智能对教育行业的影响")
print("\n" + "="*50)
print("📄 最终文章：")
print(article)
```

**CrewAI 实现（更简洁）**：
```python
from crewai import Agent, Task, Crew

# 定义 Agent
researcher = Agent(
    role='研究员',
    goal='搜集主题相关的资料',
    backstory='你是一个专业的研究员，擅长搜集和整理信息。',
    verbose=True,
)

writer = Agent(
    role='作者',
    goal='基于资料撰写文章',
    backstory='你是一个经验丰富的内容作者，擅长把复杂信息写得通俗易懂。',
    verbose=True,
)

reviewer = Agent(
    role='审校',
    goal='检查文章质量并给出修改建议',
    backstory='你是一个严格的审校编辑，对文章质量有高要求。',
    verbose=True,
)

editor = Agent(
    role='主编',
    goal='根据审校意见修改文章',
    backstory='你是一个主编，擅长打磨文章。',
    verbose=True,
)

# 定义任务
research_task = Task(
    description='研究主题：{topic}。搜集相关资料和观点。',
    agent=researcher,
    expected_output='结构化的资料摘要'
)

write_task = Task(
    description='基于研究资料撰写一篇 1000 字的文章。',
    agent=writer,
    expected_output='完整的文章初稿',
    context=[research_task]  # 依赖 research_task 的输出
)

review_task = Task(
    description='审校文章，检查准确性、逻辑性、可读性。',
    agent=reviewer,
    expected_output='审校意见和修改建议',
    context=[write_task]
)

edit_task = Task(
    description='根据审校意见修改文章，输出最终版本。',
    agent=editor,
    expected_output='最终定稿',
    context=[review_task, write_task]
)

# 创建 Crew
crew = Crew(
    agents=[researcher, writer, reviewer, editor],
    tasks=[research_task, write_task, review_task, edit_task],
    verbose=2,
)

# 执行
result = crew.kickoff(inputs={'topic': '人工智能对教育行业的影响'})
print(result)
```

---

#### Step 4：构建 Web 界面（2 小时）

**任务清单**：
- [ ] 用 Streamlit 构建交互界面
- [ ] 实时显示每个 Agent 的输出
- [ ] 支持下载最终文章

**Streamlit 代码**：
```python
import streamlit as st

st.title("🤖 多 Agent 内容生成系统")
topic = st.text_input("请输入文章主题", placeholder="例如：人工智能对教育行业的影响")

if st.button("开始生成") and topic:
    # 创建进度条
    progress = st.progress(0)
    status = st.empty()

    # Step 1: 研究
    status.text("📚 Researcher 正在研究...")
    progress.progress(25)
    # ... 调用 Agent ...

    with st.expander("📚 研究资料", expanded=True):
        st.write(research_result)

    # Step 2: 写作
    status.text("✍️ Writer 正在写作...")
    progress.progress(50)
    # ...

    with st.expander("✍️ 文章初稿", expanded=False):
        st.write(article)

    # Step 3: 审校
    status.text("🔍 Reviewer 正在审校...")
    progress.progress(75)
    # ...

    with st.expander("🔍 审校意见", expanded=False):
        st.write(review)

    # Step 4: 修改
    status.text("📝 Editor 正在修改...")
    progress.progress(100)
    # ...

    st.subheader("📄 最终文章")
    st.write(final_article)

    # 下载
    st.download_button(
        "📥 下载文章",
        final_article,
        file_name=f"{topic}.md"
    )
```

---

#### Step 5：错误处理与日志（2 小时）

**任务清单**：
- [ ] 记录每个 Agent 的执行日志
- [ ] Token 消耗统计
- [ ] 失败重试机制

**实现**：
```python
import logging
import time

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('multi_agent.log'),
        logging.StreamHandler()
    ]
)

class AgentLogger:
    """Agent 执行日志"""

    def __init__(self):
        self.logs = []
        self.total_tokens = 0

    def log(self, agent_name: str, action: str, **kwargs):
        """记录日志"""
        log_entry = {
            "timestamp": time.time(),
            "agent": agent_name,
            "action": action,
            **kwargs
        }
        self.logs.append(log_entry)
        logging.info(f"[{agent_name}] {action}")

    def get_summary(self) -> dict:
        """获取执行摘要"""
        return {
            "total_steps": len(self.logs),
            "agents_involved": list(set(l["agent"] for l in self.logs)),
            "duration": self.logs[-1]["timestamp"] - self.logs[0]["timestamp"] if self.logs else 0
        }

# 使用
logger = AgentLogger()
logger.log("Researcher", "started", topic=topic)
# ...
```

---

### 3.2 挑战版任务（选做 2 个，6-10 小时）

#### 挑战 1：并行执行

**任务**：
- [ ] 多个 Researcher 同时研究不同子主题
- [ ] Writer 基于所有研究结果写文章

**实现**：
```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

class ParallelResearcher:
    """并行研究员：多个 Researcher 同时工作"""

    def __init__(self, num_workers: int = 3):
        self.num_workers = num_workers
        self.researchers = [
            autogen.AssistantAgent(
                name=f"Researcher_{i}",
                llm_config=llm_config,
                system_message=f"你是研究员 {i+1}，负责研究主题的一个子方向。"
            )
            for i in range(num_workers)
        ]

    def parallel_research(self, topic: str, subtopics: list) -> list:
        """并行研究多个子主题"""
        results = []

        with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
            futures = [
                executor.submit(self._research_subtopic, researcher, topic, subtopic)
                for researcher, subtopic in zip(self.researchers, subtopics)
            ]
            results = [f.result() for f in futures]

        return results

    def _research_subtopic(self, researcher, main_topic, subtopic):
        """研究一个子主题"""
        user_proxy = autogen.UserProxyAgent(
            name="User",
            human_input_mode="TERMINATE",
            max_consecutive_auto_reply=1
        )
        user_proxy.initiate_chat(
            researcher,
            message=f"研究主题 '{main_topic}' 的子方向：'{subtopic}'"
        )
        return researcher.last_message()["content"]

# 使用
parallel_researcher = ParallelResearcher(num_workers=3)
subtopics = ["技术发展", "应用场景", "未来趋势"]
results = parallel_researcher.parallel_research("AI 教育", subtopics)
# results: ['技术发展资料', '应用场景资料', '未来趋势资料']
```

---

#### 挑战 2：条件分支（审校不通过打回重写）

**任务**：
- [ ] Reviewer 评分 < 70 分时，Writer 重新写
- [ ] 最多重写 3 次

**实现**：
```python
class ConditionalPipeline:
    """带条件分支的流水线"""

    def __init__(self):
        self.max_rewrites = 3
        self.passing_score = 70

    def run(self, topic: str) -> str:
        research = self.research(topic)

        for attempt in range(self.max_rewrites):
            print(f"\n✍️ 第 {attempt+1} 次写作")

            # 写作
            article = self.write(topic, research)

            # 审校
            review = self.review(article)
            score = self._extract_score(review)

            print(f"📊 审校评分：{score}/100")

            if score >= self.passing_score:
                print("✅ 审校通过")
                return article
            else:
                print(f"❌ 评分不足 {self.passing_score}，重新写作")

        print("⚠️ 达到最大重试次数，返回最佳版本")
        return article

    def _extract_score(self, review: str) -> int:
        """从审校意见中提取分数"""
        import re
        match = re.search(r'(\d+)\s*/\s*100', review)
        return int(match.group(1)) if match else 0
```

---

#### 挑战 3：人工审核节点

**任务**：
- [ ] 在关键节点暂停，等待人工审核
- [ ] 人工可以修改 Agent 的输出

**AutoGen 实现**：
```python
user_proxy = autogen.UserProxyAgent(
    name="User",
    human_input_mode="ALWAYS",  # 始终需要人工输入
    max_consecutive_auto_reply=0,
)

# 在 review 后暂停
def run_with_human_review(topic: str):
    # 1. 自动研究
    research = run_research(topic)

    # 2. 人工审核研究资料
    print(f"\n📚 研究结果：\n{research}\n")
    human_input = input("是否修改？(y/n)")
    if human_input == "y":
        research = input("请输入修改后的资料：")

    # 3. 自动写作
    article = run_write(research)

    # 4. 人工审阅文章
    print(f"\n✍️ 文章初稿：\n{article}\n")
    human_input = input("是否发布？(y/n)")
    if human_input == "y":
        return article
    else:
        # 反馈给 Writer 重新写
        feedback = input("请提供修改意见：")
        article = run_rewrite(article, feedback)
        return article
```

---

#### 挑战 4：任务队列（Celery）

**任务**：
- [ ] 用 Celery 管理长任务
- [ ] 支持后台执行
- [ ] 任务状态查询

**实现**：
```python
from celery import Celery

app = Celery('multi_agent', broker='redis://localhost:6379/0')

@app.task(bind=True)
def generate_article_task(self, topic: str) -> str:
    """后台任务：生成文章"""
    self.update_state(state='PROGRESS', meta={'step': 'research'})

    # 研究
    research = run_research(topic)
    self.update_state(state='PROGRESS', meta={'step': 'write'})

    # 写作
    article = run_write(research)
    self.update_state(state='PROGRESS', meta={'step': 'review'})

    # 审校
    review = run_review(article)
    self.update_state(state='PROGRESS', meta={'step': 'edit'})

    # 修改
    final = run_edit(article, review)
    return final

# 启动任务
from generate_article_task import generate_article_task
result = generate_article_task.delay("AI 教育")
task_id = result.id

# 查询状态
from celery.result import AsyncResult
res = AsyncResult(task_id)
print(res.state)  # PENDING / PROGRESS / SUCCESS
print(res.result)  # 最终结果
```

---

#### 挑战 5：Agent 性能监控

**任务**：
- [ ] 监控每个 Agent 的 Token 消耗
- [ ] 监控每个 Agent 的耗时
- [ ] 生成监控 Dashboard

**实现**：
```python
class AgentMetrics:
    """Agent 性能指标"""

    def __init__(self):
        self.metrics = []

    def record(self, agent: str, tokens: int, duration: float):
        """记录指标"""
        self.metrics.append({
            "agent": agent,
            "tokens": tokens,
            "duration": duration,
            "timestamp": time.time()
        })

    def get_report(self) -> pd.DataFrame:
        """生成报告"""
        df = pd.DataFrame(self.metrics)
        report = df.groupby("agent").agg({
            "tokens": ["sum", "mean"],
            "duration": ["sum", "mean"]
        })
        return report

# 使用
metrics = AgentMetrics()
metrics.record("Researcher", tokens=1500, duration=15.2)
metrics.record("Writer", tokens=2000, duration=20.5)
# ...

# Streamlit Dashboard
st.dataframe(metrics.get_report())
```

---

## 四、踩坑经验汇总

### 坑 1：Agent 陷入循环对话

**现象**：两个 Agent 互相回复，陷入死循环  
**原因**：没有终止条件  
**解决**：
```python
# 设置最大对话轮次
user_proxy = autogen.UserProxyAgent(
    name="User",
    max_consecutive_auto_reply=5,  # 最多 5 轮
    is_termination_msg=lambda x: "TERMINATE" in x.get("content", ""),
)
```

### 坑 2：上下文窗口爆炸

**现象**：多轮对话后 Token 消耗激增  
**原因**：每个 Agent 都把之前所有对话加载到 Context  
**解决**：
- 用摘要压缩（每 5 轮做一次摘要）
- 清理不必要的对话历史

### 坑 3：Agent 输出格式不一致

**现象**：Writer 输出格式有时是 Markdown，有时是纯文本  
**解决**：
```python
# 在 System Prompt 里明确格式
writer = autogen.AssistantAgent(
    name="Writer",
    system_message="""...
    输出格式要求：
    - 严格使用 Markdown 格式
    - 标题用 # 二级标题
    - 段落之间空一行
    ..."""
)
```

### 坑 4：成本失控

**现象**：一次内容生成消耗 $5+  
**原因**：多个 Agent 串行调用，Token 累积  
**解决**：
- 用更便宜的模型（GPT-4o-mini 即可）
- 限制每个 Agent 的输出长度
- 监控每个 Agent 的 Token 消耗

### 坑 5：框架选择纠结

**现象**：AutoGen vs CrewAI 不知道选哪个  
**建议**：
- 学习原理：选 AutoGen（更灵活，代码可控）
- 快速开发：选 CrewAI（API 简洁）
- 生产项目：两个都熟悉，根据场景选择

---

## 五、评估标准详解

### 及格（60 分）

- [ ] 4 个 Agent 定义清晰
- [ ] 顺序执行流程跑通
- [ ] 能输出 800+ 字文章
- [ ] 代码可运行

### 良好（75 分）

在及格基础上：
- [ ] 错误处理完善
- [ ] Web 界面可用
- [ ] 日志和监控
- [ ] 文章质量稳定

### 优秀（90 分）

在良好基础上：
- [ ] 完成了至少 3 个挑战任务
- [ ] 并行执行（多个 Researcher）
- [ ] 条件分支（审校不通过重写）
- [ ] 人工审核节点
- [ ] 有技术博客讲解多 Agent 架构

---

## 六、扩展学习

### 6.1 推荐阅读

- **AutoGen 论文**：AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation
- **CrewAI 文档**：https://docs.crewai.com
- **LangGraph**：另一个多 Agent 框架（更底层）

### 6.2 进阶方向

- **MetaGPT**：模拟软件公司多角色协作
- **ChatDev**：模拟软件开发流程
- **AgentVerse**：多 Agent 群组研究

---

## 七、交付物清单

- [ ] **代码仓库**（GitHub）
  - 4 个 Agent 定义
  - 流水线代码
  - Streamlit 界面
  - README.md
- [ ] **演示视频**（7-10 分钟）
  - 输入主题
  - 展示每个 Agent 的输出
  - 展示最终文章
- [ ] **架构文档**（可选）
  - 多 Agent 协作流程图
  - 关键技术决策
  - 踩坑经验
- [ ] **技术博客**（可选，2000 字）
  - 多 Agent 系统设计
  - 框架对比
  - 实战经验

---

**下一步**：完成本项目后，进入 Phase 3 的 [项目 7：容器化与部署](../../Phase3-生产工程/项目7-容器化与部署/README.md)
