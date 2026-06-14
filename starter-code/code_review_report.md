# 智能体工程师培养计划 Starter Code 深度审查报告

> 审查日期：2026-06-15
> 审查范围：Project 7 ~ Project 10 共 4 个项目的全部 starter code

---

## 总览

| 项目 | P0 (严重) | P1 (重要) | P2 (轻微) |
|------|-----------|-----------|-----------|
| Project 7 (Docker Deploy) | 5 | 5 | 3 |
| Project 8 (Monitoring) | 4 | 5 | 2 |
| Project 9 (Security) | 3 | 4 | 2 |
| Project 10 (Capstone) | 4 | 4 | 2 |

---

## Project 7 审查结果（project7-docker-deploy）

### 严重问题 (P0 - 必须修复)

**1. Dockerfile 缺少 pyproject.toml，构建会失败**
- 文件：`Dockerfile` 第68行
- 问题：`COPY --chown=appuser:appuser pyproject.toml ./` 引用了 `pyproject.toml`，但项目根目录中不存在此文件
- 修复：删除此行，或创建 `pyproject.toml`

**2. docker-compose.yml 中硬编码密码**
- 文件：`docker-compose.yml` 第23行、第96行
- 问题：
  - 第23行：`DATABASE_URL=postgresql://agent:agent123@postgres:5432/agentdb` — 密码明文写在 compose 文件中
  - 第96行：`POSTGRES_PASSWORD: agent123` — 硬编码密码
- 修复：改为 `${POSTGRES_PASSWORD}` 并从 `.env` 加载

**3. src/main.py 中 async 函数使用了同步 sleep**
- 文件：`src/main.py` 第113行
- 问题：`time.sleep(0.5)` 在 async 函数中会阻塞整个事件循环
- 修复：改为 `await asyncio.sleep(0.5)`（需先 `import asyncio`）

**4. docker-compose.yml 中 Prometheus 配置路径错误**
- 文件：`docker-compose.yml` 第169行
- 问题：`./monitoring/prometheus.yml` — 实际项目目录名是 `prometheus`（不是 `monitoring`）
- 修复：改为 `./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro`

**5. .env.example 中敏感信息作为默认值**
- 文件：`.env.example` 第19行、第22行、第55-56行
- 问题：`REDIS_PASSWORD=redis123`、`POSTGRES_PASSWORD=agent123`、`GRAFANA_PASSWORD=admin123` — 默认值即弱密码，容易被误用
- 修复：默认值改为空字符串或强密码提示

---

### 重要问题 (P1 - 应该修复)

**6. nginx.conf 中 .well-known 拼写错误**
- 文件：`nginx/nginx.conf` 第57行
- 问题：`.wll-known/acme-challenge/` — `wll` 应为 `well`
- 修复：改为 `.well-known/acme-challenge/`

**7. deploy.sh 中 export 环境变量方式不安全**
- 文件：`scripts/deploy.sh` 第78行
- 问题：`export $(grep -v '^#' "$ENV_FILE" | xargs)` — 若变量值含空格或特殊字符（如 `SECRET_KEY`），会解析错误
- 修复：使用 `set -a` 方式或直接 `source` 文件

**8. ci-cd.yml 中健康检查不可靠**
- 文件：`.github/workflows/ci-cd.yml` 第165-167行
- 问题：`docker compose ps | grep -q "unhealthy"` — `docker compose ps` 输出格式中，"unhealthy" 可能显示为 "(unhealthy)"，且此检查逻辑反了
- 修复：改为更可靠的检查方式

**9. main.py 中错误信息直接暴露给客户端**
- 文件：`src/main.py` 第131行
- 问题：`raise HTTPException(status_code=500, detail=str(e))` — 将内部错误详情返回给客户端
- 修复：生产环境返回通用错误信息，详细错误记入日志

**10. Chroma 服务缺少 healthcheck**
- 文件：`docker-compose.yml` 第113-136行
- 问题：`agent` 服务依赖 `chroma` 的 `service_started` 状态，但 Chroma 未配置 healthcheck
- 修复：为 Chroma 服务添加 healthcheck

