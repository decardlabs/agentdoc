# 项目 4：有记忆的对话 Agent

> **阶段**：Phase 2 - 系统构建
> **周次**：Week 5
> **难度**：⭐⭐⭐
> **预估工时**：12-15 小时

---

## 一、项目目标

在项目 2 的基础上，加入长期记忆能力。Agent 能记住用户的历史对话、偏好、习惯。

**核心能力培养**：
- 短期记忆 vs 长期记忆
- 对话历史压缩策略
- 向量检索在记忆中的应用
- 用户画像构建
- Redis / PostgreSQL 持久化

---

## 二、记忆系统设计

### 为什么需要记忆？

**问题**：
- 每次对话都是"全新"的，Agent 不记得用户
- 上下文窗口有限，无法保留所有历史
- 用户每次都要重复说明背景信息

**解决**：构建记忆系统，让 Agent 能"记住"用户

### 记忆的分类

```
记忆系统
├── 短期记忆（Short-term）
│   └── 当前会话的对话历史
│   └── 存储：内存 / Redis
│
├── 长期记忆（Long-term）
│   ├── 情节记忆（Episodic）
│   │   └── "用户上周问过 XXX"
│   ├── 语义记忆（Semantic）
│   │   └── "用户是一名 Python 开发者"
│   └── 程序记忆（Procedural）
│       └── "用户喜欢详细回答"
│
└── 工作记忆（Working）
    └── 当前任务的状态
```

### 记忆系统的架构

```
用户输入
   ↓
1. 加载相关记忆（短期 + 长期）
   ↓
2. 组装 Context（记忆 + 用户问题）
   ↓
3. LLM 生成回复
   ↓
4. 更新记忆（保存对话 + 提取关键信息）
   ↓
返回给用户
```

---

## 三、详细任务说明

### 3.1 基础版任务（必做，8-10 小时）

#### Step 1：环境准备（1 小时）

**任务清单**：
- [ ] 安装依赖：`pip install redis openai langchain`
- [ ] 安装并启动 Redis：`docker run -d -p 6379:6379 redis`
- [ ] 验证 Redis 连接

**Redis 安装（macOS）**：
```bash
brew install redis
brew services start redis
```

**Redis 安装（Docker）**：
```bash
docker run -d --name redis -p 6379:6379 redis:latest
```

**验证连接**：
```python
import redis
r = redis.Redis(host='localhost', port=6379, db=0)
r.ping()  # 返回 True 表示成功
```

---

#### Step 2：实现短期记忆（2 小时）

**任务清单**：
- [ ] 用 Redis 存储当前会话的对话历史
- [ ] 实现"最近 N 轮对话"窗口
- [ ] 会话管理（支持多用户、多会话）

**代码实现**：
```python
import redis
import json
from typing import List, Dict

class ShortTermMemory:
    """短期记忆：存储当前会话的对话历史"""

    def __init__(self, user_id: str, session_id: str, max_turns: int = 10):
        self.redis_client = redis.Redis(host='localhost', port=6379, db=0)
        self.user_id = user_id
        self.session_id = session_id
        self.max_turns = max_turns
        self.key = f"memory:short:{user_id}:{session_id}"

    def add_message(self, role: str, content: str):
        """添加一条消息"""
        message = json.dumps({"role": role, "content": content})
        self.redis_client.rpush(self.key, message)
        # 限制长度（只保留最近 N 轮）
        self.redis_client.ltrim(self.key, -self.max_turns * 2, -1)
        # 设置过期时间（24 小时）
        self.redis_client.expire(self.key, 86400)

    def get_messages(self) -> List[Dict]:
        """获取历史消息"""
        messages = self.redis_client.lrange(self.key, 0, -1)
        return [json.loads(m) for m in messages]

    def clear(self):
        """清空当前会话"""
        self.redis_client.delete(self.key)

# 使用示例
memory = ShortTermMemory(user_id="user_001", session_id="session_abc")
memory.add_message("user", "我叫小明")
memory.add_message("assistant", "你好小明！")
print(memory.get_messages())
# [{'role': 'user', 'content': '我叫小明'}, {'role': 'assistant', 'content': '你好小明！'}]
```

