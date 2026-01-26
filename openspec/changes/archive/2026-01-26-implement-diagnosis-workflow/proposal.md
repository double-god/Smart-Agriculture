# Proposal: Implement Diagnosis Workflow (implement-diagnosis-workflow)

**Change ID**: `implement-diagnosis-workflow`
**Status**: Proposed
**Created**: 2026-01-23
**Author**: Claude (Full-Stack Agent Architect)

---

## 1. Problem Statement

Smart-Agriculture 系统目前已经具备以下基础设施：
- ✅ **TaxonomyService** - 病虫害分类查询服务
- ✅ **StorageService** - MinIO 对象存储服务
- ✅ **Celery Worker** - 异步任务处理框架
- ✅ **LangChain** - 报告生成链

但是**缺少核心的诊断业务流程**，导致系统无法端到端运行。目前存在以下问题：

- **没有图片上传接口**：前端无法上传诊断图片
- **没有诊断提交接口**：无法触发 CV 分析任务
- **没有结果查询接口**：前端无法轮询获取诊断结果
- **Worker 没有诊断任务**：Celery 只有 health_check，缺少真正的 analyze_image 逻辑
- **任务状态管理缺失**：无法追踪任务进度和失败原因

这导致系统虽然有了所有组件，但**无法完成一次完整的诊断流程**。

---

## 2. Proposed Solution

实现**完整的诊断工作流**，打通从图片上传到结果返回的全链路：

### 核心流程

```
┌─────────────┐
│   前端/移动端 │
└──────┬──────┘
       │ 1. 上传图片
       ▼
┌─────────────────┐
│  POST /upload   │  → StorageService 存图 → 返回 URL
└────────┬────────┘
         │ 2. 提交诊断
         ▼
┌─────────────────────┐
│ POST /diagnose      │  → 创建 Celery 任务 → 返回 task_id
└────────┬────────────┘
         │ 3. 轮询结果
         ▼
┌─────────────────────┐
│ GET /tasks/{task_id}│  → 从 Redis 读取状态和结果
└─────────────────────┘

(异步执行)
┌──────────────────────────┐
│  Celery Worker           │
│  ┌─────────────────────┐ │
│  │ analyze_image task  │ │
│  │ 1. 下载图片         │ │
│  │ 2. CV 模型推理      │ │  (Mock 数据)
│  │ 3. 查询 Taxonomy    │ │
│  │ 4. RAG 检索上下文   │ │  (可选)
│  │ 5. LLM 生成报告     │ │  (可选)
│  └─────────────────────┘ │
└──────────────────────────┘
```

### 实施步骤

1. **图片上传接口** (`POST /upload`)
   - 接收 multipart/form-data 图片
   - 调用 StorageService 存储到 MinIO
   - 生成唯一文件名（UUID 前缀）
   - 返回访问 URL

2. **诊断提交接口** (`POST /diagnose`)
   - 接收图片 URL（来自 /upload 或外部 URL）
   - 创建 Celery 任务 `analyze_image.delay(image_url)`
   - 立即返回 `task_id`
   - 任务异步执行，不阻塞 HTTP 请求

3. **结果轮询接口** (`GET /tasks/{task_id}`)
   - 根据 task_id 查询 Celery 任务状态
   - 返回状态：PENDING / STARTED / SUCCESS / FAILURE
   - 成功时返回诊断结果（分类信息、置信度、报告等）

4. **Worker 诊断任务** (`analyze_image`)
   - 从 URL 下载图片
   - 调用 CV 模型（第一版用 Mock 数据）
   - 查询 TaxonomyService 获取分类详情
   - 可选：RAG 检索 + LLM 生成报告
   - 保存结果到 Celery result backend

---

## 3. Architecture Decisions

### 3.1. 图片上传策略
**决策**：提供专门的 `/upload` 接口，而非直接在 `/diagnose` 中接收图片。

**理由**：
- **职责分离**：上传和诊断解耦，上传后可多次诊断同一图片
- **灵活性**：支持外部 URL（如已存在的 CDN 图片）
- **可测试性**：可独立测试上传和诊断功能

**权衡**：
- 增加一次 HTTP 请求
- 缓解措施：前端可并发请求上传和诊断准备

### 3.2. 异步任务模式
**决策**：使用 Celery 异步任务 + 轮询模式，非 WebSocket/SSE。

**理由**：
- **简单可靠**：轮询逻辑简单，兼容所有客户端
- **可扩展**：Celery 支持水平扩展，可增加 worker 数量
- **容错性**：任务失败可重试，Redis 持久化结果

**权衡**：
- 轮询有延迟（取决于轮询间隔）
- 缓解措施：前端建议 2-3 秒轮询间隔

### 3.3. Mock 数据策略
**决策**：第一版使用 Mock 数据模拟 CV 推理结果。

**理由**：
- **快速验证流程**：不依赖 CV 模型部署，先跑通全链路
- **便于测试**：Mock 数据可控，测试各种场景
- **降低风险**：分阶段实施，避免一次性集成过多组件

**Mock 数据格式**：
```python
{
    "model_label": "powdery_mildew",
    "confidence": 0.92,
    "inference_time_ms": 150
}
```

**后续集成**：
- 第二阶段：接入真实的 CV 模型
- 第三阶段：添加 RAG + LLM 报告生成

### 3.4. 任务状态管理
**决策**：使用 Celery 内置状态机，不自建任务表。

