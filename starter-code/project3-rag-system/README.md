# RAG 系统

> 智能体工程师培养计划 - Phase 1 项目 3
> 
> 构建一个完整的 RAG（检索增强生成）系统，实现基于私有知识库的智能问答

## 📋 项目简介

本项目是一个 **RAG 系统**，展示了如何结合向量检索和大语言模型，构建基于私有知识库的问答系统。

### 核心功能

- ✅ 多格式文档加载（PDF、TXT、MD）
- ✅ 文本智能切分
- ✅ 向量化（OpenAI Embedding）
- ✅ 向量检索（Chroma）
- ✅ Rerank（可选，提升精度）
- ✅ Prompt 构建（含引用）
- ✅ CLI 交互界面
- ✅ 评估功能

## 🏗️ 技术架构

### 技术栈

- **框架**: LlamaIndex（推荐）或手写
- **向量数据库**: Chroma（本地运行）
- **Embedding**: OpenAI text-embedding-3-small
- **LLM**: OpenAI API (gpt-4o-mini)
- **Rerank**: sentence-transformers（可选）

### 系统架构图

```
┌─────────────────────────────────────────────────────────────┐
│                          用户界面                            │
│                   (CLI / Web UI)                            │
└────────────────────┬──────────────────┬─────────────────────┘
                     │ 上传文档          │ 提问
                     ▼                  ▼
┌─────────────────────────────┐  ┌──────────────────────────┐
│   离线索引服务              │  │   在线问答服务            │
│                             │  │                          │
│  ┌────────┐  ┌────────┐    │  │  ┌────────┐  ┌────────┐  │
│  │ 加载器 │→ │ 切分器 │    │  │  │Query   │→ │Embedding│ │
│  └────────┘  └────┬───┘    │  │  │改写器  │  │模型    │  │
│                   │        │  │  └────────┘  └───┬────┘  │
│                   ▼        │  │                  │       │
│              ┌────────┐    │  │                  ▼       │
│              │Embedding│   │  │            ┌──────────┐  │
│              │模型    │    │  │            │ 向量检索 │  │
│              └───┬────┘    │  │            └────┬─────┘  │
│                  │         │  │                 │        │
│                  ▼         │  │                 ▼        │
│          ┌──────────────┐  │  │          ┌──────────┐    │
│          │  向量数据库  │  │  │          │ Reranker │    │
│          │  (Chroma)    │  │  │          │ (可选)   │    │
│          │              │  │  │          └────┬─────┘    │
│          │  - 文档向量  │  │  │               │          │
│          │  - 元数据    │  │  │               ▼          │
│          └──────────────┘  │  │        ┌──────────────┐  │
│                             │  │        │ LLM 生成器   │  │
│                             │  │        │ + Prompt 构造│  │
│                             │  │        └──────┬───────┘  │
│                             │  │               │          │
│                             │  │               ▼          │
│                             │  │          流式返回        │
└─────────────────────────────┘  └──────────────────────────┘
```

### RAG Pipeline 流程图

```
离线索引阶段（一次或定期）：
  文档集合 → 文档加载 → 文本切分 → Embedding → 向量数据库

在线检索阶段（每次查询）：
  用户问题 → Query 改写 → Embedding → 向量检索 → Rerank → Prompt 构造 → LLM → 答案
```

## 🚀 快速开始

### 1. 环境准备

```bash
# 进入项目目录
cd starter-code/project3-rag-system

# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置 API Key

```bash
# 复制环境变量示例文件
cp .env.example .env

# 编辑 .env 文件，填入你的 OpenAI API Key
# OPENAI_API_KEY=your_openai_api_key_here
```

### 3. 准备文档

将你的文档（PDF、TXT、MD）放到 `data/` 目录下。

项目中已经提供了两个示例文档：
- `data/sample_docs/doc1_员工手册.md`
- `data/sample_docs/doc2_产品介绍.md`

### 4. 索引文档

```bash
# 运行 RAG Pipeline
python src/rag_pipeline.py

# 在 CLI 中输入：
>>> index data/sample_docs
```

### 5. 查询

```bash
# 在 CLI 中输入：
>>> query 年假怎么申请？
```

## 📖 使用说明

### CLI 命令

```
命令：
  index <数据目录>  - 索引文档（离线阶段）
  query <问题>      - 查询（在线阶段）
  eval             - 评估（需要准备测试数据）
  quit             - 退出
```

### 示例对话

```
>>> query 年假怎么算？

🤖 答案：
根据文档，年假政策如下 [来源 1]：
- 入职满 1 年：5 天年假
- 入职满 3 年：10 天年假

## 参考文档：
[1] 员工手册.pdf, 第 3 页
```

## 🧪 测试

```bash
# 运行所有测试
python -m pytest tests/

# 或者运行单个测试文件
python tests/test_rag.py
```

## 📁 项目结构

```
project3-rag-system/
├── src/
│   ├── rag_pipeline.py      # RAG 主流程
│   ├── document_loader.py   # 文档加载
│   ├── vector_store.py      # Chroma 向量库封装
│   ├── retriever.py         # 检索器（含 Rerank）
│   └── prompt_builder.py    # Prompt 构建
├── data/
│   └── sample_docs/         # 示例文档
│       ├── doc1_员工手册.md
│       └── doc2_产品介绍.md
├── tests/
│   └── test_rag.py          # 测试
├── requirements.txt         # 依赖清单
├── .env.example            # 环境变量示例
└── README.md               # 本文件
```

## 🔧 核心模块说明

### 1. document_loader.py

文档加载器：
- 支持 PDF、TXT、Markdown
- 提取文本和元数据
- 统一文档格式

### 2. vector_store.py

向量数据库封装：
- 连接 Chroma
- 存储文档向量
- 相似度检索

### 3. retriever.py

检索器：
- 向量检索
- Rerank（可选）
- 混合检索（可选）

### 4. prompt_builder.py

Prompt 构建器：
- 定义 RAG Prompt 模板
- 构造 Context
- 处理引用和溯源

### 5. rag_pipeline.py

RAG Pipeline 主文件：
- 索引文档（离线）
- 问答检索（在线）
- CLI 交互界面
- 评估功能

## ⚠️ 注意事项

1. **API Key 安全**: 不要将 `.env` 文件提交到 Git
2. **文档格式**: 扫描版 PDF 需要 OCR（项目 1 提到过）
3. **向量数据库**: Chroma 默认持久化到本地 `./chroma_db` 目录
4. **成本控制**: Embedding 有成本，注意文档数量

## 🎯 验收标准

### 基础版（必交）

- [x] 至少支持 PDF、Markdown、TXT 三种格式
- [x] 至少 100 个文档的索引
- [x] 30 个测试问题，Recall@5 ≥ 80%
- [x] 答案含引用溯源
- [x] 有 README

### 挑战版（加分）

- [ ] 加 Rerank 模型
- [ ] 加 Query 改写
- [ ] 加文档增量更新（不重建全量）
- [ ] 加缓存（相同问题秒回）
- [ ] 加 Web UI（多文档切换、可视化检索结果）

## 📚 参考资料

- [LlamaIndex 文档](https://docs.llamaindex.ai)
- [Chroma 文档](https://docs.trychroma.com)
- [OpenAI Embedding 文档](https://platform.openai.com/docs/guides/embeddings)

## 🤝 贡献

本项目是「智能体工程师培养计划」的一部分，欢迎提交 Issue 和 Pull Request。

## 📄 许可证

MIT License

---

**作者**: 智能体工程师培养计划  
**日期**: 2024  
**版本**: v1.0
