# 项目 3：RAG 系统 —— 技术文档助手

> **阶段**：Phase 1 - 基础入门
> **周次**：Week 4
> **难度**：⭐⭐⭐
> **预估工时**：12-18 小时

---

## 一、项目目标

为公司技术文档库（或任意文档集合）构建一个 RAG（检索增强生成）问答系统。

**核心能力培养**：
- RAG 全流程理解
- 文档切分策略
- 向量检索原理
- Embedding 模型应用
- RAG 评估方法

---

## 二、RAG 原理解析

### 为什么需要 RAG？

**问题**：LLM 不知道私有数据（公司文档、内部资料）  
**解决**：检索 + 生成（先找到相关信息，再让 LLM 基于这些信息回答）

### RAG 全流程

```
用户问题
   ↓
1. Embedding（把问题转成向量）
   ↓
2. 向量检索（在文档库里找最相关的 Top-K 个片段）
   ↓
3. 注入 Context（把检索到的片段 + 用户问题组成 Prompt）
   ↓
4. LLM 生成答案
   ↓
返回给用户
```

### RAG vs 直接问 LLM

| 场景 | 直接问 LLM | 用 RAG |
|------|-----------|--------|
| 问"什么是 Python？" | ✅ 能答 | ✅ 能答（杀鸡用牛刀） |
| 问"我们公司的报销流程？" | ❌ 不知道 | ✅ 能答（基于公司文档） |
| 实时信息 | ❌ 训练数据截止 | ✅ 可以接入实时文档 |
| 答案可追溯 | ❌ 来源不明 | ✅ 引用原文 |

---

## 三、详细任务说明

### 3.1 基础版任务（必做，10-12 小时）

#### Step 1：环境准备（1 小时）

**任务清单**：
- [ ] 安装依赖：`pip install llama-index chromadb openai`
- [ ] 准备 10+ 份文档（Markdown / PDF / HTML）
- [ ] 注册 OpenAI API Key

**依赖说明**：
- `llama-index`：RAG 框架（高级 API，开箱即用）
- `chromadb`：向量数据库（本地存储）
- `openai`：Embedding + LLM API

**文档准备建议**：
- 公司技术文档（API 文档、架构文档、流程文档）
- 开源项目 README
- 任何你想问答的文档集合
- 格式：优先 Markdown，PDF 也可以

---

#### Step 2：构建向量索引（4 小时）

**任务清单**：
- [ ] 用 LlamaIndex 加载文档
- [ ] 文档切分（默认按 Token 切分）
- [ ] 生成 Embedding（OpenAI text-embedding-3-small）
- [ ] 存储到 Chroma 向量数据库
- [ ] 持久化到本地（避免每次重建）

**完整代码**：
```python
import os
from llama_index.core import (
    VectorStoreIndex,
    SimpleDirectoryReader,
    StorageContext,
    load_index_from_storage,
    Settings
)
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.embeddings.openai import OpenAIEmbedding
import chromadb

# 1. 配置全局设置
Settings.embed_model = OpenAIEmbedding(
    model="text-embedding-3-small",
    api_key=os.getenv("OPENAI_API_KEY")
)
Settings.llm = None  # 暂时不用 LLM，只做检索测试

# 2. 加载文档
documents = SimpleDirectoryReader(
    "./docs",  # 文档目录
    required_exts=[".md", ".pdf", ".txt", ".html"]
).load_data()

print(f"✅ 加载了 {len(documents)} 份文档")

# 3. 切分文档（LlamaIndex 默认按 512 tokens 切分）
from llama_index.core.node_parser import SentenceSplitter
parser = SentenceSplitter(chunk_size=512, chunk_overlap=50)
nodes = parser.get_nodes_from_documents(documents)
print(f"✅ 切分为 {len(nodes)} 个片段")

# 4. 构建向量索引
chroma_client = chromadb.PersistentClient(path="./chroma_db")
chroma_collection = chroma_client.get_or_create_collection("docs")
vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
storage_context = StorageContext.from_defaults(vector_store=vector_store)

index = VectorStoreIndex(
    nodes,
    storage_context=storage_context,
    show_progress=True
)

print("✅ 向量索引构建完成")
```

**关键概念解释**：
- **Document**：一份完整文档
- **Node**：文档切分后的片段（chunk）
- **Embedding**：把文本转成向量（如 1536 维）
- **Vector Store**：存储向量的数据库（支持相似度搜索）

---

#### Step 3：实现检索与问答（3 小时）

