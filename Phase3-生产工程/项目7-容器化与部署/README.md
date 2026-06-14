# 项目 7：容器化与部署

> **阶段**：Phase 3 - 生产工程
> **周次**：Week 9-10
> **难度**：⭐⭐⭐⭐
> **预估工时**：18-22 小时

---

## 一、项目目标

将项目 6 的多 Agent 系统打包成 Docker 镜像，部署到云服务器，并配置 CI/CD。

**核心能力培养**：
- Dockerfile 编写与镜像优化
- Docker Compose 多服务编排
- 容器网络与数据持久化
- CI/CD 流程
- 云服务器运维基础

---

## 二、容器化基础

### 为什么需要容器化？

**传统部署的问题**：
```
开发环境：Python 3.11 + 依赖 A 版本 1.2
测试环境：Python 3.9 + 依赖 A 版本 1.0
生产环境：Python 3.10 + 依赖 A 版本 1.1
→ "在我电脑上能跑啊！"
```

**容器化的解决方案**：
```
Docker 镜像：包含完整运行时环境
- Python 3.11
- 所有依赖（固定版本）
- 系统库
- 应用代码

→ "构建一次，到处运行"
```

### Docker 核心概念

```
┌──────────────────────────────────┐
│ 镜像（Image）：只读模板            │
│   - 类似于"类"                   │
│   - 由 Dockerfile 构建            │
└──────────────────────────────────┘
         ↓
┌──────────────────────────────────┐
│ 容器（Container）：镜像的运行实例   │
│   - 类似于"对象"                 │
│   - 可读可写                     │
└──────────────────────────────────┘
```

### 应用架构

```
┌─────────────────────────────────────────┐
│  Docker Compose 多服务编排               │
│                                          │
│  ┌──────────┐  ┌──────────┐  ┌────────┐│
│  │ Agent    │  │ Redis    │  │ Nginx  ││
│  │ (FastAPI)│←→│ (缓存)   │  │ (代理) ││
│  └──────────┘  └──────────┘  └────────┘│
│       ↓                                  │
│  ┌──────────┐  ┌──────────┐             │
│  │ Chroma   │  │ E2B      │             │
│  │ (向量DB) │  │ (沙箱)   │             │
│  └──────────┘  └──────────┘             │
└─────────────────────────────────────────┘
```

---

## 三、详细任务说明

### 3.1 基础版任务（必做，12-15 小时）

#### Step 1：Docker 基础（2 小时）

**任务清单**：
- [ ] 安装 Docker Desktop
- [ ] 理解 Docker 基本命令
- [ ] 运行第一个容器（hello-world）

**Docker Desktop 安装**：
- macOS：https://www.docker.com/products/docker-desktop
- Windows：同上
- Linux：使用包管理器安装
> 如果 Docker Desktop 下载页变更，备选方案：macOS 用户可通过 `brew install --cask docker` 安装，Linux 用户可通过 `curl -fsSL https://get.docker.com | sh` 安装。

**核心命令**：
```bash
# 镜像相关
docker images              # 查看本地镜像
docker pull <image>        # 拉取镜像
docker rmi <image>         # 删除镜像
docker build -t <name> .   # 构建镜像

# 容器相关
docker ps                  # 查看运行中的容器
docker ps -a               # 查看所有容器
docker run <image>         # 运行容器
docker stop <container>    # 停止容器
docker rm <container>      # 删除容器
docker logs <container>    # 查看日志
docker exec -it <container> bash  # 进入容器

# 清理
docker system prune        # 清理无用资源
```

---

#### Step 2：编写 Dockerfile（3 小时）

**任务清单**：
- [ ] 为项目 6 编写 Dockerfile
- [ ] 使用多阶段构建
- [ ] 优化镜像大小

**项目结构**：
```
multi-agent-system/
├── app/
│   ├── main.py
│   ├── agents/
│   ├── config/
│   └── utils/
├── requirements.txt
├── .env.example
├── Dockerfile
├── docker-compose.yml
└── README.md
```

