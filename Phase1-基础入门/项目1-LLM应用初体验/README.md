# 项目 1：LLM 应用初体验 —— 文档问答 Web 应用

> **阶段**：Phase 1 - 基础入门
> **周次**：Week 1-2
> **难度**：⭐⭐
> **预估工时**：15-20 小时

---

## 一、项目目标

构建一个 Web 应用，用户可以上传 PDF 文档，然后基于文档内容进行问答。

**核心能力培养**：
- LLM API 调用能力
- Prompt 设计基础
- Web 界面开发（Streamlit）
- 错误处理与成本意识

---

## 二、详细任务说明

### 2.1 基础版任务（必做，10-12 小时）

#### Step 1：环境准备（1 小时）

**任务清单**：
- [ ] 安装 Python 3.10+
- [ ] 创建虚拟环境：`python -m venv venv`
- [ ] 激活虚拟环境：`source venv/bin/activate`（macOS/Linux）
- [ ] 安装依赖：`pip install openai streamlit pypdf2`
- [ ] 注册 OpenAI 账号，获取 API Key
- [ ] 设置环境变量：`export OPENAI_API_KEY="sk-..."`

**验证标准**：
```python
# test_api.py
from openai import OpenAI
client = OpenAI()
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Hello!"}]
)
print(response.choices[0].message.content)
```

能正常输出"Hello!"的回复就算成功。

---

#### Step 2：实现 PDF 文本提取（2 小时）

**任务清单**：
- [ ] 用 PyPDF2 读取 PDF 文件
- [ ] 提取所有页面的文本
- [ ] 处理特殊情况（扫描件 PDF 怎么办？提示用户）
- [ ] 加入异常处理（加密 PDF、损坏 PDF）

**参考代码**：
```python
import PyPDF2

def extract_pdf_text(pdf_file) -> str:
    """提取 PDF 文本"""
    reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text
```

**踩坑提醒**：
- 扫描件 PDF 提取出来是空的，需要 OCR（pytesseract）
- 部分 PDF 提取的文本顺序错乱，需要后续处理
- 超大 PDF（>100 页）需要切分，避免超出 Token 限制

---

#### Step 3：设计 Prompt 模板（2 小时）

**任务清单**：
- [ ] 设计 System Prompt：告诉 LLM 角色和任务
- [ ] 设计用户输入模板：注入文档内容 + 用户问题
- [ ] 思考：如何让 LLM "只回答基于文档的问题"？

**Prompt 示例**：
```python
SYSTEM_PROMPT = """你是一个文档问答助手。
- 只根据提供的文档内容回答问题
- 如果文档中没有相关信息，请明确说"文档中没有提到这个问题"
- 回答时引用原文（标注页码或段落）
- 保持简洁，不要编造内容"""

USER_PROMPT_TEMPLATE = """文档内容：
{document_content}

用户问题：{user_question}

请基于以上文档回答："""
```

**学习要点**：
- System Prompt 用于设定角色和行为准则
- User Prompt 模板用 `{}` 占位符，便于动态注入
- 明确告诉 LLM "不知道就说不知道"，减少幻觉

---

#### Step 4：实现对话功能（3 小时）

**任务清单**：
- [ ] 调用 OpenAI Chat Completions API
- [ ] 维护对话历史（多轮对话）
- [ ] 处理流式输出（可选）
- [ ] 加入错误处理（API 限流、网络错误）

**参考代码**：
```python
from openai import OpenAI

client = OpenAI()

def chat(messages: list) -> str:
    """调用 LLM 进行对话"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"调用失败：{str(e)}"
```

**对话历史管理**：
```python
# 使用 session_state 保存对话历史
if "messages" not in st.session_state:
    st.session_state.messages = []

# 添加用户消息
st.session_state.messages.append({
    "role": "user",
    "content": USER_PROMPT_TEMPLATE.format(
        document_content=pdf_text,
        user_question=user_input
    )
})

# 调用 LLM
response = chat(st.session_state.messages)

# 添加助手回复
st.session_state.messages.append({
    "role": "assistant",
    "content": response
})
```

---

