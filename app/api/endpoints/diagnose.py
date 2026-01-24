"""
Diagnosis API endpoints for Smart Agriculture system.

This module provides diagnosis submission and task status query functionality.
"""

from fastapi import APIRouter, HTTPException
from celery.result import AsyncResult
from app.worker.celery_app import celery_app
from app.worker.diagnosis_tasks import analyze_image
from app.models.diagnosis import DiagnoseRequest, DiagnoseResponse, TaskStatus

router = APIRouter(prefix="/api/v1/diagnose", tags=["diagnose"])


@router.post("", response_model=DiagnoseResponse)
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


@router.get("/tasks/{task_id}", response_model=TaskStatus)
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
    response_data = {
        "task_id": task_id,
        "status": task.state,
        "result": None,
        "error": None
    }

    # 如果任务成功，返回结果
    if task.state == "SUCCESS" and task.result:
        response_data["result"] = task.result
    # 如果任务失败，返回错误信息
    elif task.state == "FAILURE":
        response_data["error"] = str(task.info)

    return TaskStatus(**response_data)