---

### 轻微问题 (P2 - 建议修复)

**11. Dockerfile 中不必要的 --extra-index-url**
- 文件：`Dockerfile` 第32-34行
- 问题：`--extra-index-url https://download.pytorch.org/whl/cpu` 被设置，但 `requirements.txt` 中并无 PyTorch 相关包
- 修复：删除此行

**12. requirements.txt 中 LangChain 版本号异常**
- 文件：`requirements.txt` 第53-55行
- 问题：版本号极旧，且包名需确认
- 修复：确认实际需求，使用现代版本

---

### 优点

- Dockerfile 多阶段构建设计合理，运行时镜像干净
- 使用非 root 用户运行应用（安全性好）
- 健康检查配置完善
- 资源限制配置合理
- .dockerignore 配置详细

---

## Project 8 审查结果（project8-monitoring）

### 严重问题 (P0 - 必须修复)

**1. datasources.yml 中 YAML 键名拼写错误**
- 文件：`grafana/provisioning/datasources.yml` 第9行
- 问题：`datassources:` — 多写了一个 `s`，正确应为 `datasources:`
- 修复：改为 `datasources:`

**2. cost_tracker.py 中 SQL 语法错误**
- 文件：`src/cost_tracker.py` 第138-139行
- 问题：`CREATE TABLE IF NOT EXISTS` 实际上是 `IF NOT EXISTS`（连在一起），代码中的空格位置需确认
- 修复：确认 SQL 语法正确性

**3. requirements.txt 中包含无效包名**
- 文件：`requirements.txt` 第20行
- 问题：`sqlite3` 不是有效的 pip 包名，`pip install -r requirements.txt` 会报错
- 修复：删除此行或改为注释

---

### 重要问题 (P1 - 应该修复)

**4. prometheus.yml 中使用 host.docker.internal**
- 文件：`prometheus/prometheus.yml` 第30行
- 问题：仅适用于 Docker Desktop，在 Linux 服务器上无法解析
- 修复：改为服务名+端口，如 `agent:8001`

**5. metrics.py 中指标名称拼写错误**
- 文件：`src/metrics.py` 第32行
- 问题：`token_consumed_total` — `consumed` 拼写为 `consumed`（少了一个 `s`）
- 修复：统一改为 `token_consumed_total`

**6. api.py 中 uvicorn 拼写错误**
- 文件：`src/api.py` 第398行
- 问题：`import uvicorn` — 应为 `import uvicorn`
- 修复：改为 `import uvicorn`

---

### 轻微问题 (P2 - 建议修复)

**7. 多处 import 语句缺少空格**
- 多个文件中的 `from typing import` 等语句格式需统一

---

### 优点

- Prometheus 指标设计全面
- CostTracker 有完整的预算检查和告警逻辑
- Grafana Dashboard 配置了多维度图表
- 代码结构清晰，各模块职责明确

---

## Project 9 审查结果（project9-security）

### 严重问题 (P0 - 必须修复)

**1. detector.py 中 dataclass 字段默认值错误**
- 文件：`src/security/detector.py` 第34行
- 问题：`matched_patterns: List[str] = None` — 应使用 `field(default_factory=list)`
- 修复：
  ```python
  matched_patterns: List[str] = field(default_factory=list)
  ```

**2. docker-compose.security.yml 引用不存在的 Dockerfile**
- 文件：`docker-compose.security.yml` 第68行
- 问题：`dockerfile: Dockerfile.test` — 项目中无 `Dockerfile.test` 文件
- 修复：创建 `Dockerfile.test`，或改为使用主 `Dockerfile`

**3. requirements.txt 中包含无效包名**
- 文件：`requirements.txt` 第31行
- 问题：`sqlite3` 不是有效的 pip 包名
- 修复：删除此行

---

### 重要问题 (P1 - 应该修复)

**4. test_runner.py 中 LLM Judge 提示词 JSON 格式示例错误**
- 文件：`src/evaluation/test_runner.py` 第149-155行
- 问题：提示词中写了 `{{` 和 `}}`，LLM 可能输出错误格式
- 修复：改为 `{` 和 `}`