#### Step 5：构建 Streamlit 界面（2 小时）

**任务清单**：
- [ ] 文件上传组件：`st.file_uploader`
- [ ] 聊天界面：`st.chat_message`、`st.chat_input`
- [ ] 显示对话历史
- [ ] 加入"清空对话"按钮

**完整代码示例**：
```python
import streamlit as st
from openai import OpenAI
import PyPDF2

st.set_page_config(page_title="文档问答助手", page_icon="📚")
st.title("📚 文档问答助手")

# 初始化 session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pdf_text" not in st.session_state:
    st.session_state.pdf_text = ""

# 侧边栏：上传文档
with st.sidebar:
    st.header("📄 上传文档")
    pdf_file = st.file_uploader("选择 PDF 文件", type=["pdf"])
    if pdf_file:
        reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
        st.session_state.pdf_text = text
        st.success(f"✅ 已加载 {len(reader.pages)} 页")

# 主界面：聊天
if not st.session_state.pdf_text:
    st.info("👈 请先在侧边栏上传 PDF 文档")
else:
    # 显示历史消息
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    # 用户输入
    if user_input := st.chat_input("请输入你的问题"):
        # 显示用户消息
        st.chat_message("user").write(user_input)

        # 调用 LLM
        client = OpenAI()
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_PROMPT_TEMPLATE.format(
                document_content=st.session_state.pdf_text,
                user_question=user_input
            )}
        ]
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages
        )
        answer = response.choices[0].message.content

        # 显示助手回复
        st.chat_message("assistant").write(answer)

        # 保存到历史
        st.session_state.messages.append({"role": "user", "content": user_input})
        st.session_state.messages.append({"role": "assistant", "content": answer})
```

---

### 2.2 挑战版任务（选做 2 个，5-8 小时）

#### 挑战 1：支持多个 PDF 同时上传

**任务**：
- [ ] 允许用户上传多个 PDF
- [ ] 合并所有 PDF 的文本
- [ ] 显示已上传的文档列表
- [ ] 支持删除某个文档

**实现思路**：
```python
uploaded_files = st.file_uploader("选择 PDF 文件", type=["pdf"], accept_multiple_files=True)

if uploaded_files:
    all_text = ""
    for pdf in uploaded_files:
        reader = PyPDF2.PdfReader(pdf)
        all_text += f"\n\n=== {pdf.name} ===\n\n"
        for page in reader.pages:
            all_text += page.extract_text()
    st.session_state.pdf_text = all_text
```

**踩坑提醒**：
- 多个大 PDF 合并后可能超出 Token 限制
- 解决方案：只把和问题最相关的部分注入 Context（这其实是 RAG 的雏形）

---

#### 挑战 2：答案引用原文位置

**任务**：
- [ ] LLM 回答时标注"答案来自第 X 页"
- [ ] 在界面上高亮显示原文片段

**Prompt 改造**：
```python
USER_PROMPT_TEMPLATE = """文档内容：
{document_content}

用户问题：{user_question}

请基于以上文档回答，并在答案后面标注信息来源（页码或段落）。
格式：
答案：[你的回答]
来源：第 X 页 / 第 X 段"""
```

**进阶版**：用 PDF.js 在前端高亮显示原文

---

#### 挑战 3：流式输出

**任务**：
- [ ] LLM 逐字输出，模拟打字机效果
- [ ] 提升用户体验

**实现代码**：
```python
stream = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=messages,
    stream=True
)

# 在 Streamlit 中实现流式输出
placeholder = st.empty()
full_response = ""
for chunk in stream:
    if chunk.choices[0].delta.content:
        full_response += chunk.choices[0].delta.content
        placeholder.write(full_response)
```

---

#### 挑战 4：Token 监控

**任务**：
- [ ] 实时显示本次对话消耗的 Token
- [ ] 累计统计总消耗
- [ ] 预估成本

**实现代码**：
```python
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=messages
)

# 获取 Token 用量
usage = response.usage
st.sidebar.metric("本次 Token", usage.total_tokens)
st.sidebar.metric("预估成本", f"${usage.total_tokens * 0.15 / 1_000_000:.6f}")
```

