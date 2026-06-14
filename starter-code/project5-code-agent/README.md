# 项目 5：代码执行 Agent

> Phase 2 - 系统构建 | 预计用时：1-2 周

## 项目简介

构建一个能够**理解自然语言需求、自动生成 Python 代码、在沙箱中安全执行、并展示结果**的智能 Agent。

### 核心能力

- **自然语言 → 代码**：通过 LLM 将用户需求转化为可执行的 Python 代码
- **安全沙箱执行**：使用 E2B Sandbox 隔离执行环境，避免本地污染
- **自动错误修复**：执行失败时自动分析错误并修复代码（最多 3 次重试）
- **数据可视化**：支持 matplotlib 图表生成，并展示结果
- **HTML 报告**：自动生成包含代码、图表和结果的分析报告

## ⚠️ 重要说明：E2B API Key

本项目使用 **E2B Sandbox** 作为代码执行环境，需要 API Key：

1. 访问 https://e2b.dev 注册账号（支持 GitHub 登录）
2. 在 Dashboard 中复制 API Key
3. 将 API Key 填入 `.env` 文件的 `E2B_API_KEY` 字段
4. **免费版限制**：每月 100 小时沙箱使用时长，足够学习和测试

若暂时无法获取 E2B Key，可修改 `sandbox.py` 使用本地 `subprocess` 执行代码（不推荐，存在安全风险）。

## 技术架构

```
用户自然语言需求
        │
        ▼
┌───────────────────────────────────────┐
│         CodeExecutionAgent             │
│                                       │
│   CodeGenerator → Executor → 成功？   │
│                        │              │
│                        ✗              │
│                        ▼              │
│                   ErrorHandler         │
│                   (自动修复代码)       │
│                        │              │
│                        └──重试──→ Executor
│                                       │
└───────────────────────────────────────┘
        │
        ▼
    Visualizer
    (图表展示 / HTML 报告)
```

## 快速开始

### 1. 环境准备

```bash
# 复制环境变量模板
cp .env.example .env
# 填写 OPENAI_API_KEY 和 E2B_API_KEY

# 安装依赖
pip install -r requirements.txt

# 安装 E2B SDK（若 requirements 安装失败，单独安装）
pip install e2b
```

### 2. 准备示例数据（可选）

项目中已包含 `data/sample_csv/` 下的示例 CSV 文件，可直接使用。

### 3. 命令行运行

```bash
python -m src.agent
```

示例对话：

```
你: 读取 data/sample_csv/sales.csv，画出每月销售额趋势图
🤖: ✅ 执行成功
      📊 结果摘要: 7月销售额最高，达到 25000
      📈 图表已生成: ./output/plot.png
```

## 示例 CSV 数据

| 文件名 | 内容 | 适用场景 |
|--------|------|----------|
| `sales.csv` | 12 个月的销售数据 | 趋势分析、柱状图 |
| `users.csv` | 用户基本信息和活跃度 | 用户画像、分组统计 |

## 环境变量说明

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `OPENAI_API_KEY` | 必填 | OpenAI API 密钥 |
| `OPENAI_BASE_URL` | 可选 | 自定义 API 地址 |
| `MODEL_NAME` | `gpt-4o-mini` | 代码生成使用的模型 |
| `E2B_API_KEY` | 必填 | E2B 沙箱 API 密钥 |
| `E2B_TEMPLATE` | `python3` | E2B 模板名 |
| `E2B_TIMEOUT` | `300` | 沙箱最长运行时间（秒） |
| `MAX_RETRIES` | `3` | 自动修复最大重试次数 |

## 目录结构

```
project5-code-agent/
├── src/
│   ├── agent.py           # Agent 主入口
│   ├── code_generator.py  # 代码生成器（LLM）
│   ├── sandbox.py         # E2B 沙箱封装
│   ├── executor.py        # 代码执行器
│   ├── error_handler.py   # 错误捕获与自我修复
│   └── visualizer.py     # 结果可视化
├── data/
│   └── sample_csv/       # 示例 CSV 数据文件
│       ├── sales.csv
│       └── users.csv
├── output/                # 生成的图表和报告
├── tests/
│   └── test_sandbox.py   # 沙箱测试
├── requirements.txt
├── .env.example
└── README.md
```

## 学习要点

1. **E2B Sandbox 使用**：沙箱创建、文件上传、代码执行、资源释放
2. **LLM 代码生成 Prompt 设计**：如何引导 LLM 生成可执行、安全的代码
3. **错误自动修复**：分析错误类型、构造修复 Prompt、控制重试次数
4. **沙箱安全隔离**：理解为什么不直接用 `exec()` 或 `subprocess`
5. **结果可视化**：Base64 编码图片、HTML 报告生成

## 扩展挑战

- [ ] 支持更多语言（JavaScript、SQL）
- [ ] 添加代码审查步骤（执行前先检查安全性）
- [ ] 支持用户上传自定义数据文件
- [ ] 实现"代码版本管理"（保留每次生成的代码，可回滚）
- [ ] 集成 Jupyter Notebook 导出
