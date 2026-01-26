# Specification: Diagnosis Workflow

**Capability**: Diagnosis
**Version**: 1.0.0
**Status**: Proposed

---

## ADDED Requirements

### REQ-DIAGNOSIS-001: 图片上传接口

系统必须实现图片上传接口，支持接收图片文件并存储到 MinIO。

**接口定义**：

```python
# app/api/endpoints/upload.py

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from app.services.storage import StorageService, StorageConnectionError
from app.core import depends_storage
import uuid

router = APIRouter(prefix="/api/v1/upload", tags=["upload"])

@router.post("")
async def upload_image(
    file: UploadFile = File(..., description="图片文件（支持 jpg, jpeg, png）"),
    storage: StorageService = Depends(depends_storage),
) -> dict:
    """
    上传诊断图片到 MinIO 存储。

    Args:
        file: 上传的图片文件
        storage: StorageService 依赖注入

    Returns:
        包含图片 URL 和文件信息的字典

    Raises:
        HTTPException: 当文件类型不支持或上传失败时

    Example:
        POST /api/v1/upload
        Content-Type: multipart/form-data

        Response:
        {
            "url": "http://localhost:9010/smart-agriculture/a1b2c3d4-photo.jpg",
            "filename": "a1b2c3d4-photo.jpg",
            "original_filename": "photo.jpg",
            "content_type": "image/jpeg"
        }
    """
    # 验证文件类型
    allowed_types = ["image/jpeg", "image/jpg", "image/png"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(allowed_types)}"
        )

    # 生成唯一文件名
    file_extension = file.filename.split(".")[-1] if file.filename else "jpg"
    unique_filename = f"{uuid.uuid4()}_{file.filename}"

    try:
        # 上传到 MinIO
        url = storage.upload_image(
            file.file,
            unique_filename,
            content_type=file.content_type
        )

        return {
            "url": url,
            "filename": unique_filename,
            "original_filename": file.filename,
            "content_type": file.content_type
        }

    except StorageConnectionError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Failed to upload image: {str(e)}"
        )
```

**约束条件**：
- 仅支持 JPEG、JPG、PNG 格式
- 文件大小限制（建议 < 10MB）
- 使用 UUID 前缀确保文件名唯一
- 捕获存储异常并转换为 HTTP 503

---

### REQ-DIAGNOSIS-002: 诊断提交接口

系统必须实现诊断提交接口，接收图片 URL 并创建异步诊断任务。

**接口定义**：

```python
# app/api/endpoints/diagnose.py

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, HttpUrl
from typing import Optional
from app.worker.diagnosis_tasks import analyze_image

router = APIRouter(prefix="/api/v1/diagnose", tags=["diagnose"])


class DiagnoseRequest(BaseModel):
    """诊断请求模型"""
    image_url: HttpUrl
    crop_type: Optional[str] = None  # 可选：作物类型
    location: Optional[str] = None   # 可选：地理位置


class DiagnoseResponse(BaseModel):
    """诊断响应模型"""
    task_id: str
    status: str
    message: str


@router.post("")
async def create_diagnosis(
    request: DiagnoseRequest,
) -> DiagnoseResponse:
    """
    提交诊断任务，返回异步任务 ID。

    Args:
        request: 诊断请求，包含图片 URL 和可选参数

    Returns:
        任务 ID 和状态信息

    Raises:
        HTTPException: 当任务创建失败时

    Example:
        POST /api/v1/diagnose
        {
            "image_url": "http://localhost:9010/smart-agriculture/abc123-photo.jpg",
            "crop_type": "番茄",
            "location": "大棚A区"
        }

        Response:
        {
            "task_id": "a1b2c3d4-5678-90ab-cdef-123456789abc",
            "status": "PENDING",
            "message": "Diagnosis task created successfully"
        }
    """
    try:
        # 提取图片 URL 字符串
        image_url_str = str(request.image_url)

        # 创建 Celery 异步任务
        task = analyze_image.delay(
            image_url=image_url_str,
            crop_type=request.crop_type,
            location=request.location
        )

        return DiagnoseResponse(
            task_id=task.id,
            status=task.state,
            message="Diagnosis task created successfully"
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create diagnosis task: {str(e)}"
        )
```