**Dockerfile（多阶段构建）**：
```dockerfile
# ============ 阶段 1：构建依赖 ============
FROM python:3.11-slim AS builder

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖到临时目录
RUN pip install --user --no-cache-dir -r requirements.txt

# ============ 阶段 2：运行时镜像 ============
FROM python:3.11-slim

WORKDIR /app

# 创建非 root 用户
RUN useradd -m -u 1000 appuser

# 从 builder 阶段复制已安装的依赖
COPY --from=builder /root/.local /home/appuser/.local

# 复制应用代码
COPY --chown=appuser:appuser app/ ./app/

# 设置环境变量
ENV PATH=/home/appuser/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# 切换到非 root 用户
USER appuser

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**requirements.txt**：
```
fastapi==0.110.0
uvicorn[standard]==0.27.1
pyautogen==0.2.27
openai==1.12.0
redis==5.0.1
chromadb==0.4.22
pydantic==2.6.1
python-dotenv==1.0.1
```

**.env.example**：
```
OPENAI_API_KEY=sk-...
REDIS_URL=redis://redis:6379/0
E2B_API_KEY=e2b_...
LOG_LEVEL=INFO
```

**优化技巧**：
```dockerfile
# ❌ 不好：每次都重新安装
COPY . .
RUN pip install -r requirements.txt

# ✅ 好：利用缓存
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .

# ❌ 不好：镜像大
FROM python:3.11

# ✅ 好：精简镜像（~150MB vs ~900MB）
FROM python:3.11-slim

# ❌ 不好：以 root 运行
USER root

# ✅ 好：非 root 用户
USER appuser
```
> 以上为简化版 Dockerfile。多阶段构建、健康检查、非 root 用户等进阶配置的完整版本及说明，参见 [技术架构建议书 - 第 3 节](./技术架构/01-技术架构建议书.md)。

**构建并测试**：
```bash
# 构建
docker build -t multi-agent:v1.0 .

# 查看镜像大小
docker images | grep multi-agent

# 运行测试
docker run --rm -p 8000:8000 --env-file .env multi-agent:v1.0

# 访问测试
curl http://localhost:8000/health
```

---

#### Step 3：Docker Compose 多服务编排（4 小时）

**任务清单**：
- [ ] 用 Docker Compose 编排多个服务
- [ ] 配置服务间网络
- [ ] 配置数据持久化
- [ ] 配置环境变量管理

**docker-compose.yml**：
```yaml
version: '3.8'

services:
  # ============ 主应用 ============
  agent:
    build:
      context: .
      dockerfile: Dockerfile
    image: multi-agent:v1.0
    container_name: multi-agent-app
    restart: unless-stopped
    ports:
      - "8000:8000"
    env_file:
      - .env
    environment:
      - REDIS_URL=redis://redis:6379/0
      - CHROMA_HOST=chroma
      - CHROMA_PORT=8000
    depends_on:
      redis:
        condition: service_healthy
      chroma:
        condition: service_started
    volumes:
      - ./logs:/app/logs
    networks:
      - agent-network
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  # ============ Redis 缓存 ============
  redis:
    image: redis:7-alpine
    container_name: agent-redis
    restart: unless-stopped
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    command: redis-server --appendonly yes --maxmemory 512mb --maxmemory-policy allkeys-lru
    networks:
      - agent-network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3

  # ============ Chroma 向量数据库 ============
  chroma:
    image: chromadb/chroma:latest
    container_name: agent-chroma
    restart: unless-stopped
    ports:
      - "8001:8000"
    volumes:
      - chroma-data:/chroma/chroma
    environment:
      - ANONYMIZED_TELEMETRY=False
      - ALLOW_RESET=True
    networks:
      - agent-network

  # ============ Nginx 反向代理 ============
  nginx:
    image: nginx:alpine
    container_name: agent-nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
    depends_on:
      - agent
    networks:
      - agent-network

  # ============ 监控（可选）============
  prometheus:
    image: prom/prometheus:latest
    container_name: agent-prometheus
    restart: unless-stopped
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus-data:/prometheus
    networks:
      - agent-network

  grafana:
    image: grafana/grafana:latest
    container_name: agent-grafana
    restart: unless-stopped
    ports:
      - "3000:3000"
    volumes:
      - grafana-data:/var/lib/grafana
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    depends_on:
      - prometheus
    networks:
      - agent-network