---

#### Step 3：实现对话摘要压缩（3 小时）

**任务清单**：
- [ ] 当对话超过 N 轮时，自动摘要早期对话
- [ ] 摘要存入 Redis
- [ ] 加载记忆时，摘要 + 近期对话一起返回

**为什么需要摘要？**
- Context 窗口有限（GPT-4o 是 128K，但成本高）
- 早期对话的信息密度低，可以压缩
- 保留关键信息，节省 Token

**代码实现**：
```python
from openai import OpenAI

class SummaryMemory:
    """摘要记忆：压缩早期对话"""

    def __init__(self, user_id: str, session_id: str, summary_threshold: int = 8):
        self.redis_client = redis.Redis(host='localhost', port=6379, db=0)
        self.client = OpenAI()
        self.user_id = user_id
        self.session_id = session_id
        self.summary_threshold = summary_threshold
        self.summary_key = f"memory:summary:{user_id}:{session_id}"
        self.turn_count_key = f"memory:turn_count:{user_id}:{session_id}"

    def should_summarize(self, current_turn: int) -> bool:
        """判断是否需要摘要（每 N 轮摘要一次）"""
        return current_turn > 0 and current_turn % self.summary_threshold == 0

    def summarize(self, messages: List[Dict]) -> str:
        """用 LLM 摘要对话"""
        conversation = "\n".join([
            f"{msg['role']}: {msg['content']}"
            for msg in messages
        ])

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "请将以下对话摘要为 100 字以内的关键信息，保留用户偏好、重要事实、关键决策。"
                },
                {
                    "role": "user",
                    "content": conversation
                }
            ]
        )
        return response.choices[0].message.content

    def update_summary(self, new_messages: List[Dict]):
        """更新摘要"""
        old_summary = self.redis_client.get(self.summary_key)
        old_summary = old_summary.decode() if old_summary else ""

        # 把旧摘要 + 新消息一起摘要
        all_content = f"之前的摘要：{old_summary}\n\n新的对话：\n"
        all_content += "\n".join([
            f"{msg['role']}: {msg['content']}"
            for msg in new_messages
        ])

        new_summary = self.summarize([{"role": "user", "content": all_content}])
        self.redis_client.set(self.summary_key, new_summary, ex=86400)

    def get_summary(self) -> str:
        """获取摘要"""
        summary = self.redis_client.get(self.summary_key)
        return summary.decode() if summary else ""
```

---

#### Step 4：记忆用户基本信息（2 小时）

**任务清单**：
- [ ] 从对话中提取用户信息（姓名、职业、偏好）
- [ ] 存储到 Redis（用户画像）
- [ ] 新对话开始时，自动加载

**实现思路**：
```python
class UserProfile:
    """用户画像：存储用户的基本信息"""

    def __init__(self, user_id: str):
        self.redis_client = redis.Redis(host='localhost', port=6379, db=0)
        self.user_id = user_id
        self.key = f"profile:{user_id}"

    def set_attribute(self, key: str, value: str):
        """设置用户属性"""
        self.redis_client.hset(self.key, key, value)

    def get_attribute(self, key: str) -> str:
        """获取用户属性"""
        value = self.redis_client.hget(self.key, key)
        return value.decode() if value else None

    def get_all(self) -> Dict:
        """获取所有属性"""
        return {
            k.decode(): v.decode()
            for k, v in self.redis_client.hgetall(self.key).items()
        }

    def extract_and_update(self, messages: List[Dict]):
        """从对话中提取用户信息（用 LLM）"""
        conversation = "\n".join([
            f"{msg['role']}: {msg['content']}"
            for msg in messages
        ])

        client = OpenAI()
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """从以下对话中提取用户信息，输出 JSON 格式：
{
    "name": "用户姓名（如果提到）",
    "occupation": "职业（如果提到）",
    "preferences": "偏好（如果提到，如喜欢简短回答）",
    "other": "其他重要信息"
}
如果没有相关信息，字段值为 null。只输出 JSON，不要其他内容。"""
                },
                {
                    "role": "user",
                    "content": conversation
                }
            ]
        )

        try:
            import json
            info = json.loads(response.choices[0].message.content)
            for k, v in info.items():
                if v and v != "null":
                    self.set_attribute(k, v)
        except:
            pass

# 使用
profile = UserProfile("user_001")
profile.extract_and_update([
    {"role": "user", "content": "我叫小明，是一名 Python 开发者，喜欢简洁的回答。"},
    {"role": "assistant", "content": "好的小明，我记住了。"}
])
print(profile.get_all())
# {'name': '小明', 'occupation': 'Python 开发者', 'preferences': '简洁回答'}
```

