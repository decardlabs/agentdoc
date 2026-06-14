# 项目 7：容器化与部署

> 智能体工程师培养计划 - Phase 3 生产工程

## 项目简介

本项目是"智能体工程师培养计划"的 Phase 3 第一个项目，旨在教授如何将 Agent 应用容器化并部署到生产环境。

### 学习目标

- 理解 Docker 容器化原理和多阶段构建
- 掌握 Docker Compose 多服务编排
- 配置 Nginx 反向代理和 HTTPS
- 搭建 GitHub Actions CI/CD 流水线
- 实现自动化部署和健康检查

### 技术栈

- **容器化**: Docker, Docker Compose
- **Web 服务器**: Nginx
- **SSL 证书**: Let's Encrypt
- **CI/CD**: GitHub Actions
- **监控**: Prometheus, Grafana
- **数据库**: PostgreSQL, Redis, Chroma

## 项目结构

```
project7-docker-deploy/
├── Dockerfile                 # 多阶段构建配置
├── docker-compose.yml        # 服务编排配置
├── .dockerignore             # Docker 构建忽略文件
├── nginx/                   # Nginx 配置
│   ├── nginx.conf          # 反向代理配置
│   └── ssl/               # SSL 证书目录
├── src/                     # 应用源代码
│   └── main.py            # FastAPI 应用
├── scripts/                 # 部署脚本
│   ├── deploy.sh          # 部署脚本
│   └── backup.sh         # 备份脚本
├── .github/workflows/      # CI/CD 配置
│   └── ci-cd.yml        # GitHub Actions 流水线
├── requirements.txt         # Python 依赖
├── .env.example            # 环境变量示例
└── README.md              # 本文件
```

## 快速开始

### 1. 前置条件

- Docker 20.10+
- Docker Compose 2.0+
- Python 3.11+
- Git

### 2. 克隆项目

```bash
cd /path/to/starter-code/project7-docker-deploy
```

### 3. 配置环境变量

```bash
# 复制环境变量示例文件
cp .env.example .env

# 编辑 .env，填入真实的配置值
vim .env
```

### 4. 本地开发

```bash
# 安装依赖
pip install -r requirements.txt

# 启动应用（开发模式）
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Docker 构建

```bash
# 构建镜像
docker build -t multi-agent:v1.0 .

# 查看镜像大小
docker images multi-agent
```

### 6. Docker Compose 启动

```bash
# 启动所有服务
docker compose up -d

# 查看服务状态
docker compose ps

# 查看日志
docker compose logs -f

# 停止所有服务
docker compose down
```

### 7. 验证部署

```bash
# 健康检查
curl http://localhost:8000/health

# 访问 API 文档
open http://localhost:8000/docs

# 访问 Grafana 监控
open http://localhost:3000
```

## 详细指南

### Docker 多阶段构建

本项目使用多阶段构建来减小镜像大小：

1. **阶段 1 (builder)**: 安装编译依赖，构建 Python 包
2. **阶段 2 (runtime)**: 只包含运行时需要的文件

**优势**：
- 镜像大小从 ~1.2GB 降到 ~450MB
- 减少攻击面
- 加快构建速度（利用层缓存）

### Docker Compose 编排

编排了 7 个服务：

1. **agent**: 主应用（FastAPI）
2. **redis**: 缓存服务
3. **postgres**: 关系数据库
4. **chroma**: 向量数据库
5. **nginx**: 反向代理
6. **prometheus**: 指标采集
7. **grafana**: 监控仪表板

**关键配置**：
- 健康检查
- 资源限制
- 数据持久化（Volumes）
- 网络隔离

### Nginx 反向代理

Nginx 提供：
- HTTPS 终止（Let's Encrypt）
- 请求限流
- 静态资源缓存
- HTTP 到 HTTPS 重定向

### GitHub Actions CI/CD

流水线包含 3 个 Job：

1. **test**: 代码检查和单元测试
2. **build-and-push**: 构建并推送镜像
3. **deploy**: 部署到生产服务器

**需要配置的 Secrets**：
- `DOCKER_USERNAME`: Docker Hub 用户名
- `DOCKER_PASSWORD`: Docker Hub 密码
- `SERVER_HOST`: 服务器 IP
- `SERVER_USER`: 服务器用户名
- `SSH_PRIVATE_KEY`: SSH 私钥

## 部署到云服务器

### 1. 购买云服务器

推荐使用阿里云 ECS（2C4G），约 100 元/月。

### 2. 安装 Docker

```bash
# SSH 登录服务器
ssh root@your-server-ip

# 安装 Docker
curl -fsSL https://get.docker.com | sh

# 启动 Docker
systemctl enable docker
systemctl start docker

# 验证安装
docker --version
docker compose version
```

### 3. 克隆代码

```bash
# 创建项目目录
mkdir -p /opt/multi-agent
cd /opt/multi-agent

# 克隆代码（替换为你的仓库）
git clone https://github.com/yourname/multi-agent-system.git .
```

### 4. 配置环境变量

```bash
# 复制并编辑环境变量
cp .env.example .env
vim .env