**约束条件**：
- 使用 Pydantic 验证 image_url 格式
- 立即返回 task_id，不等待任务完成
- 任务创建失败返回 HTTP 500
- 支持可选的作物类型和地理位置参数

---

### REQ-DIAGNOSIS-003: 结果轮询接口

系统必须实现结果查询接口，支持根据 task_id 查询诊断任务状态和结果。

**接口定义**：

```python
# app/api/endpoints/diagnose.py (续)

from celery.result import AsyncResult
from app.worker.celery_app import celery_app


class TaskStatus(BaseModel):
    """任务状态模型"""
    task_id: str
    status: str  # PENDING, STARTED, SUCCESS, FAILURE, RETRY
    result: Optional[dict] = None
    error: Optional[str] = None


@router.get("/tasks/{task_id}")
async def get_task_status(
    task_id: str,
) -> TaskStatus:
    """
    查询诊断任务状态和结果。

    Args:
        task_id: 任务 ID

    Returns:
        任务状态和结果（如果完成）

    Raises:
        HTTPException: 当任务 ID 无效时

    Example:
        GET /api/v1/diagnose/tasks/a1b2c3d4-5678-90ab-cdef-123456789abc

        Response (SUCCESS):
        {
            "task_id": "a1b2c3d4-...",
            "status": "SUCCESS",
            "result": {
                "model_label": "powdery_mildew",
                "confidence": 0.92,
                "diagnosis_name": "白粉病",
                "category": "Disease",
                "action_policy": "RETRIEVE",
                "inference_time_ms": 150
            },
            "error": null
        }

        Response (PENDING):
        {
            "task_id": "a1b2c3d4-...",
            "status": "PENDING",
            "result": null,
            "error": null
        }
    """
    # 查询 Celery 任务状态
    task = AsyncResult(task_id, app=celery_app)

    # 准备响应
    response = TaskStatus(
        task_id=task_id,
        status=task.state
    )

    # 如果任务成功，返回结果
    if task.state == "SUCCESS":
        response.result = task.result
    # 如果任务失败，返回错误信息
    elif task.state == "FAILURE":
        response.error = str(task.info)

    return response
```

**约束条件**：
- 支持所有 Celery 状态（PENDING, STARTED, SUCCESS, FAILURE, RETRY）
- 成功时返回完整诊断结果
- 失败时返回错误信息
- 进行中的任务 result 为 null

---

### REQ-DIAGNOSIS-004: Worker 诊断任务

系统必须在 Celery Worker 中实现图片分析任务，支持异步处理诊断请求。

**任务定义**：