---

#### Step 5：整合到 Agent（2 小时）

**任务清单**：
- [ ] 在调用 LLM 前，加载相关记忆
- [ ] 组装 Prompt（系统提示 + 用户画像 + 对话摘要 + 历史 + 当前问题）
- [ ] 对话结束后，更新记忆

**完整 Agent 代码**：
```python
class MemoryAgent:
    """有记忆的对话 Agent"""

    def __init__(self, user_id: str, session_id: str):
        self.user_id = user_id
        self.session_id = session_id
        self.short_memory = ShortTermMemory(user_id, session_id, max_turns=10)
        self.summary_memory = SummaryMemory(user_id, session_id)
        self.profile = UserProfile(user_id)
        self.client = OpenAI()
        self.turn_count = 0

    def chat(self, user_input: str) -> str:
        """对话主流程"""
        self.turn_count += 1

        # 1. 加载记忆
        profile = self.profile.get_all()
        summary = self.summary_memory.get_summary()
        history = self.short_memory.get_messages()

        # 2. 组装 System Prompt
        system_prompt = self._build_system_prompt(profile, summary)

        # 3. 组装 Messages
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history)
        messages.append({"role": "user", "content": user_input})

        # 4. 调用 LLM
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages
        )
        assistant_message = response.choices[0].message.content

        # 5. 保存到短期记忆
        self.short_memory.add_message("user", user_input)
        self.short_memory.add_message("assistant", assistant_message)

        # 6. 定期摘要
        if self.summary_memory.should_summarize(self.turn_count):
            old_messages = self.short_memory.get_messages()[:-self.summary_memory.summary_threshold * 2]
            if old_messages:
                self.summary_memory.update_summary(old_messages)

        # 7. 提取并更新用户画像
        self.profile.extract_and_update([
            {"role": "user", "content": user_input},
            {"role": "assistant", "content": assistant_message}
        ])

        return assistant_message

    def _build_system_prompt(self, profile: Dict, summary: str) -> str:
        """构建系统提示"""
        prompt = "你是一个智能助手，能够记住用户的信息和历史对话。\n\n"

        if profile:
            prompt += "## 用户信息\n"
            for k, v in profile.items():
                prompt += f"- {k}: {v}\n"
            prompt += "\n"

        if summary:
            prompt += f"## 之前的对话摘要\n{summary}\n\n"

        prompt += "请基于以上信息回答用户问题。"
        return prompt

# 使用
agent = MemoryAgent(user_id="user_001", session_id="session_001")
print(agent.chat("我叫小明，是一名 Python 开发者"))
print(agent.chat("我喜欢简洁的回答"))  # 第二次对话
# 注意：这里只是示例，实际需要保持同一个 session
```

---

### 3.2 挑战版任务（选做 2 个，5-8 小时）

#### 挑战 1：向量检索记忆

**任务**：
- [ ] 把历史对话 Embedding 存入向量数据库
- [ ] 新对话时，检索语义相关的历史对话
- [ ] 比"最近 N 轮"更智能

