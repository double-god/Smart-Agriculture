# Proposal: Expose Taxonomy API (expose-taxonomy-api)

**Change ID**: `expose-taxonomy-api`
**Status**: Proposed
**Created**: 2026-01-22
**Author**: Claude (Full-Stack Agent Architect)

---

## 1. Problem Statement

Smart-Agriculture 系统已经实现了 `TaxonomyService` 单例服务，提供了病虫害分类数据的查询功能。但目前该服务**只能通过 Python 代码访问**，存在以下问题：

- **缺少 HTTP API 接口**：前端和其他服务无法通过 HTTP 请求访问分类数据
- **测试困难**：无法使用 curl/Postman 等工具测试分类查询功能
- **耦合度高**：如果直接在 FastAPI 路由中 import 全局变量，违反依赖注入原则
- **缺少 API 文档**：无法通过 Swagger UI 自动生成 API 文档

---

## 2. Proposed Solution

实现 **Taxonomy REST API**，将 `TaxonomyService` 暴露为标准的 HTTP 接口：

1. **创建 `app/api/endpoints/taxonomy.py`**：实现分类查询路由
2. **实现两个主要接口**：
   - `GET /api/v1/taxonomy/{id}` - 根据 ID 查询分类条目
   - `GET /api/v1/taxonomy/search?q=xxx` - 根据中文名称或模型标签搜索
3. **使用依赖注入**：通过 `Depends(depends_taxonomy)` 注入服务，而非直接 import 全局变量
4. **注册路由**：在 `app/api/main.py` 中注册分类路由
5. **自动文档**：利用 FastAPI 自动生成 OpenAPI 文档

---

## 3. Architecture Decisions

### 3.1. API 版本化
**决策**：所有接口使用 `/api/v1/taxonomy` 前缀。

**理由**：
- 遵循 REST API 最佳实践
- 为未来 API 演进预留空间（v2, v3）
- 与现有 `/api/v1/health` 端点保持一致

**权衡**：
- URL 路径稍长
- 缓解措施：前端可以使用配置文件管理 API 基础路径

### 3.2. RESTful URL 设计
**决策**：
- `GET /api/v1/taxonomy/{id}` - 按查询（幂等）
- `GET /api/v1/taxonomy/search?q=xxx` - 搜索（幂等）

**理由**：
- 遵循 RESTful 资源命名规范
- HTTP 方法语义明确（GET 用于查询）
- 搜索使用 query parameter 更符合 HTTP 习惯

**权衡**：
- 搜索也可以用 `GET /api/v1/taxonomy?search=xxx`
- 缓解措施：当前设计更清晰，后续可按需调整

### 3.3. 错误处理策略
**决策**：将 `TaxonomyNotFoundError` 转换为 HTTP 404 响应。

**实现**：
```python
from fastapi import HTTPException

try:
    entry = taxonomy.get_by_id(id)
except TaxonomyNotFoundError as e:
    raise HTTPException(status_code=404, detail=str(e))
```

**理由**：
- 符合 HTTP 语义（404 Not Found）
- 前端可以根据状态码统一处理错误
- 保留原始错误信息便于调试

### 3.4. 响应数据格式
**决策**：直接返回 Pydantic 模型，FastAPI 自动序列化为 JSON。

**示例**：
```python
@app.get("/taxonomy/{id}")
async def get_taxonomy_entry(id: int, taxonomy: TaxonomyService = Depends(depends_taxonomy)):
    return taxonomy.get_by_id(id)  # FastAPI 自动转换为 JSON
```

**理由**：
- FastAPI 内置 Pydantic 支持，无需手动序列化
- 自动生成 JSON Schema 用于 OpenAPI 文档
- 类型安全，编译期检查

---

## 4. Impact Assessment

### 4.1. Affected Components
- **New Files Created**:
  - `app/api/endpoints/taxonomy.py` (分类查询路由)
  - `app/api/endpoints/__init__.py` (路由模块标记)
  - `openspec/changes/expose-taxonomy-api/` (OpenSpec 文档)

- **Modified Files**:
  - `app/api/main.py` (注册分类路由)
  - `tests/api/test_taxonomy.py` (新增 API 集成测试)

### 4.2. Breaking Changes
- **None** (新功能，不破坏现有代码)

### 4.3. Migration Path
- 无需迁移（新功能）

---

## 5. Success Criteria

实现成功需满足以下条件：

1. [ ] `GET /api/v1/taxonomy/{id}` 返回正确的分类条目
2. [ ] `GET /api/v1/taxonomy/search?q=白粉病` 能搜索到白粉病分类
3. [ ] 查询不存在的 ID 返回 HTTP 404
4. [ ] 所有接口出现在 Swagger UI (`/docs`) 中
5. [ ] API 集成测试覆盖率 > 80%
6. [ ] 使用 `Depends(depends_taxonomy)` 而非直接 import 全局变量
7. [ ] 错误响应包含清晰的错误信息

---

## 6. Risks & Mitigations

| 风险 | 影响 | 缓解措施 |
|------|--------|----------|
| ID 注入攻击（恶意输入超大 ID） | 中 | 使用 Pydantic 路径参数验证（自动限制范围） |
| 搜索参数注入（SQL 注入等） | 低 | 使用内存 dict 查询，无数据库操作 |
| 性能问题（大量并发查询） | 低 | 单例服务 + 内存查询，性能足够 |
| API 文档不一致 | 低 | FastAPI 自动生成 OpenAPI，确保文档与代码同步 |

---

## 7. Open Questions

1. **是否需要分页**：
   - 当前分类数据仅 5 条，不需要分页
   - 如果分类扩展到 100+ 条，考虑添加 `GET /api/v1/taxonomy?page=1&size=20`

2. **是否支持批量查询**：
   - 当前未实现
   - 未来可添加 `POST /api/v1/taxonomy/batch` 接受 ID 列表

3. **搜索是否支持模糊匹配**：
   - 当前只支持精确匹配（中文名称、模型标签）
   - 可考虑使用正则或包含匹配

---

## 8. Related Specifications

详细技术规范见 `openspec/changes/expose-taxonomy-api/specs/taxonomy/spec.md`。