**任务清单**：
- [ ] 配置 LLM（OpenAI GPT-4o-mini）
- [ ] 用 LlamaIndex 的 Query Engine 实现问答
- [ ] 设计自定义 Prompt（让 LLM 引用原文）
- [ ] 测试检索效果

**完整代码**：
```python
from llama_index.core import Settings
from llama_index.llms.openai import OpenAI
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.retrievers import VectorIndexRetriever

# 1. 配置 LLM
Settings.llm = OpenAI(
    model="gpt-4o-mini",
    api_key=os.getenv("OPENAI_API_KEY"),
    temperature=0.1  # 降低随机性，提高准确性
)

# 2. 加载已有索引（避免重复构建）
chroma_client = chromadb.PersistentClient(path="./chroma_db")
chroma_collection = chroma_client.get_or_create_collection("docs")
vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
index = VectorStoreIndex.from_vector_store(vector_store)

# 3. 创建检索器
retriever = VectorIndexRetriever(
    index=index,
    similarity_top_k=3  # 检索 Top 3 相关片段
)

# 4. 创建 Query Engine
query_engine = RetrieverQueryEngine.from_args(
    retriever=retriever,
    response_mode="compact"  # 紧凑模式：把多个片段合并
)

# 5. 自定义 Prompt（让 LLM 引用原文）
from llama_index.core.prompts import PromptTemplate

QA_PROMPT_TEMPLATE = """
你是一个技术文档助手。请基于以下上下文回答用户问题。

要求：
1. 只根据提供的上下文回答，不要编造内容
2. 如果上下文中没有相关信息，请明确说"文档中没有提到这个问题"
3. 回答时引用原文（标注来源文件名）
4. 保持简洁、准确

上下文信息：
{context_str}

用户问题：{query_str}

回答：
"""

query_engine.update_prompts(
    {"response_synthesizer:text_qa_template": PromptTemplate(QA_PROMPT_TEMPLATE)}
)

# 6. 测试问答
def ask(question: str):
    response = query_engine.query(question)
    print(f"\n❓ 问题: {question}")
    print(f"🤖 回答: {response}")

    # 显示引用的原文
    print("\n📚 引用来源:")
    for i, node in enumerate(response.source_nodes):
        print(f"  [{i+1}] {node.metadata.get('file_name', '未知')}: {node.text[:100]}...")

# 测试
ask("我们的部署流程是什么？")
ask("如何申请 API Key？")
```

---

#### Step 4：构建交互界面（2 小时）

**任务清单**：
- [ ] 用 Streamlit 构建 Web 界面
- [ ] 文件上传（支持增量添加文档）
- [ ] 问答界面
- [ ] 显示引用来源

**Streamlit 代码**：
```python
import streamlit as st
from llama_index.core import VectorStoreIndex, StorageContext
import chromadb
from llama_index.vector_stores.chroma import ChromaVectorStore

st.set_page_config(page_title="RAG 文档助手", page_icon="📚")
st.title("📚 技术文档问答助手")

# 初始化
@st.cache_resource
def load_index():
    """加载向量索引"""
    chroma_client = chromadb.PersistentClient(path="./chroma_db")
    chroma_collection = chroma_client.get_or_create_collection("docs")
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    return VectorStoreIndex.from_vector_store(vector_store)

index = load_index()

# 侧边栏：上传文档
with st.sidebar:
    st.header("📂 文档管理")
    uploaded_files = st.file_uploader(
        "上传新文档",
        type=["md", "pdf", "txt"],
        accept_multiple_files=True
    )
    if uploaded_files and st.button("添加到索引"):
        with st.spinner("处理中..."):
            # 保存到临时目录
            os.makedirs("./docs", exist_ok=True)
            for f in uploaded_files:
                with open(f"./docs/{f.name}", "wb") as out:
                    out.write(f.getbuffer())

            # 重建索引
            from llama_index.core import SimpleDirectoryReader
            documents = SimpleDirectoryReader("./docs").load_data()
            for doc in documents:
                index.insert(doc)
            st.success("✅ 已添加")

# 主界面：问答
query_engine = index.as_query_engine(similarity_top_k=3)

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

if user_input := st.chat_input("请输入你的问题"):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    with st.spinner("思考中..."):
        response = query_engine.query(user_input)

    with st.chat_message("assistant"):
        st.write(response.response)

        # 显示引用来源
        with st.expander("📚 查看引用来源"):
            for i, node in enumerate(response.source_nodes):
                st.markdown(f"**来源 [{i+1}]**: `{node.metadata.get('file_name', '未知')}`")
                st.text(node.text[:300] + "...")

    st.session_state.messages.append({"role": "assistant", "content": response.response})
```

---