```python
# app/worker/diagnosis_tasks.py

from app.worker.celery_app import celery_app
from app.services.taxonomy_service import TaxonomyService, get_taxonomy_service
import requests
import logging
import time
import random

logger = logging.getLogger(__name__)


@celery_app.task(name="app.worker.diagnosis_tasks.analyze_image", bind=True)
def analyze_image(self, image_url: str, crop_type: str = None, location: str = None):
    """
    分析图片并返回诊断结果（Mock 版本）。

    Args:
        self: Celery task instance (for bind=True)
        image_url: 图片 URL
        crop_type: 可选的作物类型
        location: 可选的地理位置

    Returns:
        诊断结果字典

    Mock 数据格式:
        {
            "model_label": "powdery_mildew",
            "confidence": 0.92,
            "diagnosis_name": "白粉病",
            "category": "Disease",
            "action_policy": "RETRIEVE",
            "inference_time_ms": 150,
            "taxonomy_id": 2
        }
    """
    logger.info(f"Starting diagnosis for image: {image_url}")

    try:
        # 1. 下载图片（验证 URL 可访问性）
        logger.info(f"Downloading image from: {image_url}")
        try:
            response = requests.get(image_url, timeout=10)
            response.raise_for_status()
            image_size = len(response.content)
            logger.info(f"Image downloaded successfully, size: {image_size} bytes")
        except Exception as e:
            raise RuntimeError(f"Failed to download image: {str(e)}")

        # 2. 模拟 CV 模型推理（Mock 数据）
        logger.info("Running CV model inference...")
        start_time = time.time()

        # Mock: 随机选择一个分类结果
        mock_results = [
            {
                "model_label": "healthy",
                "confidence": 0.95,
            },
            {
                "model_label": "powdery_mildew",
                "confidence": 0.87,
            },
            {
                "model_label": "aphid_complex",
                "confidence": 0.92,
            },
            {
                "model_label": "spider_mite",
                "confidence": 0.78,
            },
            {
                "model_label": "late_blight",
                "confidence": 0.85,
            },
        ]

        mock_result = random.choice(mock_results)
        inference_time = int((time.time() - start_time) * 1000)

        logger.info(f"Mock inference result: {mock_result['model_label']} (confidence: {mock_result['confidence']})")

        # 3. 查询 TaxonomyService 获取详细信息
        taxonomy = get_taxonomy_service()
        try:
            taxonomy_entry = taxonomy.get_by_model_label(mock_result["model_label"])
        except Exception as e:
            logger.warning(f"Taxonomy entry not found for {mock_result['model_label']}: {e}")
            taxonomy_entry = None

        # 4. 构建诊断结果
        result = {
            "model_label": mock_result["model_label"],
            "confidence": mock_result["confidence"],
            "inference_time_ms": inference_time,
        }

        if taxonomy_entry:
            result.update({
                "diagnosis_name": taxonomy_entry.zh_scientific_name,
                "latin_name": taxonomy_entry.latin_name,
                "category": taxonomy_entry.category,
                "action_policy": taxonomy_entry.action_policy,
                "taxonomy_id": taxonomy_entry.id,
                "description": taxonomy_entry.description,
                "risk_level": taxonomy_entry.risk_level,
            })
        else:
            result.update({
                "diagnosis_name": "未知",
                "latin_name": "Unknown",
                "category": "Unknown",
                "action_policy": "HUMAN_REVIEW",
                "taxonomy_id": None,
            })

        # 5. 添加可选参数
        if crop_type:
            result["crop_type"] = crop_type
        if location:
            result["location"] = location

        logger.info(f"Diagnosis completed successfully: {result['diagnosis_name']}")

        return result

    except Exception as e:
        logger.error(f"Diagnosis failed: {str(e)}", exc_info=True)
        # 重新抛出异常，Celery 会标记任务为 FAILURE
        raise
```

**任务行为**：
1. **下载图片**：验证 URL 可访问性
2. **Mock 推理**：随机选择一个分类结果
3. **查询分类**：根据模型标签查询 TaxonomyService
4. **返回结果**：包含置信度、分类信息、置信度等
5. **错误处理**：任何异常都会标记任务为 FAILURE

**任务配置**：
- 超时时间：30 分钟（在 celery_app.py 中配置）
- 重试策略：失败不自动重试（手动触发）
- 日志记录：详细的任务执行日志

---

### REQ-DIAGNOSIS-005: 数据模型

系统必须定义诊断相关的 Pydantic 数据模型。

**模型定义**：

```python
# app/models/diagnosis.py

from pydantic import BaseModel, HttpUrl
from typing import Optional


class DiagnoseRequest(BaseModel):
    """诊断请求模型"""
    image_url: HttpUrl
    crop_type: Optional[str] = None
    location: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "image_url": "http://localhost:9010/smart-agriculture/abc123-photo.jpg",
                    "crop_type": "番茄",
                    "location": "大棚A区"
                }
            ]
        }
    }


class DiagnoseResponse(BaseModel):
    """诊断响应模型"""
    task_id: str
    status: str
    message: str


class DiagnosisResult(BaseModel):
    """诊断结果模型"""
    model_label: str
    confidence: float
    diagnosis_name: str
    latin_name: Optional[str] = None
    category: str
    action_policy: str
    taxonomy_id: Optional[int] = None
    inference_time_ms: int
    description: Optional[str] = None
    risk_level: Optional[str] = None
    crop_type: Optional[str] = None
    location: Optional[str] = None


class TaskStatus(BaseModel):
    """任务状态模型"""
    task_id: str
    status: str  # PENDING, STARTED, SUCCESS, FAILURE, RETRY
    result: Optional[DiagnosisResult] = None
    error: Optional[str] = None


class UploadResponse(BaseModel):
    """上传响应模型"""
    url: str
    filename: str
    original_filename: str
    content_type: str
```

