# Starter Code 回归测试

本目录包含每个项目（Project 1-10）的 **P0 修复回归测试**，用于防止真实 P0 修复被回退。

## 🎯 测试目标

| 项目 | 真实 P0（已修）| 防御重点 |
|------|----------------|---------|
| P1 (LLM App) | 0 个 | 2 个误报（load_dotenv / tempfile 清理）|
| P2 (Tool Agent) | 0 个 | 2-3 个误报（eval() / tools 参数）|
| P3 (RAG System) | **1 个**（chunk_overlap）| 4 个误报（拼写错误）|
| P4 (Memory Agent) | **3 个**（ainvoke / next_action / API_PORT）| 防止回退到阻塞同步调用 |
| P5 (Code Agent) | **3 个**（List / Sandbox.create / e2b pin）| 防止 e2b 0.x 回退 |
| P6 (Multi-Agent) | **4 个**（enable_critic / typing_extensions / SqliteSaver / langgraph pin）| 防止 LangGraph 0.0.x 兼容写法 |
| P7 (Docker Deploy) | **5 个**（pyproject / 密码 / asyncio.sleep / prometheus 路径 / 弱密码）| 防止硬编码密码回归 |
| P8 (Monitoring) | **2 个**（datasources 拼写 / sqlite3 包）| 防止 Grafana 启动失败 |
| P9 (Security) | **3 个**（field(default_factory) / Dockerfile.test / sqlite3 包）| 防止 dataclass 共享可变默认值 |
| P10 (Capstone) | **2+ 个**（openai.api_key / 端口冲突）| 防止多线程竞争条件 |

## 🚀 运行方式

### 单个项目
```bash
cd starter-code/project3-rag-system
python -m unittest tests.test_p0_fixes -v
```

### 全部 10 个项目
```bash
for p in starter-code/project{1..10}-*; do
  echo "=== $p ==="
  (cd "$p" && python -m unittest tests.test_p0_fixes -v 2>&1 | tail -5)
done
```

> 注意：P10 路径是 `starter-code/project10-capstone/`，10 个项目统一在 `tests/test_p0_fixes.py`。

## 🧪 测试设计原则

1. **零外部依赖**：使用 `unittest.mock.MagicMock` 注入 OpenAI/Chroma/Streamlit 等
   - 在已安装 `requirements.txt` 的环境下，真实组件会被自动使用（mock 失效）
   - 在无依赖环境下（如 CI 早期检查），mock 兜底，测试仍可运行
2. **离线运行**：所有测试都不连接 OpenAI / Chroma / Docker / 任何网络服务
3. **快速**：每个项目的 P0 修复测试 < 0.1 秒
4. **可读**：每个测试都有中文 docstring，说明它防御的是哪个 review P0

## 🛡 防御的"真实 P0 修复"

### P1-P3（v0.5.0 ~ v0.5.1 已修）
- `P3 chunk_overlap`：`test_default_overlap_is_50` / `test_custom_overlap` / `test_invalid_overlap_raises` / `test_blank_chunks_skipped` / `test_sliding_window_math` / `test_metadata_contains_chunk_start`
- `P3 误报防御`：`test_persistentclient_correctly_spelled`（防 PersistantClient 幻觉）/ `test_collection_add_uses_metadatas`（防 metadatas→metadata 改回）

### P4（v0.5.0 已修）
- **ainvoke**：api.py chat 路由用 `await app_graph.ainvoke(initial_state)`，不能用 `invoke()`
- **next_action 动态化**：generate_response 节点根据消息数和关键词设置 next_action，让 update_profile / summarize 节点可达
- **API_PORT != 8000**：.env.example 默认 8080，避免与 Chroma 8000 冲突

### P5（v0.5.0 已修）
- **typing.List**：sandbox.py 用 `List` 大写，不能用 `list` 小写
- **E2B SDK 1.x**：create_sandbox 优先用 `Sandbox.create()`，保留 0.x 回退
- **e2b 版本锁**：`e2b>=1.0.0,<2.0.0`

### P6（v0.5.0 已修）
- **enable_critic=False 不崩溃**：路由不能引用不存在的 critic 边
- **typing_extensions**：TypedDict/Annotated 改从 typing_extensions 导入
- **SqliteSaver 死代码已删**
- **langgraph>=0.2.0 + typing-extensions>=4.0.0**

### P7（v0.3.0 已修）
- **Dockerfile 无 pyproject.toml COPY**
- **docker-compose.yml 用 ${POSTGRES_PASSWORD:?env_required}** 强制必填
- **main.py 用 await asyncio.sleep** 替代 time.sleep
- **Prometheus 挂载 `./prometheus/`** 不是 `./monitoring/`
- **.env.example 无默认值即弱密码**（redis123/admin123/agent123）

### P8（v0.3.0 已修）
- **datasources.yml 顶层键正确拼写**（`datasources:` 不是 `datassources:`）
- **requirements.txt 无 sqlite3 pip 包**

### P9（v0.3.0 已修）
- **dataclass 用 field(default_factory=list)** 防止可变默认值共享
- **docker-compose.security.yml 引用的 Dockerfile 存在**（不是 Dockerfile.test）
- **requirements.txt 无 sqlite3 pip 包**

### P10（v0.3.0 + 本次 v0.5.3 已修）
- **OpenAI 客户端实例**：4 个 topic 全部从 `openai.api_key = ...` 改为 `OpenAI(api_key=...)`，无线程竞争
- **端口互不冲突**：topic1=8001, topic2=8002, topic3=8003, topic4=8004

## 📚 教学价值

这些测试本身就是 **AI 辅助编程的最佳实践**：

1. **永远不直接采信 review agent 的报告**，要用 grep 现场验证
   - 经验数据：v0.3.0 中 review agent 报出 24 个 P0，**80% 是幻觉**（如 "PersistantClient" 实际是 "PersistentClient"）
2. **修复后必须写回归测试**，否则下次还会回归
3. **误报也要存证**（用反向断言 `assertNotIn`），防止 review agent 反复提出同一个"幻觉问题"
4. **静态源码检查**（`open(file).read() + assertIn`）能防御 grep 不到的隐藏问题
   - 例：v0.5.3 发现 P9 的 `Dockerfile` 引用了不存在的文件，靠的就是"引用必须可解析"这条不变量

## 🔧 已知限制

- 测试只防御**已经发生的 P0**，不能预测未来的新问题
- 单元测试不替代集成测试；要发现真实运行问题，仍需启动服务跑一遍
- 部分测试是**静态源码扫描**（不执行被测代码），仅当源文件被完全重写时才失效