### 3.2 挑战版任务（选做 2 个，5-8 小时）

#### 挑战 1：加入 Rerank 模型

**任务**：
- [ ] 第一阶段：向量检索 Top 20
- [ ] 第二阶段：用 Rerank 模型重新排序，取 Top 3
- [ ] 提升检索准确率

**实现**：
```python
# 安装：pip install sentence-transformers
from sentence_transformers import CrossEncoder

# 加载 Rerank 模型
rerank_model = CrossEncoder('BAAI/bge-reranker-base')

def rerank_results(query: str, retrieved_nodes: list, top_k: int = 3) -> list:
    """用 Rerank 模型重新排序"""
    # 准备数据
    pairs = [[query, node.text] for node in retrieved_nodes]

    # 预测相关性分数
    scores = rerank_model.predict(pairs)

    # 排序
    scored_nodes = list(zip(scores, retrieved_nodes))
    scored_nodes.sort(key=lambda x: x[0], reverse=True)

    return [node for score, node in scored_nodes[:top_k]]

# 使用
retrieved_nodes = retriever.retrieve(query)  # Top 20
reranked_nodes = rerank_results(query, retrieved_nodes, top_k=3)  # Rerank to Top 3
```

**效果对比**：
- 纯向量检索：准确率约 70%
- 向量检索 + Rerank：准确率约 85%

---

#### 挑战 2：混合检索（向量 + BM25）

**任务**：
- [ ] 向量检索：擅长语义理解
- [ ] 关键词检索（BM25）：擅长精确匹配
- [ ] 融合两种结果

**实现**：
```python
from llama_index.retrievers.bm25 import BM25Retriever
from llama_index.core.retrievers import QueryFusionRetriever

# 向量检索器
vector_retriever = VectorIndexRetriever(index=index, similarity_top_k=10)

# BM25 检索器
bm25_retriever = BM25Retriever.from_defaults(
    nodes=nodes,
    similarity_top_k=10
)

# 融合检索器
fusion_retriever = QueryFusionRetriever(
    retrievers=[vector_retriever, bm25_retriever],
    similarity_top_k=5,
    num_queries=1,  # 不做 query 改写
    mode="reciprocal_rerank"  # 倒数排名融合
)

# 使用
retrieved_nodes = fusion_retriever.retrieve("你的问题")
```

**适用场景**：
- 关键词很重要（如 API 名称、专有名词）：混合检索更准
- 语义理解重要（如"怎么处理错误"）：向量检索更准

---

#### 挑战 3：答案引用原文位置

**任务**：
- [ ] 答案后面标注"来自 [文件名] 第 X 段"
- [ ] 支持点击跳转到原文

**Prompt 改造**：
```python
QA_PROMPT_TEMPLATE = """
基于以下上下文回答问题，并标注信息来源。

上下文：
---
[来源 1] 文件名：api_docs.md，段落：第 12 段
{context_1}
---
[来源 2] 文件名：deploy_guide.md，段落：第 5 段
{context_2}
---

问题：{query_str}

回答格式：
答案：[你的回答]
来源：[列出引用的来源编号]
"""
```

---

#### 挑战 4：多文档联合问答

**任务**：
- [ ] 用户可以指定"综合 A 和 B 两个文档"
- [ ] 实现文档过滤检索

**实现**：
```python
# 为每个 Node 添加 metadata
for node in nodes:
    node.metadata["doc_name"] = "api_docs"  # 或 "deploy_guide"

# 检索时过滤
from llama_index.core.vector_stores import MetadataFilters, ExactMatchFilter

filters = MetadataFilters(
    filters=[
        ExactMatchFilter(key="doc_name", value="api_docs")
    ]
)

retriever = VectorIndexRetriever(
    index=index,
    similarity_top_k=3,
    filters=filters
)
```

---

#### 挑战 5：检索质量评估

**任务**：
- [ ] 构建测试集（问题 + 标准答案）
- [ ] 评估指标：Recall@K、MRR
- [ ] 自动化评估脚本

**评估指标**：
- **Recall@K**：Top-K 结果中包含正确答案的比例
- **MRR**（Mean Reciprocal Rank）：正确答案排名的倒数平均值

