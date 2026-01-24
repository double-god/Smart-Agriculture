# Specification: Taxonomy REST API

**Capability**: Taxonomy API
**Version**: 1.0.0
**Status**: Proposed

---

## ADDED Requirements

### REQ-TAXONOMY-API-001: GET /taxonomy/{id}

系统必须实现根据 ID 查询分类条目的 REST API 接口。

**接口定义**：

```python
# app/api/endpoints/taxonomy.py

from fastapi import APIRouter, Depends, HTTPException, Path
from app.services.taxonomy_service import TaxonomyService, TaxonomyNotFoundError
from app.core import depends_taxonomy

router = APIRouter(prefix="/api/v1/taxonomy", tags=["taxonomy"])

@router.get("/{id}")
async def get_taxonomy_entry(
    id: int = Path(..., ge=0, le=1000, description="分类 ID (0-1000)"),
    taxonomy: TaxonomyService = Depends(depends_taxonomy),
) -> TaxonomyEntry:
    """
    根据 ID 查询分类条目。

    Args:
        id: 分类唯一标识符
        taxonomy: TaxonomyService 依赖注入

    Returns:
        TaxonomyEntry: 分类条目对象

    Raises:
        HTTPException: 当 ID 不存在时返回 404

    Example:
        GET /api/v1/taxonomy/1
        Response:
        {
            "id": 1,
            "model_label": "aphid_complex",
            "zh_scientific_name": "蚜虫类",
            "latin_name": "Aphididae",
            "category": "Pest",
            "action_policy": "RETRIEVE",
            "search_keywords": ["蚜虫", "腻虫"],
            "description": "成虫和若虫刺吸汁液...",
            "risk_level": "medium",
            "note": null
        }
    """
    try:
        return taxonomy.get_by_id(id)
    except TaxonomyNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
```

**约束条件**：
- URL 路径参数 `id` 必须是整数，范围 0-1000
- ID 不存在时返回 HTTP 404，错误信息包含 ID 值
- 响应 Content-Type 为 `application/json`
- 必须使用 `Depends(depends_taxonomy)` 进行依赖注入

---

### REQ-TAXONOMY-API-002: GET /taxonomy/search

系统必须实现根据中文名称或模型标签搜索分类条目的 REST API 接口。

**接口定义**：

```python
from fastapi import Query, HTTPException
from typing import List

@router.get("/search")
async def search_taxonomy(
    q: str = Query(..., min_length=1, max_length=100, description="搜索关键词（中文名称或模型标签）"),
    taxonomy: TaxonomyService = Depends(depends_taxonomy),
) -> List[TaxonomyEntry]:
    """
    根据中文名称或模型标签搜索分类条目。

    Args:
        q: 搜索关键词，支持中文名称或模型标签
        taxonomy: TaxonomyService 依赖注入

    Returns:
        List[TaxonomyEntry]: 匹配的分类条目列表

    Raises:
        HTTPException: 当未找到匹配结果时返回 404

    Example:
        GET /api/v1/taxonomy/search?q=白粉病
        Response:
        [
            {
                "id": 2,
                "model_label": "powdery_mildew",
                "zh_scientific_name": "白粉病",
                "latin_name": "Erysiphales",
                "category": "Disease",
                "action_policy": "RETRIEVE",
                "search_keywords": ["白粉", "粉病"],
                "description": "叶片表面出现白色粉状物...",
                "risk_level": "high",
                "note": null
            }
        ]
    """
    results = []

    # 尝试按中文名称搜索
    try:
        result = taxonomy.get_by_name(q)
        results.append(result)
    except TaxonomyNotFoundError:
        pass

    # 尝试按模型标签搜索
    try:
        result = taxonomy.get_by_model_label(q)
        if result not in results:
            results.append(result)
    except TaxonomyNotFoundError:
        pass

    if not results:
        raise HTTPException(
            status_code=404,
            detail=f"No taxonomy entry found for query: '{q}'"
        )

    return results
```

**约束条件**：
- Query 参数 `q` 必须非空，长度 1-100 字符
- 同时支持中文名称和模型标签搜索
- 未找到结果时返回 HTTP 404
- 返回列表类型，即使只有一个结果
- 必须使用 `Depends(depends_taxonomy)` 进行依赖注入

---

### REQ-TAXONOMY-API-003: 路由注册

系统必须在 `app/api/main.py` 中注册分类路由。

**实现**：

```python
# app/api/main.py

from fastapi import FastAPI
from app.core.config import get_settings
from app.api.endpoints.taxonomy import router as taxonomy_router

# Initialize settings
settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="Plant Disease and Pest Diagnosis System",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Register taxonomy router
app.include_router(
    taxonomy_router,
    prefix="/api/v1/taxonomy",
    tags=["taxonomy"]
)

# ... existing routes ...
```