---

### REQ-DIAGNOSIS-006: API 集成测试

系统必须包含完整的 API 集成测试。

**测试场景**：

#### 场景 1: 成功上传图片
**GIVEN** 有效的 JPEG 图片文件
**WHEN** 调用 `POST /upload`
**THEN** 返回 HTTP 200
**AND** 返回包含 URL 的响应

#### 场景 2: 上传不支持的文件类型
**GIVEN** PDF 文件
**WHEN** 调用 `POST /upload`
**THEN** 返回 HTTP 400
**AND** 错误信息包含 "Unsupported file type"

#### 场景 3: 成功创建诊断任务
**GIVEN** 有效的图片 URL
**WHEN** 调用 `POST /diagnose`
**THEN** 返回 HTTP 200
**AND** 返回 task_id 和 PENDING 状态

#### 场景 4: 查询进行中的任务
**GIVEN** 刚创建的任务 ID
**WHEN** 调用 `GET /tasks/{task_id}`
**THEN** 返回 PENDING 或 STARTED 状态
**AND** result 为 null

#### 场景 5: 查询完成的任务
**GIVEN** Worker 已完成的任务 ID
**WHEN** 调用 `GET /tasks/{task_id}`
**THEN** 返回 SUCCESS 状态
**AND** result 包含完整诊断结果

#### 场景 6: 端到端测试
**GIVEN** 一张测试图片
**WHEN** 上传 → 诊断 → 轮询结果
**THEN** 完整流程成功
**AND** 返回正确的诊断结果

**测试实现**：

```python
# tests/api/test_upload.py

import pytest
from fastapi.testclient import TestClient
from app.api.main import app

client = TestClient(app)


def test_upload_image_success():
    """测试成功上传图片"""
    from io import BytesIO

    # 创建模拟图片文件
    image_content = b"fake image data"
    files = {"file": ("test.jpg", BytesIO(image_content), "image/jpeg")}

    response = client.post("/api/v1/upload", files=files)

    assert response.status_code == 200
    data = response.json()
    assert "url" in data
    assert "filename" in data
    assert data["content_type"] == "image/jpeg"


def test_upload_unsupported_file_type():
    """测试上传不支持的文件类型"""
    from io import BytesIO

    files = {"file": ("test.pdf", BytesIO(b"fake pdf"), "application/pdf")}

    response = client.post("/api/v1/upload", files=files)

    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


# tests/api/test_diagnose.py

def test_create_diagnosis_task():
    """测试创建诊断任务"""
    request_data = {
        "image_url": "http://localhost:9010/smart-agriculture/test.jpg",
        "crop_type": "番茄"
    }

    response = client.post("/api/v1/diagnose", json=request_data)

    assert response.status_code == 200
    data = response.json()
    assert "task_id" in data
    assert data["status"] in ["PENDING", "STARTED"]


def test_get_task_status_pending():
    """测试查询进行中的任务"""
    # 先创建任务
    create_response = client.post("/api/v1/diagnose", json={
        "image_url": "http://localhost:9010/smart-agriculture/test.jpg"
    })
    task_id = create_response.json()["task_id"]

    # 查询状态
    response = client.get(f"/api/v1/diagnose/tasks/{task_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == task_id
    assert data["status"] in ["PENDING", "STARTED", "SUCCESS"]


def test_end_to_end_diagnosis():
    """测试端到端诊断流程"""
    # 需要运行 Celery Worker 才能测试完整流程
    pass
```

---

## MODIFIED Requirements

None (this is a new capability)

---

## DEPRECATED Requirements

None
