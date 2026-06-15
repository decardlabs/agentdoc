# Starter Code 回归测试

本目录包含每个项目（Project 1-3）的 **P0 修复回归测试**，用于防止真实 P0 修复被回退。

## 🎯 测试目标

| 项目 | 真实 P0（已修） | 误报 P0（已存证） |
|------|----------------|------------------|
| P1 (LLM App) | 0 个 | 2 个（load_dotenv / tempfile 清理）|
| P2 (Tool Agent) | 0 个 | 2-3 个（eval() / tools 参数）|
| P3 (RAG System) | **1 个**（chunk_overlap）| 4 个（拼写错误等）|

## 🚀 运行方式

### 单个项目
```bash
cd starter-code/project3-rag-system
python -m unittest tests.test_p0_fixes -v
```

### 全部项目
```bash
for p in starter-code/project{1,2,3}-*; do
  echo "=== $p ==="
  (cd "$p" && python -m unittest tests.test_p0_fixes -v 2>&1 | tail -5)
done
```

## 🧪 测试设计原则

1. **零外部依赖**：使用 `unittest.mock.MagicMock` 注入 OpenAI/Chroma/Streamlit 等
   - 在已安装 `requirements.txt` 的环境下，真实组件会被自动使用（mock 失效）
   - 在无依赖环境下（如 CI 早期检查），mock 兜底，测试仍可运行
2. **离线运行**：所有测试都不连接 OpenAI / Chroma / 任何网络服务
3. **快速**：每个项目的 P0 修复测试 < 0.1 秒
4. **可读**：每个测试都有中文 docstring，说明它防御的是哪个 review P0

## 🛡 防御的"真实 P0 修复"

### P3 chunk_overlap（v0.5.1 已修）
- `test_default_overlap_is_50`：默认 overlap=50 不能变成 0
- `test_custom_overlap`：自定义 overlap 必须生效
- `test_invalid_overlap_raises`：overlap >= size 时必须抛 ValueError（防死循环）
- `test_blank_chunks_skipped`：空白 chunk 必须被跳过
- `test_sliding_window_math`：stride = size - overlap 数学正确
- `test_metadata_contains_chunk_start`：metadata 记录 chunk 起始位置

### P3 误报（防止 review agent 重新"修复"）
- `test_persistentclient_correctly_spelled`：防止有人把 `PersistentClient` 改成 `PersistantClient`
- `test_collection_add_uses_metadatas`：防止 `metadatas=` 被改成 `metadata=` 单数

## 📚 教学价值

这些测试本身就是 **AI 辅助编程的最佳实践**：
- **永远不直接采信 review agent 的报告**，要用 grep 现场验证
- **修复后必须写回归测试**，否则下次还会回归
- **误报也要存证**（用反向断言 `assertNotIn`），防止 review agent 反复提出同一个"幻觉问题"