# 填入真实的 API Key 和密码
```

### 5. 配置防火墙

```bash
# 允许 HTTP/HTTPS 流量
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 22/tcp

# 启用防火墙
ufw --force enable
```

### 6. 申请 SSL 证书

```bash
# 安装 certbot
apt update && apt install -y certbot

# 申请证书（需要暂停 Nginx）
docker compose stop nginx

certbot certonly --standalone \
  -d api.yourdomain.com \
  --agree-tos \
  --email your@email.com

# 重启 Nginx
docker compose start nginx
```

### 7. 启动服务

```bash
# 启动所有服务
docker compose up -d

# 验证服务状态
docker compose ps

# 查看日志
docker compose logs --tail=50 agent
```

## 监控和日志

### Prometheus 指标

访问 `http://localhost:9090` 查看 Prometheus 界面。

### Grafana 仪表板

访问 `http://localhost:3000`（默认账号：admin/admin）。

### 应用日志

```bash
# 查看应用日志
docker compose logs -f agent

# 查看 Nginx 日志
docker compose logs -f nginx

# 查看所有服务日志
docker compose logs -f
```

## 备份和恢复

### 备份

```bash
# 完整备份
./scripts/backup.sh --full

# 仅备份数据
./scripts/backup.sh --data-only

# 仅备份镜像
./scripts/backup.sh --images
```

### 恢复

```bash
# 恢复数据卷
./scripts/backup.sh --restore /opt/backups/multi-agent/20250115_120000
```

## 测试场景

本项目包含 30 个测试场景，涵盖：

1. **镜像构建** (5 个): 多阶段构建、镜像大小、层数、非 root 用户、.dockerignore
2. **Docker Compose** (7 个): 服务启动、网络互通、数据持久化、健康检查、资源限制
3. **Nginx + HTTPS** (5 个): HTTP 重定向、证书有效、反向代理、限流、缓存
4. **CI/CD** (5 个): PR 触发、代码检查、镜像构建、安全扫描、自动部署
5. **生产部署** (4 个): 外网访问、安全组、自动重启、日志输出
6. **监控** (4 个): Prometheus 指标、Grafana 仪表板、日志查询、回滚

## 成本估算

| 项目 | 月费 | 说明 |
|------|------|------|
| 云服务器 2C4G | ~100 元 | 包年更便宜 |
| 域名 (.com) | ~5 元/月 | 首年可能更便宜 |
| SSL 证书 | 0 元 | Let's Encrypt 免费 |
| Docker Hub | 免费 | 公开仓库不限 |
| GitHub Actions | 免费 | 公开仓库 2000 分钟/月 |
| **合计** | **~105 元/月** | |

## 安全清单

- [x] 非 root 用户运行容器
- [x] 使用 slim 基础镜像
- [x] 镜像中不硬编码密钥
- [x] 安全组只开放 22/80/443
- [x] Redis / Postgres 设置密码
- [x] HTTPS 全链路加密
- [x] API Key 不打印到日志
- [x] CORS 配置正确
- [x] 定期 Trivy 扫描
- [x] SSH 禁用密码登录
- [x] 定期更新基础镜像

## 常见问题

### 1. 镜像构建失败

**问题**: `docker build` 失败，提示依赖安装错误。

**解决**:
```bash
# 清理构建缓存
docker builder prune -f

# 重新构建（不使用缓存）
docker build --no-cache -t multi-agent:v1.0 .
```

### 2. 服务启动失败

**问题**: `docker compose up` 后某些服务不健康。

**解决**:
```bash
# 查看服务日志
docker compose logs redis
docker compose logs postgres

# 检查健康检查
docker inspect multi-agent-redis | grep Health
```

### 3. Nginx 反向代理不工作

**问题**: 访问 `http://localhost` 返回 502 Bad Gateway。

**解决**:
```bash
# 检查 Nginx 配置
docker compose exec nginx nginx -t

# 检查 upstream 连通性
docker compose exec nginx curl http://agent:8000/health
```

### 4. HTTPS 证书过期

**问题**: 浏览器提示证书不安全。

**解决**:
```bash
# 手动续期
certbot renew --force-renewal

# 重启 Nginx
docker compose restart nginx

# 设置自动续期（crontab）
0 3 * * * certbot renew --quiet && docker compose restart nginx
```

## 扩展方向

完成项目 7 后，可以继续学习：

- **项目 8**: 监控与成本优化（Prometheus、Grafana、成本追踪）
- **项目 9**: 安全与评估（Prompt 注入检测、安全过滤）
- **项目 10**: 端到端 Agent 应用（毕业设计）

## 参考资料

- [Docker 官方文档](https://docs.docker.com/)
- [Docker Compose 文档](https://docs.docker.com/compose/)
- [Nginx 文档](https://nginx.org/en/docs/)
- [Let's Encrypt 文档](https://letsencrypt.org/docs/)
- [GitHub Actions 文档](https://docs.github.com/en/actions)
- [Prometheus 文档](https://prometheus.io/docs/)
- [Grafana 文档](https://grafana.com/docs/)

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

---

**Happy Deploying! 🚀**