**约束条件**：
- 使用 `app.include_router()` 注册路由
- 不要修改路由前缀（已在 taxonomy.py 中定义）
- 必须在应用启动时完成注册

---

### REQ-TAXONOMY-API-004: 依赖注入规范

所有 API 路由必须使用 `app.core.deps.depends_taxonomy` 进行依赖注入，**禁止**直接 import 全局变量。

**正确示例**：

```python
from app.core import depends_taxonomy

@router.get("/taxonomy/{id}")
async def get_taxonomy_entry(
    id: int,
    taxonomy: TaxonomyService = Depends(depends_taxonomy)  # ✅ 正确
):
    return taxonomy.get_by_id(id)
```

**错误示例**：

```python
from app.services.taxonomy_service import get_taxonomy_service  # ❌ 错误

@router.get("/taxonomy/{id}")
async def get_taxonomy_entry(id: int):
    taxonomy = get_taxonomy_service()  # ❌ 违反依赖注入原则
    return taxonomy.get_by_id(id)
```

**理由**：
- 遵循依赖倒置原则（Dependency Inversion Principle）
- 便于测试（可轻松 mock 服务）
- 与 TaxonomyService、StorageService 保持一致的设计模式

---

### REQ-TAXONOMY-API-005: API 集成测试

系统必须包含 API 集成测试，覆盖所有接口和错误场景。

**测试场景**：

#### 场景 1: 查询存在的 ID
**GIVEN** 数据库中存在 ID=1 的分类条目
**WHEN** 调用 `GET /api/v1/taxonomy/1`
**THEN** 返回 HTTP 200
**AND** 响应体包含正确的分类数据

#### 场景 2: 查询不存在的 ID
**GIVEN** 数据库中不存在 ID=9999
**WHEN** 调用 `GET /api/v1/taxonomy/9999`
**THEN** 返回 HTTP 404
**AND** 响应体包含错误信息

#### 场景 3: 搜索中文名称
**GIVEN** 数据库中存在 "白粉病" 分类
**WHEN** 调用 `GET /api/v1/taxonomy/search?q=白粉病`
**THEN** 返回 HTTP 200
**AND** 返回列表包含白粉病分类

#### 场景 4: 搜索模型标签
**GIVEN** 数据库中存在 "aphid_complex" 分类
**WHEN** 调用 `GET /api/v1/taxonomy/search?q=aphid_complex`
**THEN** 返回 HTTP 200
**AND** 返回列表包含蚜虫类分类

#### 场景 5: 搜索不存在的关键词
**GIVEN** 数据库中不存在匹配的关键词
**WHEN** 调用 `GET /api/v1/taxonomy/search?q=不存在的病害`
**THEN** 返回 HTTP 404
**AND** 响应体包含错误信息

#### 场景 6: 路径参数验证
**GIVEN** 用户输入无效的 ID
**WHEN** 调用 `GET /api/v1/taxonomy/abc`
**THEN** FastAPI 自动返回 HTTP 422
**AND** 响应体包含验证错误详情

**实现**：

```python
# tests/api/test_taxonomy.py

import pytest
from fastapi.testclient import TestClient
from app.api.main import app

client = TestClient(app)

def test_get_taxonomy_by_id_success():
    """测试查询存在的 ID"""
    response = client.get("/api/v1/taxonomy/1")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert data["zh_scientific_name"] == "蚜虫类"

def test_get_taxonomy_by_id_not_found():
    """测试查询不存在的 ID"""
    response = client.get("/api/v1/taxonomy/9999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

def test_search_taxonomy_by_chinese_name():
    """测试按中文名称搜索"""
    response = client.get("/api/v1/taxonomy/search?q=白粉病")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["zh_scientific_name"] == "白粉病"

def test_search_taxonomy_by_model_label():
    """测试按模型标签搜索"""
    response = client.get("/api/v1/taxonomy/search?q=aphid_complex")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["model_label"] == "aphid_complex"

def test_search_taxonomy_not_found():
    """测试搜索不存在的关键词"""
    response = client.get("/api/v1/taxonomy/search?q=不存在的病害")
    assert response.status_code == 404

def test_invalid_id_parameter():
    """测试无效的 ID 参数"""
    response = client.get("/api/v1/taxonomy/abc")
    assert response.status_code == 422
```

**约束条件**：
- 使用 `TestClient` 进行集成测试
- 测试覆盖率 > 80%
- 所有测试必须在 <1 秒内完成
- 不需要真实的数据库或外部服务

---

## MODIFIED Requirements

None (this is a new capability)

---

## DEPRECATED Requirements

None