**实现**：
```python
import chromadb
from openai import OpenAI

class VectorMemory:
    """向量记忆：基于语义检索历史对话"""

    def __init__(self, user_id: str):
        self.client = chromadb.PersistentClient(path="./memory_db")
        self.collection = self.client.get_or_create_collection(f"memory_{user_id}")
        self.openai_client = OpenAI()

    def add_memory(self, content: str, metadata: Dict = None):
        """添加记忆"""
        # 生成 Embedding
        embedding = self._get_embedding(content)

        self.collection.add(
            embeddings=[embedding],
            documents=[content],
            metadatas=[metadata or {}],
            ids=[f"mem_{int(time.time() * 1000)}"]
        )

    def search(self, query: str, top_k: int = 3) -> List[str]:
        """检索相关记忆"""
        query_embedding = self._get_embedding(query)

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k
        )

        return results["documents"][0] if results["documents"] else []

    def _get_embedding(self, text: str) -> List[float]:
        """生成 Embedding"""
        response = self.openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding

# 使用
vector_mem = VectorMemory("user_001")
vector_mem.add_memory("用户喜欢简洁回答")
vector_mem.add_memory("用户是 Python 开发者")

# 检索
related = vector_mem.search("用户的编程语言")
print(related)  # ['用户是 Python 开发者', ...]
```

---

#### 挑战 2：用户画像系统

**任务**：
- [ ] 跟踪用户行为数据
- [ ] 自动构建用户标签（"技术爱好者"、"喜欢深度回答"）
- [ ] 根据画像调整回复风格

**实现**：
```python
class AdvancedUserProfile:
    """高级用户画像"""

    def __init__(self, user_id: str):
        self.redis_client = redis.Redis(host='localhost', port=6379, db=0)
        self.user_id = user_id

    def add_interaction(self, interaction_type: str, data: Dict):
        """记录一次交互"""
        key = f"interactions:{self.user_id}"
        interaction = {
            "type": interaction_type,
            "timestamp": int(time.time()),
            **data
        }
        self.redis_client.rpush(key, json.dumps(interaction))

    def get_behavior_patterns(self) -> Dict:
        """分析行为模式"""
        interactions = self.redis_client.lrange(f"interactions:{self.user_id}", 0, -1)
        interactions = [json.loads(i) for i in interactions]

        # 简单统计
        patterns = {
            "total_interactions": len(interactions),
            "preferred_topics": self._extract_topics(interactions),
            "active_hours": self._analyze_active_time(interactions),
            "avg_message_length": self._avg_message_length(interactions)
        }
        return patterns

    def _extract_topics(self, interactions: List[Dict]) -> List[str]:
        """提取用户关注的主题（用 LLM）"""
        # 简化：直接用 LLM 分析
        recent = [i.get("content", "") for i in interactions[-20:]]
        conversation = "\n".join(recent)

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": f"从以下对话中提取用户关注的 3-5 个主题，用逗号分隔：\n{conversation}"
            }]
        )
        return response.choices[0].message.content.split("，")
```

---

#### 挑战 3：记忆可视化

**任务**：
- [ ] 用 Streamlit 展示 Agent 记住了什么
- [ ] 用户可以编辑/删除记忆

**界面效果**：
```
┌─────────────────────────────────┐
│ 🧠 Agent 的记忆                │
├─────────────────────────────────┤
│ ## 用户画像                      │
│ - 姓名：小明                     │
│ - 职业：Python 开发者            │
│ - 偏好：简洁回答                 │
│                                 │
│ ## 最近的对话                    │
│ - 你好 → 你好小明！              │
│ - 我喜欢 Python → 好的...        │
│                                 │
│ ## 相关记忆（向量检索）          │
│ - [相似度 0.92] 你是...          │
│                                 │
│ [编辑] [删除] [清空]             │
└─────────────────────────────────┘
```

---

#### 挑战 4：记忆编辑功能

**任务**：
- [ ] 用户可以删除某段记忆（"忘掉我刚才说的"）
- [ ] 用户可以修改用户画像
- [ ] Agent 确认："已删除 XXX 记忆"

