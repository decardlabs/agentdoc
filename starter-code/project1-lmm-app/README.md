# LLM 文档问答 Web 应用

> 智能体工程师培养计划 - Phase 1 项目 1
> 
> 构建一个基于 LLM 的文档问答 Web 应用，支持 PDF 上传和智能问答

## 📋 项目简介

本项目是一个 **LLM 文档问答 Web 应用**，用户可以上传 PDF 文档，然后基于文档内容提问，应用会调用 OpenAI API 生成准确的回答。

### 核心功能

- ✅ PDF 文件上传和解析
- ✅ 智能文本切分（Chunking）
- ✅ 基于文档的问答
- ✅ 流式输出
- ✅ 对话历史保持
- ✅ Token 计数和成本显示
- ✅ 防幻觉 Prompt 设计

## 🏗️ 技术架构

### 技术栈

- **Web 框架**: Streamlit
- **LLM**: OpenAI API (gpt-4o-mini / gpt-4o)
- **PDF 解析**: pdfplumber
- **文本切分**: LangChain TextSplitter
- **Token 计数**: tiktoken

### 系统架构图

```
┌──────────────────────────────────────────────────────────┐
│                     Streamlit Web UI                      │
│              (文件上传 / 问答交互 / 流式展示)               │
└────────────────────────┬─────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────┐
│                    应用服务层 (Python)                     │
│  ┌─────────────────┐         ┌──────────────────────┐    │
│  │   PDF 加载器    │         │   LLM 客户端         │    │
│  │  - 文本提取     │  ───►   │  - OpenAI API 调用  │    │
│  │  - 智能切分     │         │  - 流式输出          │    │
│  └─────────────────┘         │  - 错误处理          │    │
│                               └──────────┬───────────┘    │
└──────────────────────────────────────────┼────────────────┘
                                          │
                                          ▼
                              ┌──────────────────────┐
                              │   OpenAI API         │
                              │  (gpt-4o-mini)       │
                              └──────────────────────┘
```

## 🚀 快速开始

### 1. 环境准备

```bash
# 克隆项目（或创建项目目录）
cd starter-code/project1-lmm-app

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

或者在 Streamlit 侧边栏直接输入 API Key（临时使用）。

### 3. 运行应用

```bash
# 启动 Streamlit 应用
streamlit run src/app.py
```

应用会在浏览器中自动打开，地址为：http://localhost:8501

## 📖 使用说明

### 基本使用流程

1. **上传文档**: 在左侧边栏上传 PDF 文件
2. **等待加载**: 应用会自动解析 PDF 并切分成 Chunks
3. **提问**: 在右侧问答区输入你的问题
4. **获取回答**: 应用会基于文档内容生成回答，并流式显示

### 示例问题

- "这篇文档主要讲了什么？"
- "实验设置是什么？"
- "结论部分怎么说的？"
- "请总结第 3 章的内容"

### 高级功能

在侧边栏可以配置：

- **模型选择**: gpt-4o-mini（性价比高）或 gpt-4o（质量更好）
- **温度 (Temperature)**: 控制回答的随机性
- **最大输出 Token**: 控制回答长度
- **Few-shot 示例**: 启用后提升回答质量（但增加 Token 消耗）

## 🧪 测试

```bash
# 运行单元测试
python -m pytest tests/

# 或者运行单个测试文件
python tests/test_pdf_loader.py
```

## 📁 项目结构

```
project1-lmm-app/
├── src/
│   ├── app.py              # Streamlit 主应用
│   ├── pdf_loader.py        # PDF 加载和切分
│   ├── lmm_client.py        # OpenAI API 封装
│   └── prompt_templates.py  # Prompt 模板
├── tests/
│   └── test_pdf_loader.py   # 单元测试
├── requirements.txt         # 依赖清单
├── .env.example            # 环境变量示例
└── README.md               # 本文件
```

## 🔧 核心模块说明

### 1. pdf_loader.py

负责 PDF 文件加载和文本切分：

- `PDFLoader`: 主类，提供 `load_pdf()` 和 `split_text()` 方法
- 支持表格提取
- 支持多文件批量处理

### 2. lmm_client.py

封装 OpenAI API 调用：

- `LLMClient`: 主类，提供 `chat()` 方法
- 支持流式输出
- 自动重试机制
- Token 计数和成本估算

### 3. prompt_templates.py

管理 Prompt 模板：

- `PromptBuilder`: 主类，构造 System Prompt 和 User Prompt
- 防幻觉规则
- Few-shot 示例（可选）

### 4. app.py

Streamlit Web 应用主文件：

- 文件上传界面
- 问答交互界面
- 流式输出展示
- Token 统计显示

## ⚠️ 注意事项

1. **API Key 安全**: 不要将 `.env` 文件提交到 Git
2. **PDF 格式**: 目前支持文本型 PDF，扫描版 PDF 需要 OCR（项目 3 会讲解）
3. **文档长度**: 过长的文档可能超出模型 Context 限制，建议分段处理
4. **成本控制**: 每次问答会消耗 Token，请注意成本

## 🎯 验收标准

### 基础版（必交）

- [x] 能上传 PDF（至少 5 页）
- [x] 能基于文档回答 10 个测试问题，准确率 ≥ 80%
- [x] 答案能引用文档具体段落
- [x] 流式输出、错误处理、成本显示齐备
- [x] 包含 README（如何运行、技术栈、设计思路）

### 挑战版（加分）

- [ ] 支持多文档切换
- [ ] 支持「对比两个文档」功能
- [ ] 加入了对话历史（多轮问答）
- [ ] 引入了缓存（相同问题秒回）

## 📚 参考资料

- [OpenAI API 文档](https://platform.openai.com/docs)
- [Streamlit 文档](https://docs.streamlit.io)
- [LangChain 文档](https://python.langchain.com)

## 🤝 贡献

本项目是「智能体工程师培养计划」的一部分，欢迎提交 Issue 和 Pull Request。

## 📄 许可证

MIT License

---

**作者**: 智能体工程师培养计划  
**日期**: 2024  
**版本**: v1.0