**代码示例**：
```python
test_set = [
    {
        "question": "如何申请 API Key？",
        "expected_doc": "api_docs.md",
        "expected_section": "API Key 申请"
    },
    # ... 更多测试用例
]

def evaluate(test_set, retriever):
    recall_at_3 = 0
    mrr = 0

    for item in test_set:
        retrieved = retriever.retrieve(item["question"])
        retrieved_docs = [node.metadata["file_name"] for node in retrieved[:3]]

        # Recall@3
        if item["expected_doc"] in retrieved_docs:
            recall_at_3 += 1

        # MRR
        for rank, doc in enumerate(retrieved_docs, 1):
            if doc == item["expected_doc"]:
                mrr += 1 / rank
                break

    return {
        "Recall@3": recall_at_3 / len(test_set),
        "MRR": mrr / len(test_set)
    }

results = evaluate(test_set, retriever)
print(results)
# {'Recall@3': 0.85, 'MRR': 0.78}
```

---

## 四、踩坑经验汇总

### 坑 1：检索不到相关内容

**现象**：明明文档里有，但 RAG 检索不到  
**原因**：
- 文档切分粒度太大（一个 chunk 包含多个主题）
- Embedding 模型不匹配（中文用英文 Embedding）
- 文档格式问题（PDF 提取的文本顺序错乱）

**解决**：
- 调小 chunk_size（如 256 tokens）
- 换用中文 Embedding（bge-large-zh-v1.5、text-embedding-3-small 也支持中文）
- 文档预处理（去除多余空白、特殊字符）

### 坑 2：LLM 幻觉（答案不在原文中）

**现象**：RAG 检索到了原文，但 LLM 还是瞎编  
**原因**：Prompt 没强调"只基于上下文回答"  
**解决**：
```python
QA_PROMPT_TEMPLATE = """严格基于以下上下文回答问题。

规则：
1. 只能使用上下文中的信息
2. 如果上下文不包含答案，必须回答"文档中没有相关信息"
3. 严禁编造任何上下文之外的内容

上下文：{context}

问题：{query}

回答："""
```

### 坑 3：检索速度慢

**现象**：每次问答要等 5-10 秒  
**原因**：
- 文档太多（百万级）
- Embedding 计算慢
- Chroma 没有索引

**解决**：
- 用更快的 Embedding 模型（bge-small）
- 启用向量索引（HNSW）
- 加入缓存（相同问题直接返回）

### 坑 4：Token 消耗大

**现象**：每次问答消耗 5000+ tokens  
**原因**：
- Top-K 太大（K=10）
- 检索到的片段太长
- LLM 把检索结果全部塞进 Context

**解决**：
- 调小 Top-K（3-5 即可）
- 检索后做摘要压缩
- 用更便宜的模型（GPT-4o-mini）

### 坑 5：增量更新困难

**现象**：每次新增文档都要重建整个索引  
**原因**：简单实现用的是 `from_documents`（全量构建）  
**解决**：
```python
# 增量添加文档
new_documents = SimpleDirectoryReader("./new_docs").load_data()
for doc in new_documents:
    index.insert(doc)  # 增量插入，不需要重建
```

---

## 五、评估标准详解

### 及格（60 分）

- [ ] 文档加载、Embedding、检索、生成全流程跑通
- [ ] 至少支持 10 份文档
- [ ] 基础问答功能可用
- [ ] 代码可运行

### 良好（75 分）

在及格基础上：
- [ ] Prompt 设计合理（引用原文、避免幻觉）
- [ ] 错误处理完善
- [ ] 文档切分策略有思考
- [ ] 有简单的演示

### 优秀（90 分）

在良好基础上：
- [ ] 完成了至少 3 个挑战任务
- [ ] Rerank + 混合检索
- [ ] 检索质量评估（Recall@K > 0.8）
- [ ] 有技术博客讲解 RAG 原理

---

## 六、进阶学习

完成本项目后，建议深入学习：

1. **Advanced RAG 技巧**
   - Query 改写（让问题更清晰）
   - HyDE（Hypothetical Document Embeddings）
   - Self-RAG（让 LLM 自己判断是否需要检索）

2. **向量数据库**
   - 深入了解 Chroma / Milvus / Weaviate
   - 索引算法（HNSW、IVF）

3. **Embedding 模型**
   - MTEB Leaderboard
   - Fine-tuning Embedding

4. **RAG 框架对比**
   - LlamaIndex vs LangChain
   - 自研 RAG vs 用框架

---

## 七、交付物清单

- [ ] **代码仓库**（GitHub）
  - 完整可运行代码
  - 文档数据（至少 10 份）
  - README.md
- [ ] **演示视频**（5 分钟）
  - 展示文档问答效果
  - 展示引用来源
- [ ] **检索质量报告**（可选）
  - Recall@K、MRR 指标
  - 优化前后对比

---

**下一步**：完成本项目后，进入 Phase 2 的 [项目 4：有记忆的对话 Agent](../../Phase2-系统构建/项目4-有记忆的对话Agent/README.md)