**实现**：
```python
# 在 Agent 中加入特殊命令处理
def chat(self, user_input: str) -> str:
    # 检测特殊命令
    if "忘掉" in user_input or "删除记忆" in user_input:
        return self._handle_forget_command(user_input)

    # 正常对话...

def _handle_forget_command(self, command: str) -> str:
    """处理遗忘命令"""
    if "全部" in command:
        self.short_memory.clear()
        self.summary_memory.clear()
        return "已清空所有记忆"

    if "上次" in command or "刚才" in command:
        # 删除最近一轮
        self.short_memory.redis_client.rpop(self.short_memory.key)
        self.short_memory.redis_client.rpop(self.short_memory.key)
        return "已删除最近的对话"

    return "抱歉，我没有理解要删除哪段记忆"
```

---

#### 挑战 5：跨会话记忆共享

**任务**：
- [ ] 多个 Agent 实例（不同 session）共享用户画像
- [ ] 每个 session 独立的短期记忆
- [ ] 共享的长期记忆（用户偏好、关键信息）

**架构**：
```
用户画像（共享）     ← 所有 session 共享
├── 姓名：小明
├── 职业：Python 开发者
└── 偏好：简洁回答

短期记忆（独立）     ← 每个 session 独立
├── Session 001
│   └── 你好 → 你好
├── Session 002
│   └── Python 怎么学 → ...
```

---

## 四、踩坑经验汇总

### 坑 1：Redis 内存爆炸

**现象**：Redis 占用内存越来越大  
**原因**：记忆没有过期时间，无限累积  
**解决**：
```python
# 设置过期时间
self.redis_client.expire(key, 86400)  # 24 小时过期
```

### 坑 2：摘要丢失关键信息

**现象**：摘要后，Agent 不记得某个关键细节  
**原因**：LLM 摘要会丢失细节  
**解决**：
- 摘要前用 LLM 提取"关键事实"（姓名、日期、数字等）
- 关键事实单独存储，不参与摘要

### 坑 3：用户画像污染

**现象**：用户画像里出现了错误信息（LLM 幻觉）  
**原因**：LLM 提取信息时编造  
**解决**：
- 提取后人工校验（至少在初期）
- 加入来源追溯（这条信息来自哪次对话）

### 坑 4：记忆加载慢

**现象**：每次对话都要加载所有记忆，耗时  
**原因**：记忆太多，每次都全量加载  
**解决**：
- 按需加载（只加载相关的）
- 缓存常用记忆
- 用向量检索代替全量加载

### 坑 5：跨平台同步问题

**现象**：本地和云端的记忆不一致  
**原因**：Redis 没有同步  
**解决**：
- 用云 Redis（阿里云、腾讯云）
- 定期备份

---

## 五、评估标准详解

### 及格（60 分）

- [ ] 短期记忆可用（记住当前会话）
- [ ] 基本摘要功能
- [ ] 跨会话能记住用户姓名等基本信息
- [ ] 代码可运行

### 良好（75 分）

在及格基础上：
- [ ] 摘要策略合理
- [ ] 用户画像自动提取
- [ ] 错误处理完善
- [ ] 演示了"第二次对话 Agent 记得第一次内容"

### 优秀（90 分）

在良好基础上：
- [ ] 完成了至少 3 个挑战任务
- [ ] 向量检索记忆
- [ ] 记忆可视化界面
- [ ] 用户可以编辑/删除记忆

---

## 六、交付物清单

- [ ] **代码仓库**（GitHub）
  - MemoryAgent 完整代码
  - Redis 配置说明
  - README.md
- [ ] **演示视频**（5 分钟）
  - 展示"第二次对话时，Agent 记得第一次的内容"
  - 展示用户画像
- [ ] **技术博客**（可选，1500 字）
  - 记忆系统设计
  - 摘要策略 trade-off
  - 踩坑经验

---

**下一步**：完成本项目后，进入 [项目 5：代码执行 Agent](../项目5-代码执行Agent/README.md)