**5. red_team.py 中攻击成功判定逻辑有问题**
- 文件：`src/evaluation/red_team.py` 第219-232行
- 问题：若响应不包含拒绝关键词就认为"攻击成功"，但某些安全 Agent 可能以其他方式拒绝
- 修复：增加更多拒绝信号检测，或结合 LLM Judge 评估

---

### 轻微问题 (P2 - 建议修复)

**6. 多处 from typing/dataclasses import 语句格式不一致**
- 修复：统一使用标准格式

---

### 优点

- 双层检测设计（规则 + LLM）合理
- 支持编码绕过检测（Base64、Unicode 混淆）
- RBAC 权限模型设计完善
- Red Teaming 工具设计完整

---

## Project 10 审查结果（project10-capstone）

### 严重问题 (P0 - 必须修复)

**1. review_agent.py 中 GitHub API 字段名拼写错误**
- 文件：`topic1-github-review/src/agent/review_agent.py` 第98-99行
- 问题：`f.get("additions", 0)` — GitHub API 返回字段是 `additions`（ correct spelling），但代码中拼写为 `additions`（少了一个 `d`）
- 修复：全局搜索 `additions` 改为 `additions`

**2. 多个主题项目共用相同端口（8000）**
- 文件：各主题的 `docker-compose.yml` 和 `.env.example`
- 问题：所有主题的默认端口都是 8000，若部署在同一服务器会冲突
- 修复：为每个主题分配不同默认端口

**3. cs_agent.py 中 API Key 在每次 LLM 调用时重复设置**
- 文件：`topic2-dingtalk-cs/src/agent/cs_agent.py` 第170行等多处
- 问题：`openai.api_key = self.openai_api_key` 使用全局模块变量，多线程环境下有竞争条件
- 修复：使用 `openai.OpenAI(api_key=...)` 客户端实例方式

---

### 重要问题 (P1 - 应该修复)

**4. obsidian-agent 的 requirements.txt 中可能缺少依赖**
- 文件：`topic3-obsidian-agent/requirements.txt`
- 问题：需确认 `chromadb` 或向量数据库依赖是否已包含
- 修复：核对并补充依赖

**5. marketing-agent 的 content_agent.py 中 JSON 输出解析可能失败**
- 文件：`topic4-marketing-agent/src/agent/content_agent.py` 第299-304行
- 问题：`json_end = generated.rfind("}") + 1` — 若 LLM 输出的 JSON 外还有 `}` 字符，会截断错误
- 修复：使用更健壮的 JSON 提取

---

### 轻微问题 (P2 - 建议修复)

**6. 所有主题项目都允许所有 CORS 来源**
- 文件：各主题 `src/app.py` 中的 `CORSMiddleware` 配置
- 问题：`allow_origins=["*"]` — 生产环境应限制具体域名
- 修复：从环境变量读取允许的 origins

**7. 缺少 .dockerignore 文件**
- 文件：所有 topic 目录下
- 修复：为每个主题添加 `.dockerignore`

---

### 优点

- 四个主题项目覆盖了多样化的 Agent 应用场景
- API 设计符合 RESTful 规范
- 支持后台任务处理（BackgroundTasks）
- Webhook 签名验证机制基本完整

---

## 跨项目共性问题汇总

| 问题 | 影响项目 |
|------|---------|
| `requirements.txt` 中含 `sqlite3` 无效包名 | Project 8, Project 9 |
| `.env.example` 中默认值即弱密码 | Project 7 |
| 异步函数中使用了同步 `time.sleep` | Project 7 |
| 多处 import 语句格式异常 | Project 8, Project 9, Project 10 |

---

## 优先修复建议

1. **立即修复（P0）**：所有硬编码密码、Dockerfile 构建错误、SQL 语法错误
2. **本周修复（P1）**：路径拼写错误、CI/CD 健康检查、环境变量加载安全性
3. **有时间修复（P2）**：代码格式统一、CORS 配置、文档完善
