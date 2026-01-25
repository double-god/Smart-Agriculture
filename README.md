# 智能农业 - 植物病虫害诊断系统

一个结合计算机视觉 (CV) 与检索增强生成 (RAG) 的实验室级植物病虫害智能诊断系统。

## 功能特性

- **CV 集成**: 连接现有的计算机视觉算法进行病虫害识别
- **基于 RAG 的报告**: 使用从 ChromaDB 检索的上下文，基于 LangChain 生成报告
- **异步任务处理**: Celery worker 处理繁重的推理操作
- **动态模板**: 针对病害与虫害分别使用不同的报告格式
- **健康监控**: 内置针对所有基础设施组件的健康检查脚本

## 快速开始

### 环境要求

确保您已安装以下组件：

- **Python 3.12** ([下载](https://www.python.org/downloads/))
- **Docker Engine** >= 20.10 ([安装指南](https://docs.docker.com/engine/install/))
- **Docker Compose** >= 2.0 ([安装指南](https://docs.docker.com/compose/install/))
- **uv** 包管理器 ([安装](https://github.com/astral-sh/uv))

### 安装步骤

```bash
# 1. 克隆仓库
git clone <repository-url>
cd Smart-Agriculture

# 2. 安装 uv (如果尚未安装)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 3. 安装 Python 依赖
uv sync

# 4. 创建环境文件
cp .env.example .env
# 使用您的实际值编辑 .env (特别是 OPENAI_API_KEY)

# 5. 启动基础设施服务
docker-compose up -d

# 6. 验证所有系统是否正常运行
python scripts/doctor.py
```

### 预期输出

如果所有检查通过，您应该看到：

```
🏥 Smart Agriculture System Health Check

Checking infrastructure components...

✓ Python version: 3.12.x
✓ Directory exists: app/
...
✓ All systems operational! (7/7 checks passed)
```

## 系统架构

### 技术栈

| 组件 | 技术 | 用途 |
|-----------|-----------|---------|
| Web 框架 | **FastAPI** | 异步 REST API |
| 任务队列 | **Celery** + Redis | 后台任务处理 |
| 数据库 | **PostgreSQL** | 任务持久化 |
| 向量数据库 | **ChromaDB** | RAG 语义搜索 |
| LLM 编排 | **LangChain** | 报告生成 |
| 存储 | **MinIO** | 图片持久化 |
| 包管理器 | **uv** | 快速依赖管理 |

### 系统流程

1. **上传图片**: 用户通过 FastAPI 上传植物图片
2. **创建任务**: 系统生成任务 ID 并立即返回
3. **CV 处理**: Celery worker 调用 CV 算法
4. **分类映射**: 将 class_id 映射为标准中文名称
5. **RAG 检索**: 使用诊断名称查询 ChromaDB
6. **报告生成**: LangChain + LLM 生成结构化报告
7. **结果轮询**: 前端轮询 API 获取完成结果

### RAG 智能报告系统

系统集成了检索增强生成（RAG）技术，为诊断结果生成专业的农业指导报告：

**工作原理**:
```
诊断结果 (病害名称)
    ↓
向量检索 (ChromaDB)
    ↓
相关知识库 (农业专业文档)
    ↓
LLM 生成 (GPT-4o-mini)
    ↓
结构化报告 (Markdown)
```

**报告内容**:
- 📋 **病害描述**: 病原、症状、发病条件
- 🛡️ **防治措施**: 农业防治、生物防治、化学防治
- 💊 **药剂推荐**: 具体用量、稀释倍数、安全间隔期
- 🌱 **预防措施**: 栽培管理建议

**特点**:
- ✅ 基于真实农业知识库
- ✅ 上下文感知，针对性强
- ✅ 容错设计，失败不影响诊断
- ✅ 置信度警告，低置信度时提醒用户

### 项目结构

```
Smart-Agriculture/
├── app/
│   ├── api/              # FastAPI 路由
│   ├── core/             # 配置与模板
│   ├── models/           # Pydantic & SQLModel 模式
│   ├── services/         # 外部集成 (CV, Chroma, MinIO)
│   └── worker/           # Celery 任务与链
├── data/                 # 静态 JSON 文件 (taxonomy 等)
├── scripts/              # 工具脚本 (doctor.py)
├── openspec/             # OpenSpec 变更管理
├── pyproject.toml        # 项目元数据与依赖
├── Dockerfile            # 多阶段构建
├── docker-compose.yml    # 服务编排
└── README.md
```

## 配置

### 环境变量

关键环境变量 (见 `.env.example`):

```bash
# 应用程序
APP_NAME=Smart Agriculture
DEBUG=false

# 数据库
DATABASE_URL=postgresql://postgres:postgres@db:5432/smartag

# Redis
REDIS_URL=redis://redis:6379/0

# OpenAI (LLM 功能需要)
OPENAI_API_KEY=sk-your-key-here

# ChromaDB
CHROMA_HOST=chroma
CHROMA_PORT=8000

# MinIO (对象存储)
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=your-access-key
MINIO_SECRET_KEY=your-secret-key
```

### 端口映射

| 服务 | 容器端口 | 主机端口 | 备注 |
|---------|---------------|-----------|---|
| FastAPI (Web) | 8000 | 8000 | - |
| Celery Worker | - | - | 未暴露 |
| PostgreSQL | 5432 | 5434 | - |
| Redis | 6379 | 6379 | - |
| ChromaDB | 8000 | 8001 | - |
| MinIO API | 9000 | 9010 | 已修改以避免冲突 |
| MinIO Console | 9001 | 9011 | - |

## 开发指南

### 运行测试

```bash
# 运行所有测试
uv run pytest

# 运行并生成覆盖率报告
uv run pytest --cov=app --cov-report=html
```

### 代码质量

```bash
# 格式化代码
uv run black app/ scripts/

# 代码检查 (Lint)
uv run ruff check app/ scripts/

# 类型检查
uv run mypy app/
```

### 添加依赖

```bash
# 添加新依赖
uv add package-name

# 添加开发依赖
uv add --dev package-name
```

### Docker 开发

```bash
# 代码更改后重建服务
docker-compose up --build

# 查看特定服务的日志
docker-compose logs -f web
docker-compose logs -f worker

# 停止所有服务
docker-compose down

# 停止并删除卷 (⚠️ 会删除数据)
docker-compose down -v
```

## 故障排除

### 问题: `uv sync` 失败

**解决方案**: 确保您使用的是 Python 3.12
```bash
python --version  # 应该是 3.12.x
```

### 问题: doctor.py 中 PostgreSQL 连接失败

**解决方案**: 检查 Docker 服务是否正在运行
```bash
docker-compose ps
docker-compose logs db
```

### 问题: 端口已被占用

**解决方案**: 停止冲突的服务或修改 `docker-compose.yml` 端口映射

### 问题: OpenAI API 错误

**解决方案**: 在 `.env` 中验证您的 API 密钥:
```bash
echo $OPENAI_API_KEY  # 应该以 "sk-" 开头
```

### 问题: ChromaDB 连接超时

**解决方案**: ChromaDB 启动需要时间。在 `docker-compose up` 后等待 30 秒再运行运行状况检查。

## OpenSpec 开发

本项目遵循 **OpenSpec** 规范驱动的开发工作流。详见 `openspec/AGENTS.md`。

创建一个新变更:

1. 创建提案: `openspec/changes/<change-id>/proposal.md`
2. 编写规范: `openspec/changes/<change-id>/specs/<capability>/spec.md`
3. 定义任务: `openspec/changes/<change-id>/tasks.md`
4. 验证: `openspec validate <change-id>`
5. 按照 tasks.md 实现

## 许可证

MIT



## 支持

如有问题或疑问:
- 查看 [故障排除](#troubleshooting) 部分
- 运行 `python scripts/doctor.py` 诊断基础设施问题
- 查看服务日志: `docker-compose logs <service-name>`
