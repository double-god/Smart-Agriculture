# Proposal: Implement Storage Service (implement-storage-service)

**Change ID**: `implement-storage-service`
**Status**: Proposed
**Created**: 2026-01-22
**Author**: Claude (Full-Stack Agent Architect)

---

## 1. Problem Statement

Smart-Agriculture 系统目前缺乏**统一的对象存储服务抽象层**。虽然 MinIO 已经通过 Docker Compose 部署，并且环境变量配置已就绪，但存在以下问题：

- **直接调用 MinIO 客户端**: 业务代码直接依赖 `minio` Python 包，缺乏抽象层
- **配置分散**: MinIO 连接参数散落在代码中，难以维护
- **错误处理不统一**: 缺乏统一的连接异常处理策略
- **URL 生成逻辑重复**: 每个需要生成访问 URL 的地方都要重复实现相同逻辑
- **难以测试**: 直接依赖 MinIO 客户端，单元测试困难

这违反了 **依赖倒置原则**（Dependency Inversion Principle），增加了代码耦合度。

---

## 2. Proposed Solution

实现一个 **StorageService 单例服务**，封装 MinIO 操作：

1. **配置管理**: 从 `app.core.config.Settings` 读取 MinIO 配置
2. **连接管理**: 建立并维护 MinIO 客户端连接
3. **文件上传**: `upload_image(file_data, filename)` → 返回可访问的 URL
4. **异常处理**: 统一处理连接失败、认证失败、Bucket 不存在等异常
5. **Bucket 自动创建**: 如果 Bucket 不存在，自动创建并设置公共访问策略

---

## 3. Architecture Decisions

### 3.1. Singleton Pattern
**决策**: 使用单例模式 `StorageService`。

**理由**:
- MinIO 客户端连接是重量级资源，应该复用
- 配置在运行时不变，单例避免重复初始化
- 与 `TaxonomyService` 保持一致的设计模式

**权衡**:
- 全局状态（但对只读配置和连接池可接受）
- 缓解措施: 文档说明服务为线程安全的只读操作

### 3.2. MinIO Python Client
**决策**: 使用官方 `minio` Python SDK。

**理由**:
- 官方维护，稳定可靠
- 支持 Python 3.12+
- 提供同步和异步 API（本提案先用同步 API）

**权衡**:
- 同步 API 可能阻塞 FastAPI 异步事件循环
- 缓解措施: 在后续版本中可迁移到异步 API

### 3.3. URL 生成策略
**决策**: 服务返回完整的 HTTP 访问 URL。

**格式**: `http://{endpoint}/{bucket}/{filename}`

**理由**:
- 调用方无需拼接 URL
- 支持后续添加 CDN 或签名 URL（presigned URL）
- 统一 URL 格式，便于前端集成

**权衡**:
- 假设 MinIO 端点可从外部访问
- 缓解措施: 后续可添加 `generate_presigned_url()` 方法

---

## 4. Impact Assessment

### 4.1. Affected Components
- **New Files Created**:
  - `app/services/storage.py` (StorageService 实现)
  - `tests/services/test_storage.py` (单元测试)
  - `openspec/changes/implement-storage-service/` (OpenSpec 文档)

- **Modified Files**:
  - `app/core/config.py` (MinIO 配置已存在，无需修改)
  - `pyproject.toml` (添加 `minio` 依赖)

### 4.2. Breaking Changes
- **None** (新功能，不破坏现有代码)

### 4.3. Migration Path
- 无需迁移（新功能）

---

## 5. Success Criteria

实现成功需满足以下条件：

1. [ ] `StorageService` 可成功连接到 MinIO
2. [ ] `upload_image(file_data, filename)` 上传图片并返回完整 URL
3. [ ] Bucket 不存在时自动创建并设置公共访问策略
4. [ ] 连接失败时抛出清晰的异常信息
5. [ ] 单元测试覆盖率 > 80%
6. [ ] FastAPI 路由可通过依赖注入使用 StorageService
7. [ ] 上传的文件可通过返回的 URL 在浏览器中访问

---

## 6. Risks & Mitigations

| 风险 | 影响 | 缓解措施 |
|------|--------|----------|
| MinIO 服务不可用 | 高 | 启动时验证连接，失败时快速失败并提示 |
| 网络延迟阻塞请求 | 中 | 使用 FastAPI 后台任务处理大文件上传 |
| Bucket 权限配置错误 | 高 | 自动创建时设置公共读取策略，并验证 |
| 文件名冲突 | 中 | 添加 UUID 前缀或时间戳（后续版本） |
| 磁盘空间不足 | 中 | 监控 Bucket 大小，添加删除方法（后续版本） |

---

## 7. Open Questions

1. **文件名冲突处理**: 是否在 `upload_image()` 中自动添加 UUID 前缀？
   - **建议**: 第一版不处理，由调用方确保文件名唯一
   - **未来**: 添加 `generate_unique_filename()` 辅助方法

2. **是否支持文件删除**: 第一版是否实现 `delete_file()` 方法？
   - **建议**: 第一版不实现，后续根据需求添加
   - **理由**: YAGNI 原则（You Aren't Gonna Need It）

3. **是否支持 Presigned URL**: 是否生成带签名的临时 URL？
   - **建议**: 第一版使用公共访问 URL
   - **未来**: 添加 `generate_presigned_url(expires_in)` 方法

---

## 8. Related Specifications

详细技术规范见 `openspec/changes/implement-storage-service/specs/storage/spec.md`。