# ============ 数据卷 ============
volumes:
  redis-data:
  chroma-data:
  prometheus-data:
  grafana-data:

# ============ 网络 ============
networks:
  agent-network:
    driver: bridge
```

**启动和管理**：
```bash
# 构建并启动
docker compose up -d

# 查看状态
docker compose ps

# 查看日志
docker compose logs -f agent
docker compose logs -f redis

# 进入容器调试
docker compose exec agent bash

# 重启某个服务
docker compose restart agent

# 停止所有服务
docker compose down

# 停止并删除数据卷
docker compose down -v
```

---

#### Step 4：Nginx 反向代理配置（2 小时）

**任务清单**：
- [ ] 配置 Nginx 反向代理到 Agent 服务
- [ ] 配置 HTTPS（Let's Encrypt）
- [ ] 配置限流和缓存

**nginx.conf**：
```nginx
events {
    worker_connections 1024;
}

http {
    upstream agent_backend {
        server agent:8000;
    }

    # 限流
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;

    # 缓存
    proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=api_cache:10m max_size=1g inactive=60m;

    server {
        listen 80;
        server_name api.yourdomain.com;

        # 重定向到 HTTPS
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name api.yourdomain.com;

        # SSL 证书
        ssl_certificate /etc/nginx/ssl/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/privkey.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;

        # 限流
        limit_req zone=api_limit burst=20 nodelay;

        # 代理配置
        location / {
            proxy_pass http://agent_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            # 超时
            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 300s;  # Agent 任务可能耗时较长
        }

        # 健康检查
        location /health {
            proxy_pass http://agent_backend/health;
            access_log off;
        }

        # 静态资源缓存
        location ~* \.(jpg|jpeg|png|gif|ico|css|js)$ {
            proxy_pass http://agent_backend;
            proxy_cache api_cache;
            proxy_cache_valid 200 60m;
            expires 1h;
        }
    }
}
```

---

#### Step 5：CI/CD 配置（3 小时）

**任务清单**：
- [ ] 配置 GitHub Actions
- [ ] 自动化测试
- [ ] 自动化构建和推送镜像

**.github/workflows/ci.yml**：
```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  # ============ 1. 测试 ============
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: 设置 Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: 缓存依赖
        uses: actions/cache@v3
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}

      - name: 安装依赖
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov

      - name: 代码检查
        run: |
          pip install flake8 black
          flake8 app/ --max-line-length=120
          black --check app/

      - name: 运行测试
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          pytest tests/ --cov=app/ --cov-report=xml

      - name: 上传覆盖率
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml

  # ============ 2. 构建并推送镜像 ============
  build-and-push:
    needs: test
    runs-on: ubuntu-latest
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4

      - name: 登录 Docker Hub
        uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKER_USERNAME }}
          password: ${{ secrets.DOCKER_PASSWORD }}

      - name: 登录阿里云容器镜像服务（可选）
        uses: docker/login-action@v3
        with:
          registry: registry.cn-hangzhou.aliyuncs.com
          username: ${{ secrets.ALIYUN_USERNAME }}
          password: ${{ secrets.ALIYUN_PASSWORD }}

      - name: 构建并推送
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: |
            yourusername/multi-agent:latest
            yourusername/multi-agent:${{ github.sha }}
            registry.cn-hangzhou.aliyuncs.com/yourname/multi-agent:latest

      - name: 镜像安全扫描
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: yourusername/multi-agent:latest
          format: 'table'
          exit-code: '0'
          ignore-unfixed: true

  # ============ 3. 部署到服务器 ============
  deploy:
    needs: build-and-push
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - name: 部署到服务器
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            cd /opt/multi-agent
            docker compose pull
            docker compose up -d
            docker system prune -f
            echo "✅ 部署完成"