**Celery 状态流转**：
```
PENDING → STARTED → SUCCESS
                → FAILURE
                → RETRY
```

**理由**：
- **开箱即用**：Celery 提供完整的状态管理
- **减少开发**：不需要自己实现任务队列和状态存储
- **监控友好**：可使用 Flower 监控任务

**权衡**：
- 依赖 Redis 可用性
- 缓解措施：Redis 已是基础设施组件，依赖合理

### 3.5. 文件命名策略
**决策**：使用 UUID 前缀 + 原始文件名。

**格式**：`{uuid}_{original_filename}`

**示例**：`a1b2c3d4-..._photo.jpg`

**理由**：
- **避免冲突**：UUID 保证全局唯一性
- **保留原名**：便于识别和调试
- **按时间排序**：UUID 时间戳可推断上传顺序

---

## 4. Impact Assessment

### 4.1. Affected Components
- **New Files Created**:
  - `app/api/endpoints/upload.py` - 图片上传路由
  - `app/api/endpoints/diagnose.py` - 诊断提交和结果查询路由
  - `app/worker/diagnosis_tasks.py` - 诊断任务逻辑
  - `app/models/diagnosis.py` - 诊断结果 Pydantic 模型
  - `tests/api/test_upload.py` - 上传接口测试
  - `tests/api/test_diagnose.py` - 诊断接口测试
  - `tests/worker/test_diagnosis_tasks.py` - Worker 任务测试

- **Modified Files**:
  - `app/api/main.py` - 注册新路由
  - `app/worker/celery_app.py` - 可能需要更新 task 注册

### 4.2. Breaking Changes
- **None** (新功能，不破坏现有代码)

### 4.3. Migration Path
- 无需迁移（新功能）
- 需要确保 Redis 和 Celery Worker 运行

---

## 5. Success Criteria

实现成功需满足以下条件：

1. [ ] `POST /upload` 成功上传图片并返回可访问的 URL
2. [ ] `POST /diagnose` 成功创建 Celery 任务并返回 task_id
3. [ ] `GET /tasks/{task_id}` 能正确返回任务状态和结果
4. [ ] Worker 成功执行 `analyze_image` 任务并返回 Mock 结果
5. [ ] 任务失败时能正确返回错误信息
6. [ ] 完整的端到端测试通过（上传 → 诊断 → 轮询 → 结果）
7. [ ] API 集成测试覆盖率 > 80%
8. [ ] 所有接口出现在 Swagger UI 文档中

---

## 6. Risks & Mitigations

| 风险 | 影响 | 缓解措施 |
|------|--------|----------|
| Redis 不可用导致任务丢失 | 高 | 健康检查确保 Redis 可用，任务失败提示用户 |
| MinIO 存储失败 | 中 | 捕获异常并返回清晰的错误信息 |
| CV 模型推理超时 | 中 | 设置任务超时时间（30分钟），超时自动标记失败 |
| 文件名冲突导致覆盖 | 低 | UUID 前缀确保唯一性 |
| 轮询频率过高导致压力 | 低 | 文档建议合理的轮询间隔（2-3秒） |
| Mock 数据与真实结果差异大 | 中 | Mock 数据标注清楚，第二阶段尽快替换为真实模型 |

---

## 7. Open Questions

1. **是否支持批量诊断**：
   - 当前提案：一次只能诊断一张图片
   - 未来扩展：`POST /diagnose/batch` 接受多个 URL

2. **任务结果保留多久**：
   - Redis 结果过期时间（TTL）
   - 建议：24 小时后自动删除

3. **是否需要历史记录**：
   - 当前方案：任务结果仅存在 Redis，重启后丢失
   - 未来扩展：持久化到数据库，支持查询历史诊断

4. **报告生成是否必需**：
   - 第一版：只返回 CV 分类结果
   - 第二版：集成 RAG + LLM 生成详细报告

---

## 8. Related Specifications

详细技术规范见 `openspec/changes/implement-diagnosis-workflow/specs/diagnosis/spec.md`。

---

## 9. Implementation Phases

### Phase 1: 图片上传接口 (REQ-DIAGNOSIS-001)
- 创建 `app/api/endpoints/upload.py`
- 实现 `POST /upload` 路由
- 集成 StorageService
- 添加文件验证和错误处理

### Phase 2: 诊断提交接口 (REQ-DIAGNOSIS-002)
- 创建 `app/api/endpoints/diagnose.py`
- 实现 `POST /diagnose` 路由
- 创建 Celery 任务
- 返回 task_id

### Phase 3: 结果轮询接口 (REQ-DIAGNOSIS-003)
- 实现 `GET /tasks/{task_id}` 路由
- 查询 Celery 任务状态
- 返回格式化的结果

### Phase 4: Worker 诊断任务 (REQ-DIAGNOSIS-004)
- 创建 `app/worker/diagnosis_tasks.py`
- 实现 `analyze_image` 任务（Mock 版本）
- 集成 TaxonomyService
- 错误处理和日志记录

### Phase 5: 数据模型和测试 (REQ-DIAGNOSIS-005)
- 创建诊断结果 Pydantic 模型
- 编写 API 集成测试
- 编写 Worker 单元测试
- 端到端测试

### Phase 6: 文档和验证
- 更新 API 文档
- 创建使用示例
- 手动测试完整流程
- 性能测试
