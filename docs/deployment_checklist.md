# 部署检查清单

本文档提供了 Smart-Agriculture 系统完整部署的检查清单，确保所有组件正确配置和运行。

## 目录

- [环境准备](#环境准备)
- [知识库初始化](#知识库初始化)
- [服务启动](#服务启动)
- [健康检查](#健康检查)
- [功能测试](#功能测试)
- [生产环境注意事项](#生产环境注意事项)

---

## 环境准备

### 1. 系统要求

- [ ] **操作系统**: Linux (推荐 Ubuntu 22.04+) / macOS / Windows (WSL2)
- [ ] **Python**: 3.12.x
- [ ] **Docker**: >= 20.10
- [ ] **Docker Compose**: >= 2.0
- [ ] **uv**: 最新版（包管理器）
- [ ] **内存**: 至少 4GB RAM
- [ ] **磁盘**: 至少 10GB 可用空间

### 2. 环境变量配置

创建 `.env` 文件（从 `.env.example` 复制）：

```bash
cp .env.example .env
```

**必需环境变量**:

- [ ] `OPENAI_API_KEY`: OpenAI/SiliconFlow API 密钥
- [ ] `DATABASE_URL`: PostgreSQL 连接字符串
- [ ] `REDIS_URL`: Redis 连接字符串
- [ ] `MINIO_ENDPOINT`: MinIO 端点
- [ ] `MINIO_ACCESS_KEY`: MinIO 访问密钥
- [ ] `MINIO_SECRET_KEY`: MinIO 秘密密钥

**可选环境变量** (使用 SiliconFlow):

```bash
OPENAI_BASE_URL=https://api.siliconflow.cn/v1
OPENAI_CHAT_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=Qwen/Qwen3-Embedding-0.6B
CHROMA_PERSIST_DIRECTORY=data/chroma
```

### 3. 依赖安装

```bash
# 安装 Python 依赖
uv sync

# 验证安装
uv run python --version
uv run pytest --version
```

---

## 知识库初始化

### 1. 准备知识文件

- [ ] 确认 `data/knowledge/` 目录存在
- [ ] 检查示例文件是否存在：
  - [ ] `diseases/powdery_mildew.md`
  - [ ] `diseases/late_blight.md`
  - [ ] `crops/tomato.md`

### 2. 运行摄取脚本

```bash
# 首次初始化（重置模式）
uv run python scripts/ingest_knowledge.py --path data/knowledge/ --reset
```

**预期输出**:
```
📚 Knowledge Base Ingestion Script
==================================
Path: data/knowledge/
Mode: reset (rebuild database)

📄 Processing files...
  ✅ diseases/powdery_mildew.md (2.3 KB)
  ✅ diseases/late_blight.md (2.8 KB)
  ✅ crops/tomato.md (4.1 KB)

🔪 Splitting documents...
  ✅ Created 47 chunks from 3 files

📊 Creating embeddings...
  ✅ Embedded 47 chunks (took 12.3s)

💾 Storing in ChromaDB...
  ✅ Stored at: data/chroma/

✨ Done!
```

### 3. 验证 ChromaDB

```bash
# 检查 ChromaDB 目录
ls -la data/chroma/

# 应该看到 chroma.sqlite3 和其他文件
```

---

## 服务启动

### 1. 启动基础设施

```bash
# 启动所有 Docker 服务
docker-compose up -d

# 验证服务状态
docker-compose ps
```

**预期输出**:
```
NAME                    COMMAND                  SERVICE      STATUS
smart-agriculture-db    "docker-entrypoint.s…"   db           Up
smart-agriculture-minio "/usr/bin/docker-ent…"   minio        Up
smart-agriculture-redis "docker-entrypoint.s…"   redis        Up
```

### 2. 启动应用服务

**Terminal 1 - FastAPI**:
```bash
uv run uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Celery Worker**:
```bash
celery -A app.worker.celery_app worker --loglevel=info
```

### 3. 验证服务可访问性

- [ ] **FastAPI**: 访问 http://localhost:8000/docs
- [ ] **MinIO Console**: 访问 http://localhost:9011
  - 用户名: minioadmin
  - 密码: minioadmin
- [ ] **Redis**: `docker-compose logs redis`
- [ ] **PostgreSQL**: `docker-compose logs db`

---

## 健康检查

### 1. 运行系统诊断

```bash
python scripts/doctor.py
```

**预期输出**:
```
🏥 Smart Agriculture System Health Check

Checking infrastructure components...

✓ Python version: 3.12.x
✓ Directory exists: app/
✓ Directory exists: data/
✓ Environment file: .env exists
✓ Docker: Docker version 24.0.x
✓ Docker Compose: Docker Compose version 2.x.x
✓ All systems operational! (7/7 checks passed)
```

### 2. API 健康检查

```bash
curl http://localhost:8000/health
```

**预期响应**:
```json
{
  "status": "healthy",
  "timestamp": "2025-01-25T12:00:00Z",
  "services": {
    "database": "ok",
    "redis": "ok",
    "minio": "ok"
  }
}
```

### 3. 服务日志检查

```bash
# 检查 FastAPI 日志
docker-compose logs -f web

# 检查 Celery Worker 日志
# (在 Terminal 2 中查看)
```

---

## 功能测试

### 1. 测试图片上传

```bash
# 准备测试图片
wget https://upload.wikimedia.org/wikipedia/commons/thumb/a/a2/Phytophthora_infestans_Tomato.jpg/640px-Phytophthora_infestans_Tomato.jpg -O test_photo.jpg

# 上传图片
curl -X POST "http://localhost:8000/api/v1/upload" \
  -F "file=@test_photo.jpg"
```

**预期响应**:
```json
{
  "url": "http://localhost:9010/smart-agriculture/xxx-photo.jpg",
  "filename": "xxx-photo.jpg",
  "original_filename": "test_photo.jpg",
  "content_type": "image/jpeg"
}
```

### 2. 测试诊断任务

```bash
# 提交诊断（替换 <image_url>）
curl -X POST "http://localhost:8000/api/v1/diagnose" \
  -H "Content-Type: application/json" \
  -d '{
    "image_url": "<image_url>",
    "crop_type": "番茄"
  }'
```

**预期响应**:
```json
{
  "task_id": "xxx-xxx-xxx",
  "status": "PENDING",
  "message": "Diagnosis task created successfully"
}
```

### 3. 轮询诊断结果

```bash
# 替换 <task_id>
curl "http://localhost:8000/api/v1/diagnose/tasks/<task_id>"
```

**预期响应（成功）**:
```json
{
  "task_id": "xxx-xxx-xxx",
  "status": "SUCCESS",
  "result": {
    "diagnosis_name": "番茄晚疫病",
    "confidence": 0.92,
    "action_policy": "RETRIEVE",
    "report": "# 番茄晚疫病诊断报告\n\n..."
  },
  "error": null
}
```

### 4. 运行集成测试

```bash
# 运行所有测试
uv run pytest

# 运行 RAG 集成测试
uv run pytest tests/worker/test_diagnosis_tasks_rag.py -v

# 运行端到端测试（需要真实环境）
uv run pytest tests/integration/test_rag_e2e.py -v -s -m integration
```

---

## 生产环境注意事项

### 1. 安全配置

- [ ] **修改默认密码**: MinIO、PostgreSQL
- [ ] **使用环境变量管理密钥**: 不要提交到 Git
- [ ] **启用 HTTPS**: 使用反向代理（Nginx）
- [ ] **配置防火墙**: 限制端口访问
- [ ] **定期备份数据**: ChromaDB、PostgreSQL

### 2. 性能优化

- [ ] **配置 Celery 并发**: `--concurrency=4`
- [ ] **启用 Gunicorn**: 多 worker 模式
- [ ] **配置 Redis 持久化**: AOF/RDB
- [ ] **配置 PostgreSQL 连接池**
- [ ] **启用 CDN**: 静态资源加速

### 3. 监控和日志

- [ ] **配置日志级别**: 生产环境使用 `INFO`
- [ ] **集成监控系统**: Prometheus + Grafana
- [ ] **设置告警**: 服务失败、API 错误率
- [ ] **日志轮转**: 避免磁盘占满
- [ ] **API 限流**: 防止滥用

### 4. 备份策略

```bash
# ChromaDB 备份
tar -czf chroma_backup_$(date +%Y%m%d).tar.gz data/chroma/

# PostgreSQL 备份
docker-compose exec db pg_dump -U postgres smartag > backup_$(date +%Y%m%d).sql

# MinIO 数据备份（通过 mc 客户端）
mc mirror minio/smart-agriculture /backup/minio-$(date +%Y%m%d)/
```

### 5. 高可用配置

- [ ] **Redis Sentinel**: 主从复制 + 自动故障转移
- [ ] **PostgreSQL 主从**: 读写分离
- [ ] **多 Celery Worker**: 负载均衡
- [ ] **ChromaDB 集群**: 分布式向量数据库
- [ ] **负载均衡器**: Nginx/HAProxy

---

## 故障排查

### 问题: 服务启动失败

**检查步骤**:
1. 查看服务日志: `docker-compose logs <service>`
2. 检查端口占用: `netstat -tulpn | grep <port>`
3. 验证环境变量: `cat .env`
4. 重启 Docker: `docker-compose restart`

### 问题: RAG 查询失败

**检查步骤**:
1. 验证 ChromaDB 已初始化: `ls data/chroma/`
2. 重新摄取知识库: `uv run python scripts/ingest_knowledge.py --reset`
3. 检查 API 密钥: `echo $OPENAI_API_KEY`
4. 查看详细日志: 设置 `LOG_LEVEL=DEBUG`

### 问题: LLM 报告生成失败

**检查步骤**:
1. 验证 OpenAI API 密钥有效
2. 检查网络连接: `ping api.openai.com`
3. 检查 API 配额: 登录 OpenAI 控制台
4. 查看错误日志: Celery Worker 日志

### 问题: 诊断任务超时

**检查步骤**:
1. 检查 Celery Worker 是否运行
2. 查看任务队列: `docker-compose logs redis`
3. 增加超时时间: 修改 `timeout` 参数
4. 检查系统资源: `htop` 或 `top`

---

## 部署后验证

### 完整功能测试清单

- [ ] **上传功能**: 成功上传图片
- [ ] **诊断功能**: 提交诊断任务
- [ ] **结果查询**: 成功获取诊断结果
- [ ] **RAG 检索**: 查询相关文档
- [ ] **LLM 报告**: 生成诊断报告
- [ ] **置信度警告**: 低置信度显示警告
- [ ] **健康样本**: 不生成报告（action_policy=PASS）
- [ ] **错误处理**: 报告失败不影响诊断

### 性能基准

- [ ] **上传响应时间**: <500ms
- [ ] **诊断创建时间**: <100ms
- [ ] **诊断完成时间**: <30s（含 LLM）
- [ ] **状态查询时间**: <50ms
- [ ] **并发支持**: 20+ 任务/秒

---

## 相关文档

- [知识库 RAG 指南](./knowledge_rag.md)
- [报告生成指南](./report_generation.md)
- [诊断工作流程](./diagnosis_workflow.md)

---

## 更新日志

- **2025-01-25**: 初始版本，支持完整的 RAG + LLM 部署