```

**需要的 GitHub Secrets**：
- `DOCKER_USERNAME` / `DOCKER_PASSWORD`：Docker Hub 账号
- `ALIYUN_USERNAME` / `ALIYUN_PASSWORD`：阿里云账号（可选）
- `SERVER_HOST` / `SERVER_USER` / `SSH_PRIVATE_KEY`：服务器 SSH
- `OPENAI_API_KEY`：用于测试

---

#### Step 6：部署到云服务器（2 小时）

**任务清单**：
- [ ] 购买云服务器（阿里云/腾讯云）
- [ ] 配置安全组
- [ ] 部署应用
- [ ] 配置域名解析（可选）

**云服务器配置建议**：
- **CPU**：2 核
- **内存**：4 GB
- **硬盘**：50 GB SSD
- **带宽**：5 Mbps
- **操作系统**：Ubuntu 22.04 LTS
- **价格**：约 ¥80-150/月

**部署步骤**：
```bash
# 1. SSH 登录服务器
ssh root@your-server-ip

# 2. 安装 Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
systemctl start docker
systemctl enable docker

# 3. 安装 Docker Compose
apt install docker-compose

# 4. 克隆代码
git clone https://github.com/yourname/multi-agent-system.git
cd multi-agent-system

# 5. 配置环境变量
cp .env.example .env
nano .env  # 填入真实的 API Key

# 6. 启动服务
docker compose up -d

# 7. 查看状态
docker compose ps
docker compose logs -f

# 8. 配置防火墙
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 22/tcp
ufw enable
```

---

### 3.2 挑战版任务（选做 2 个，6-10 小时）

#### 挑战 1：Kubernetes 部署

**任务**：
- [ ] 编写 K8s 部署文件
- [ ] 用 minikube 本地测试
- [ ] 部署到云 K8s 服务

**deployment.yaml**：
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: multi-agent
  labels:
    app: multi-agent
spec:
  replicas: 3
  selector:
    matchLabels:
      app: multi-agent
  template:
    metadata:
      labels:
        app: multi-agent
    spec:
      containers:
      - name: agent
        image: yourusername/multi-agent:v1.0
        ports:
        - containerPort: 8000
        env:
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: agent-secrets
              key: openai-api-key
        - name: REDIS_URL
          value: "redis://redis-service:6379/0"
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: agent-service
spec:
  selector:
    app: multi-agent
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
```

**常用命令**：
```bash
kubectl apply -f deployment.yaml
kubectl get pods
kubectl logs -f <pod-name>
kubectl scale deployment/multi-agent --replicas=5
kubectl rollout status deployment/multi-agent
```

---

#### 挑战 2：HTTPS + Let's Encrypt

**任务**：
- [ ] 用 Certbot 自动申请证书
- [ ] 配置自动续期

**实现**：
```bash
# 安装 Certbot
apt install certbot python3-certbot-nginx

# 申请证书
certbot --nginx -d api.yourdomain.com

# 测试自动续期
certbot renew --dry-run

# 添加 crontab
crontab -e
# 0 3 * * * certbot renew --quiet
```

---

#### 挑战 3：负载均衡 + 自动伸缩

**任务**：
- [ ] 配置 K8s HPA（Horizontal Pod Autoscaler）
- [ ] 根据 CPU/内存自动扩缩容

**hpa.yaml**：
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: multi-agent-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: multi-agent
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

---

#### 挑战 4：滚动更新 + 回滚

**任务**：
- [ ] 配置 K8s 滚动更新策略
- [ ] 出问题时快速回滚

**更新策略**：
```yaml
spec:
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1        # 最多多 1 个 Pod
      maxUnavailable: 0  # 至少保持所有 Pod 可用
```

**回滚命令**：
```bash
# 查看历史
kubectl rollout history deployment/multi-agent

# 回滚到上一版
kubectl rollout undo deployment/multi-agent

# 回滚到指定版本
kubectl rollout undo deployment/multi-agent --to-revision=2
```

---

#### 挑战 5：镜像安全扫描

**任务**：
- [ ] 用 Trivy 扫描镜像漏洞
- [ ] 集成到 CI/CD
- [ ] 设置漏洞阈值

**GitHub Actions 集成**：
```yaml
- name: 镜像安全扫描
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: yourusername/multi-agent:latest
    format: 'sarif'
    output: 'trivy-results.sarif'
    severity: 'CRITICAL,HIGH'
    exit-code: '1'  # 有严重漏洞时失败
```

---

## 四、踩坑经验汇总

### 坑 1：镜像太大（>2GB）