---

#### 挑战 5：对话历史导出

**任务**：
- [ ] 一键导出对话历史为 Markdown
- [ ] 一键导出为 PDF

**Markdown 导出**：
```python
def export_to_markdown(messages: list) -> str:
    md = "# 对话记录\n\n"
    for msg in messages:
        role = "👤 用户" if msg["role"] == "user" else "🤖 助手"
        md += f"## {role}\n\n{msg['content']}\n\n"
    return md

if st.button("📥 导出对话"):
    md = export_to_markdown(st.session_state.messages)
    st.download_button("下载 Markdown", md, "conversation.md")
```

---

## 三、踩坑经验汇总

### 坑 1：扫描件 PDF 提取不到文字

**现象**：用 PyPDF2 提取的文本是空的  
**原因**：扫描件 PDF 里的"文字"其实是图片  
**解决**：
- 短期：提示用户"暂不支持扫描件"
- 长期：用 OCR（pytesseract、百度 OCR、Azure Read API）

### 坑 2：超出 Token 限制

**现象**：调用 API 时报错 "context_length_exceeded"  
**原因**：PDF 内容太多，超过了模型的 Context Window  
**解决**：
- 切分 PDF（每 N 页一组）
- 摘要压缩（让 LLM 先总结文档）
- 这其实是 RAG 系统的核心问题

### 坑 3：LLM 幻觉（胡编内容）

**现象**：LLM 回答了文档里没有的内容  
**原因**：LLM 倾向于"看起来合理"的回答，而不是"我不知道"  
**解决**：
- Prompt 明确要求"不知道就说不知道"
- 降低 temperature（设为 0）
- 加入验证步骤（先用 LLM 提取答案，再用 LLM 验证是否在文档中）

### 坑 4：API 调用慢

**现象**：用户点击后等很久才有响应  
**原因**：LLM 生成文本需要时间  
**解决**：
- 用流式输出（边生成边显示）
- 切换到更快的模型（GPT-4o-mini）
- 异步处理

### 坑 5：成本失控

**现象**：测试一天，账单突然涨到 $50  
**原因**：每次调用都把整个 PDF 塞进 Context  
**解决**：
- Token 监控
- 缓存相同问题
- 限制 Context 长度

---

## 四、评估标准详解

### 及格（60 分）

- [ ] 能上传 PDF 并提取文本
- [ ] 能调用 LLM API 完成问答
- [ ] 基础界面可用（上传 + 问答）
- [ ] 代码可运行，有 README

### 良好（75 分）

在及格基础上：
- [ ] 支持多轮对话
- [ ] 错误处理完善（API 失败、PDF 损坏等）
- [ ] 代码结构清晰（函数、类、模块化）
- [ ] 有简单的演示视频

### 优秀（90 分）

在良好基础上：
- [ ] 完成了至少 3 个挑战任务
- [ ] 流式输出 + Token 监控
- [ ] 有技术博客（讲清楚原理）
- [ ] 界面美观，用户体验好
- [ ] 代码有单元测试

---

## 五、扩展学习

完成本项目后，建议深入学习：

1. **RAG 原理**（为项目 3 打基础）
   - Embedding 模型是什么？
   - 向量检索如何工作？
   - 文档切分策略

2. **Prompt 工程进阶**
   - Chain-of-Thought
   - Few-Shot Learning
   - ReAct 模式

3. **Token 优化**
   - 如何减少 Token 消耗？
   - 缓存策略设计
   - 上下文压缩

---

## 六、交付物清单

- [ ] **代码仓库**（GitHub）
  - 完整可运行代码
  - requirements.txt
  - .gitignore
  - README.md
- [ ] **演示视频**（5 分钟以内）
  - 展示上传 PDF
  - 展示问答效果
  - 展示多轮对话
- [ ] **技术博客**（可选，1000 字以上）
  - 项目背景
  - 技术选型 rationale
  - 核心代码讲解
  - 踩坑经验

---

**下一步**：完成本项目后，进入 [项目 2：工具调用 Agent](../项目2-工具调用Agent/README.md)