**现象**：构建出来的镜像 2GB+，部署慢  
**原因**：基础镜像选错，依赖没清理  
**解决**：
- 用 `python:3.11-slim` 而不是 `python:3.11`（节省 700MB）
- 多阶段构建
- 清理 apt 缓存：`rm -rf /var/lib/apt/lists/*`
- 用 `.dockerignore` 排除不必要文件

**.dockerignore**：
```
.git
.github
__pycache__
*.pyc
*.pyo
.pytest_cache
.coverage
htmlcov
*.log
node_modules
.vscode
.idea
README.md
docs/
tests/
```

### 坑 2：容器启动失败

**现象**：`docker compose up` 后容器一直重启  
**排查**：
```bash
# 查看日志
docker compose logs agent

# 常见问题：
# 1. 环境变量未配置
# 2. 端口被占用
# 3. 依赖服务未启动（depends_on 配置问题）
# 4. 权限问题（数据卷）
```

### 坑 3：数据丢失

**现象**：容器重启后，之前的数据没了  
**原因**：数据没持久化到卷  
**解决**：
```yaml
volumes:
  - redis-data:/data  # 必须用 named volume 或 bind mount
```

### 坑 4：内存溢出（OOM）

**现象**：容器被 OOMKilled  
**解决**：
- 设置内存限制
- 优化应用内存使用
- 增加服务器内存

### 坑 5：CI/CD 失败

**现象**：GitHub Actions 一直报错  
**排查**：
- Secrets 没配置
- 镜像名拼写错误
- 服务器 SSH 密钥格式问题
- 镜像拉取限速（用国内镜像源）

### 坑 6：HTTPS 配置复杂

**现象**：Let's Encrypt 证书申请失败  
**解决**：
- 确保 80 端口可访问
- DNS 解析正确
- 用 `certbot certonly --webroot` 手动模式

---

## 五、评估标准详解

### 及格（60 分）

- [ ] Dockerfile 编写正确
- [ ] 镜像能成功构建
- [ ] Docker Compose 启动成功
- [ ] 部署到云服务器，外部可访问

### 良好（75 分）

在及格基础上：
- [ ] 镜像优化（大小 < 500MB）
- [ ] CI/CD 配置完整
- [ ] Nginx 反向代理
- [ ] 数据持久化

### 优秀（90 分）

在良好基础上：
- [ ] 完成了至少 3 个挑战任务
- [ ] K8s 部署
- [ ] HTTPS 配置
- [ ] 自动伸缩
- [ ] 有部署文档 + 演示视频

---

## 六、生产环境最佳实践

### 6.1 安全清单

- [ ] **非 root 用户运行**容器
- [ ] **镜像最小化**（slim/alpine）
- [ ] **镜像签名**（Docker Content Trust）
- [ ] **漏洞扫描**（Trivy / Snyk）
- [ ] **Secret 管理**（不用环境变量明文，用 Secret Manager）
- [ ] **网络安全**（网络隔离、最小权限）
- [ ] **日志脱敏**（API Key 不能进日志）

### 6.2 性能清单

- [ ] **资源限制**（CPU、内存）
- [ ] **健康检查**（liveness + readiness）
- [ ] **优雅停机**（处理 SIGTERM）
- [ ] **缓存策略**（Redis 缓存热点数据）
- [ ] **负载均衡**（多实例）

### 6.3 可靠性清单

- [ ] **多实例部署**（至少 2 个）
- [ ] **自动重启**（restart policy）
- [ ] **数据备份**（定期备份数据卷）
- [ ] **监控告警**（Prometheus + Alertmanager）
- [ ] **日志聚合**（Loki / ELK）

---

## 七、交付物清单

- [ ] **代码仓库**（GitHub）
  - Dockerfile（多阶段构建）
  - docker-compose.yml
  - .github/workflows/ci.yml
  - nginx 配置
  - README.md
- [ ] **部署文档**
  - 架构图
  - 部署步骤
  - 故障排查指南
  - 监控告警说明
- [ ] **演示视频**（5-7 分钟）
  - 本地构建
  - 推送到镜像仓库
  - CI/CD 自动部署
  - 云服务器访问

---

**下一步**：完成本项目后，进入 [项目 8：监控与成本优化](../项目8-监控与成本优化/README.md)
